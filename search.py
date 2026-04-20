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
import os
import re
import sys
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MODEL = "gemini-2.5-flash"
OUTPUT_DIR = Path(__file__).parent / "raw" / "searches"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def kebab(text: str, max_len: int = 80) -> str:
    """Convert text to kebab-case filename."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text[:max_len]


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


def format_markdown(
    query: str,
    response_text: str,
    sources: list[dict],
    search_queries: list[str],
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
    search_queries = list(metadata.web_search_queries) if metadata and metadata.web_search_queries else [query]

    # Write file
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{kebab(query)}.md"
    filepath = OUTPUT_DIR / filename

    # Avoid overwriting — append a counter if file exists
    counter = 1
    while filepath.exists():
        counter += 1
        filepath = OUTPUT_DIR / f"{kebab(query)}-{counter}.md"

    content = format_markdown(query, text_with_citations, sources, search_queries)
    filepath.write_text(content, encoding="utf-8")

    return filepath


def main():
    parser = argparse.ArgumentParser(description="Gemini grounded search → markdown")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--prompt", help="Additional prompt instructions for Gemini", default=None)
    args = parser.parse_args()

    filepath = search(args.query, args.prompt)
    # Print path so the calling agent knows where to find the file
    print(filepath)


if __name__ == "__main__":
    main()
