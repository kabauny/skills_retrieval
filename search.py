#!/usr/bin/env python3
"""
Gemini grounded search → markdown file.

Usage:
    python search.py "your search query here"
    python search.py "your search query here" --prompt "focus on clinical trials"

Requires:
    GOOGLE_API_KEY environment variable (or .env file in project root)
"""

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MODEL = "gemini-2.5-flash"
OUTPUT_DIR = Path(__file__).parent / "raw" / "searches"
TOKEN_LOG = OUTPUT_DIR / "_token_log.jsonl"

# URLs from Gemini grounding chunks come back as redirect URLs through this host.
# We resolve them to their final destination so the wiki cites the real source.
REDIRECT_HOST = "vertexaisearch.cloud.google.com"
RESOLVE_TIMEOUT = 5.0     # seconds per HEAD request
RESOLVE_WORKERS = 8       # parallel HTTP workers
RESOLVE_USER_AGENT = "skills_retrieval/0.1 (+url-resolver)"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def kebab(text: str, max_len: int = 80) -> str:
    """Convert text to kebab-case filename."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text[:max_len]


# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------


def _resolve_one(url: str) -> str:
    """Follow a Google grounding redirect to its final URL. Return original on failure."""
    if REDIRECT_HOST not in url:
        return url
    headers = {"User-Agent": RESOLVE_USER_AGENT}
    try:
        # HEAD first — cheap and avoids downloading body
        resp = requests.head(url, allow_redirects=True, timeout=RESOLVE_TIMEOUT, headers=headers)
        if resp.status_code < 400 and resp.url and REDIRECT_HOST not in resp.url:
            return resp.url
        # Fall back to GET if HEAD didn't yield a clean redirect (some hosts block HEAD)
        resp = requests.get(
            url, allow_redirects=True, timeout=RESOLVE_TIMEOUT, stream=True, headers=headers
        )
        resp.close()
        if resp.url and REDIRECT_HOST not in resp.url:
            return resp.url
    except Exception:
        pass
    return url


def resolve_urls(urls: list[str]) -> dict[str, str]:
    """Resolve a list of URLs in parallel. Returns {original: resolved} mapping.

    Deduplicates input. Failures map original → original (caller can keep the redirect).
    """
    unique = list({u for u in urls if u})
    if not unique:
        return {}
    out: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=RESOLVE_WORKERS) as ex:
        future_to_url = {ex.submit(_resolve_one, u): u for u in unique}
        for fut in as_completed(future_to_url):
            original = future_to_url[fut]
            try:
                out[original] = fut.result()
            except Exception:
                out[original] = original
    return out


def apply_url_map(text: str, url_map: dict[str, str]) -> str:
    """Replace every original URL with its resolved counterpart in a text blob.

    Substitution is by exact-match string replace, longest first, so partial
    URL prefixes don't get clobbered.
    """
    if not url_map:
        return text
    for original in sorted(url_map.keys(), key=len, reverse=True):
        resolved = url_map[original]
        if resolved and resolved != original:
            text = text.replace(original, resolved)
    return text


def build_inline_citations(text: str, metadata) -> str:
    """Insert inline citation links into the response text."""
    if not metadata or not metadata.grounding_supports:
        return text

    chunks = metadata.grounding_chunks or []

    # Collect all insertions: list of (position, citation_text)
    insertions: list[tuple[int, str]] = []

    for support in metadata.grounding_supports:
        if not support.grounding_chunk_indices or not support.segment:
            continue
        end = support.segment.end_index or len(text)
        links = []
        for idx in support.grounding_chunk_indices:
            if idx < len(chunks) and chunks[idx].web:
                uri = chunks[idx].web.uri
                title = chunks[idx].web.title or "source"
                links.append(f"[{title}]({uri})")
        if links:
            insertions.append((end, " " + " ".join(links)))

    # Apply insertions from end to start so positions stay valid
    for pos, cite_text in sorted(insertions, key=lambda x: x[0], reverse=True):
        text = text[:pos] + cite_text + text[pos:]

    return text


def extract_sources(metadata) -> list[dict]:
    """Pull unique sources from grounding chunks."""
    if not metadata or not metadata.grounding_chunks:
        return []
    seen = set()
    sources = []
    for chunk in metadata.grounding_chunks:
        if chunk.web and chunk.web.uri and chunk.web.uri not in seen:
            seen.add(chunk.web.uri)
            sources.append({
                "title": chunk.web.title or "Untitled",
                "url": chunk.web.uri,
            })
    return sources


def format_sources_yaml(sources: list[dict]) -> str:
    """Format sources list as YAML."""
    if not sources:
        return "sources: []"
    lines = ["sources:"]
    for s in sources:
        lines.append(f'  - title: "{s["title"]}"')
        lines.append(f'    url: "{s["url"]}"')
    return "\n".join(lines)


def extract_token_usage(response) -> dict:
    """Pull token counts from response.usage_metadata. Returns zeros on failure."""
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        return {"prompt_tokens": 0, "candidates_tokens": 0, "total_tokens": 0}
    return {
        "prompt_tokens": getattr(usage, "prompt_token_count", 0) or 0,
        "candidates_tokens": getattr(usage, "candidates_token_count", 0) or 0,
        "total_tokens": getattr(usage, "total_token_count", 0) or 0,
    }


def append_token_log(query: str, filepath: Path, tokens: dict, model: str) -> None:
    """Append a JSONL entry to _token_log.jsonl for per-call audit."""
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "query": query,
        "file": str(filepath.relative_to(filepath.parent.parent.parent)) if filepath.is_absolute() else str(filepath),
        **tokens,
    }
    TOKEN_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TOKEN_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def format_markdown(
    query: str,
    response_text: str,
    sources: list[dict],
    search_queries: list[str],
    tokens: dict,
    model: str,
) -> str:
    """Assemble the full markdown file."""
    today = date.today().isoformat()
    sq_yaml = "\n".join(f'  - "{q}"' for q in search_queries) if search_queries else "  []"

    frontmatter = f"""---
title: "Search: {query}"
source_type: search
search_query: "{query}"
search_queries_used:
{sq_yaml}
date_retrieved: {today}
model: {model}
tokens:
  prompt: {tokens["prompt_tokens"]}
  candidates: {tokens["candidates_tokens"]}
  total: {tokens["total_tokens"]}
{format_sources_yaml(sources)}
tags: []
---"""

    sources_section = ""
    if sources:
        sources_section = "\n\n## Sources\n"
        for i, s in enumerate(sources, 1):
            sources_section += f'\n{i}. [{s["title"]}]({s["url"]})'

    return f"""{frontmatter}

# {query}

{response_text}
{sources_section}
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def search(query: str, extra_prompt: str | None = None) -> Path:
    """Run a grounded Gemini search and save results as markdown."""
    load_dotenv()

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY not set. Add it to .env or export it.", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    prompt = query
    if extra_prompt:
        prompt = f"{query}\n\nAdditional instructions: {extra_prompt}"

    response = client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )

    # Extract metadata
    metadata = None
    if response.candidates and response.candidates[0].grounding_metadata:
        metadata = response.candidates[0].grounding_metadata

    raw_text = response.text or ""
    text_with_citations = build_inline_citations(raw_text, metadata)
    sources = extract_sources(metadata)
    # Empty list (not a fallback to [query]) when metadata missing — cleaner audit
    search_queries = (
        list(metadata.web_search_queries)
        if metadata and metadata.web_search_queries
        else []
    )
    tokens = extract_token_usage(response)

    # Resolve Google grounding redirect URLs to their final destinations so the
    # wiki cites real domains (and the file size drops dramatically).
    all_urls = [s["url"] for s in sources]
    url_map = resolve_urls(all_urls)
    for s in sources:
        s["url"] = url_map.get(s["url"], s["url"])
    text_with_citations = apply_url_map(text_with_citations, url_map)

    # Write file
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{kebab(query)}.md"
    filepath = OUTPUT_DIR / filename

    # Avoid overwriting — append a counter if file exists
    counter = 1
    while filepath.exists():
        counter += 1
        filepath = OUTPUT_DIR / f"{kebab(query)}-{counter}.md"

    content = format_markdown(query, text_with_citations, sources, search_queries, tokens, MODEL)
    filepath.write_text(content, encoding="utf-8")

    # Append per-call token usage to JSONL audit log
    append_token_log(query, filepath, tokens, MODEL)

    return filepath


def backfill_file(path: Path) -> tuple[int, int, int]:
    """Resolve all redirect URLs in an existing search file in-place.

    Returns (urls_found, urls_resolved, bytes_saved).
    """
    text = path.read_text(encoding="utf-8")
    before_size = len(text.encode("utf-8"))

    # Find every redirect URL in the file (frontmatter + body + Sources section)
    pattern = rf"https://{re.escape(REDIRECT_HOST)}/[^\s\)\"\']+"
    found = re.findall(pattern, text)
    if not found:
        return (0, 0, 0)

    url_map = resolve_urls(found)
    resolved_count = sum(
        1 for orig, resolved in url_map.items() if resolved and resolved != orig
    )

    new_text = apply_url_map(text, url_map)
    after_size = len(new_text.encode("utf-8"))
    path.write_text(new_text, encoding="utf-8")

    return (len(set(found)), resolved_count, before_size - after_size)


def main():
    parser = argparse.ArgumentParser(description="Gemini grounded search → markdown")
    parser.add_argument("query", nargs="?", help="Search query (omit when using --backfill)")
    parser.add_argument("--prompt", help="Additional prompt instructions for Gemini", default=None)
    parser.add_argument(
        "--backfill",
        metavar="FILE",
        help="Resolve redirect URLs in an existing search file in-place (no API call)",
    )
    args = parser.parse_args()

    if args.backfill:
        target = Path(args.backfill)
        if not target.is_file():
            print(f"ERROR: {target} not found", file=sys.stderr)
            sys.exit(1)
        found, resolved, saved = backfill_file(target)
        print(target)
        print(
            f"[backfill] urls_found={found} resolved={resolved} bytes_saved={saved}",
            file=sys.stderr,
        )
        return

    if not args.query:
        parser.error("query is required unless --backfill is given")

    filepath = search(args.query, args.prompt)
    # Print path so the calling agent knows where to find the file
    print(filepath)
    # Print a one-line token summary on stderr so the agent can capture cost without polluting stdout
    try:
        with TOKEN_LOG.open("r", encoding="utf-8") as f:
            last_line = f.readlines()[-1]
        entry = json.loads(last_line)
        print(
            f"[tokens] prompt={entry['prompt_tokens']} candidates={entry['candidates_tokens']} total={entry['total_tokens']}",
            file=sys.stderr,
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()
