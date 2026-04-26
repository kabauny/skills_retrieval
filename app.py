"""
Wiki LM — Streamlit MVP.

Capabilities:
  1. Ask questions of the wiki
  2. Internet fallback when wiki is insufficient (Gemini grounded search)
  3. Audit-back-to-wiki: every query writes structured entries to log.md +
     avatar/{user}/questions.md
  4. Agent generates multiple-choice preference probes for clinical equipoise
  5. Preferences captured to avatar/{user}/decisions.md

Extensions (this version):
  A. Persistent chat transcript — turns saved to raw/sessions/{user}-{date}.jsonl,
     reloaded on startup
  B. Grounded searches saved to raw/searches/ via shared search.py helpers
     (URL resolution + token tracking + frontmatter exactly like agent-driven
     search.py)
  C. Auto-ingest novel entities from grounded answers as stub pages with
     `auto_generated: true` frontmatter, indexed in wiki/index.md, logged in
     wiki/log.md

Run:
    streamlit run app.py
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Reuse search.py helpers for the raw/searches save (URL resolution, citation
# insertion, frontmatter, token logging — same format as agent-driven searches)
from search import (
    OUTPUT_DIR as SEARCH_OUTPUT_DIR,
    append_token_log,
    apply_url_map,
    build_inline_citations,
    extract_sources,
    extract_token_usage,
    format_markdown,
    kebab,
    resolve_urls,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent
WIKI = ROOT / "wiki"
RAW = ROOT / "raw"
SESSIONS_DIR = RAW / "sessions"

# Two-model split: Pro for heavy reasoning, Flash for light structured tasks.
# - Pro: wiki + internet synthesis, MC preference probe (clinical reasoning + avatar quality)
# - Flash: page routing, entity extraction (pattern-matching + structured output)
MODEL_PRO = "gemini-3.1-pro-preview"
MODEL_FLASH = "gemini-2.5-flash"
DEFAULT_USER = "jim.chen"

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

load_dotenv()
_api_key = os.environ.get("GOOGLE_API_KEY")
if not _api_key:
    st.set_page_config(page_title="Wiki LM", layout="wide")
    st.error("GOOGLE_API_KEY not set. Add it to .env and restart.")
    st.stop()

_client = genai.Client(api_key=_api_key)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class TokenUsage:
    prompt: int = 0
    candidates: int = 0
    total: int = 0

    def __add__(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            prompt=self.prompt + other.prompt,
            candidates=self.candidates + other.candidates,
            total=self.total + other.total,
        )


@dataclass
class MCQuestion:
    label: str
    question: str
    options: list[dict]
    rationale: str
    captured: bool = False


@dataclass
class Turn:
    idx: int
    question: str
    answer: str
    sources: list[str] = field(default_factory=list)
    origin: str = "wiki"  # "wiki" | "internet" | "mixed"
    gemini_calls: int = 0
    tokens: TokenUsage = field(default_factory=TokenUsage)
    mc: MCQuestion | None = None
    saved_search_path: str | None = None  # raw/searches/{slug}.md if grounded
    stubs_created: list[str] = field(default_factory=list)  # paths to stub pages


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tokens(response) -> TokenUsage:
    usage = getattr(response, "usage_metadata", None)
    if not usage:
        return TokenUsage()
    return TokenUsage(
        prompt=getattr(usage, "prompt_token_count", 0) or 0,
        candidates=getattr(usage, "candidates_token_count", 0) or 0,
        total=getattr(usage, "total_token_count", 0) or 0,
    )


def _extract_json(text: str):
    """Pull the first JSON array or object from a model response."""
    for pattern in (r"\[.*\]", r"\{.*\}"):
        m = re.search(pattern, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                continue
    return None


# ---------------------------------------------------------------------------
# Wiki retrieval
# ---------------------------------------------------------------------------


def _read_index() -> str:
    return (WIKI / "index.md").read_text(encoding="utf-8")


def _list_wiki_pages() -> list[Path]:
    pages: list[Path] = []
    for p in WIKI.rglob("*.md"):
        if any(part.startswith(".") for part in p.parts):
            continue
        if "avatar" in p.parts:
            continue
        pages.append(p)
    return pages


def _list_wiki_page_filenames() -> list[str]:
    return sorted({p.stem for p in _list_wiki_pages()})


def _load_pages(filenames: list[str]) -> dict[str, str]:
    contents: dict[str, str] = {}
    for f in filenames:
        for path in WIKI.rglob(f"{f}.md"):
            if "avatar" in path.parts:
                continue
            try:
                contents[f] = path.read_text(encoding="utf-8")
                break
            except OSError:
                continue
    return contents


def select_relevant_pages(query: str) -> tuple[list[str], TokenUsage]:
    index = _read_index()
    prompt = f"""You are a wiki retrieval router. Given the user's question and the wiki index below, list the page filenames (without paths or .md extension) most relevant to answering the question.

Return STRICTLY a JSON array of strings — page filenames only. Maximum 8. If no pages are relevant, return [].

QUESTION:
{query}

WIKI INDEX:
{index}
"""
    resp = _client.models.generate_content(model=MODEL_FLASH, contents=prompt)
    parsed = _extract_json(resp.text or "")
    pages = parsed if isinstance(parsed, list) else []
    valid: list[str] = []
    for p in pages:
        if isinstance(p, str) and list(WIKI.rglob(f"{p}.md")):
            valid.append(p)
    return valid, _tokens(resp)


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------


_WIKI_ONLY_INSTRUCTIONS = """You are a clinical knowledge assistant answering strictly from the provided wiki pages. Do not use external knowledge.

If the wiki does NOT contain enough information to answer the question well, respond with EXACTLY this token on its own line at the start: INSUFFICIENT_WIKI_DATA

After the verdict, briefly explain what is missing.

If the wiki IS sufficient:
  - Give a clear, structured answer
  - Use [[wiki-page-name]] inline citations for every factual claim
  - Cite only pages that actually appear in the input below — do NOT invent page names
  - End with a short "Sources" line listing the pages cited
"""


def synthesize_wiki_answer(query: str, page_contents: dict[str, str]) -> tuple[str, bool, TokenUsage]:
    if not page_contents:
        return (
            "INSUFFICIENT_WIKI_DATA\nNo relevant wiki pages were found for this question.",
            False,
            TokenUsage(),
        )
    pages_text = "\n\n---\n\n".join(
        f"## wiki/{name}\n\n{content}" for name, content in page_contents.items()
    )
    prompt = f"""{_WIKI_ONLY_INSTRUCTIONS}

QUESTION:
{query}

WIKI PAGES:
{pages_text}
"""
    resp = _client.models.generate_content(model=MODEL_PRO, contents=prompt)
    answer = (resp.text or "").strip()
    sufficient = not answer.upper().startswith("INSUFFICIENT_WIKI_DATA")
    return answer, sufficient, _tokens(resp)


def synthesize_internet_answer(query: str, page_contents: dict[str, str]):
    """Returns (answer, raw_response, tokens). Raw response is needed for raw/searches save."""
    pages_text = (
        "\n\n---\n\n".join(f"## wiki/{name}\n\n{content}" for name, content in page_contents.items())
        if page_contents
        else "(no relevant wiki pages found)"
    )
    prompt = f"""You are a clinical knowledge assistant. The internal wiki was insufficient for this question. Answer using a combination of the wiki context (where present) AND web search.

Mark every claim with provenance:
  - [[wiki-page-name]] for claims drawn from the wiki context
  - [search-sourced] for claims drawn from web search

Do NOT invent wiki citations. Only cite pages that appear in the wiki context.

End with a short "Sources" line listing the wiki pages cited (if any) and noting web search was used.

QUESTION:
{query}

WIKI CONTEXT:
{pages_text}
"""
    resp = _client.models.generate_content(
        model=MODEL_PRO,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    return (resp.text or "").strip(), resp, _tokens(resp)


# ---------------------------------------------------------------------------
# (B) Save grounded responses to raw/searches/ — same format as search.py
# ---------------------------------------------------------------------------


def save_grounded_response_to_raw(query: str, response, model: str) -> Path | None:
    """Use search.py helpers to write a grounded response as a clean source file.

    Same artifact format as agent-driven `python search.py "..."`:
    YAML frontmatter (including token counts and resolved sources), inline
    citations, numbered Sources section, append to _token_log.jsonl.
    """
    metadata = None
    if response.candidates and response.candidates[0].grounding_metadata:
        metadata = response.candidates[0].grounding_metadata

    raw_text = response.text or ""
    text_with_cites = build_inline_citations(raw_text, metadata)
    sources = extract_sources(metadata)
    if not sources:
        # No grounding chunks returned — likely the model didn't actually search.
        # Still save with no sources rather than nothing, for audit completeness.
        pass

    search_queries = (
        list(metadata.web_search_queries)
        if metadata and metadata.web_search_queries
        else []
    )
    tokens = extract_token_usage(response)

    # Resolve Google grounding redirect URLs (slow but matches search.py output)
    if sources:
        all_urls = [s["url"] for s in sources]
        url_map = resolve_urls(all_urls)
        for s in sources:
            s["url"] = url_map.get(s["url"], s["url"])
        text_with_cites = apply_url_map(text_with_cites, url_map)

    SEARCH_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    filepath = SEARCH_OUTPUT_DIR / f"{kebab(query)}.md"
    counter = 1
    while filepath.exists():
        counter += 1
        filepath = SEARCH_OUTPUT_DIR / f"{kebab(query)}-{counter}.md"

    content = format_markdown(query, text_with_cites, sources, search_queries, tokens, model)
    filepath.write_text(content, encoding="utf-8")
    append_token_log(query, filepath, tokens, model)
    return filepath


# ---------------------------------------------------------------------------
# (C) Auto-ingest: extract entities → write stub pages → update index + log
# ---------------------------------------------------------------------------


_ENTITY_EXTRACT_PROMPT = """You analyze a clinical query and its grounded answer. Identify NOVEL named entities mentioned in the answer that are NOT already represented in the wiki page list provided.

Categories:
  - drug (e.g., trastuzumab, pembrolizumab)
  - trial (e.g., DESTINY-Breast05, KATHERINE)
  - cancer (e.g., HER2-positive breast cancer)
  - biomarker (e.g., HER2, ctDNA, TMB)
  - concept (mechanisms, paradigms, decision frameworks)

Skip:
  - Anything already in the wiki page list (provided)
  - Vague references without enough info to populate a stub
  - Entities mentioned only in passing without clinical content

Each NOVEL entity, return a JSON object:
{{
  "name": "<official name>",
  "filename": "<kebab-case, no .md, no path>",
  "type": "drug" | "trial" | "cancer" | "biomarker" | "concept",
  "brief": "<1-2 sentence summary based on the answer>",
  "aliases": [<alternative names>],
  "relevance": "<one short sentence on why this matters in oncology>"
}}

Return STRICTLY a JSON array, max 5 entities. If nothing novel, return [].

EXISTING WIKI PAGES (do NOT duplicate any of these):
{existing}

QUERY:
{query}

ANSWER:
{answer}
"""


def extract_novel_entities(query: str, answer: str) -> tuple[list[dict], TokenUsage]:
    existing = ", ".join(_list_wiki_page_filenames())
    prompt = _ENTITY_EXTRACT_PROMPT.format(existing=existing, query=query, answer=answer)
    resp = _client.models.generate_content(model=MODEL_FLASH, contents=prompt)
    parsed = _extract_json(resp.text or "")
    if not isinstance(parsed, list):
        return [], _tokens(resp)
    valid: list[dict] = []
    for e in parsed:
        if not isinstance(e, dict):
            continue
        if not e.get("name") or not e.get("filename"):
            continue
        valid.append(e)
    return valid[:5], _tokens(resp)


def write_entity_stub(entity: dict, source_filename: str) -> Path | None:
    """Write a stub entity/concept page with auto_generated frontmatter. Skip on filename collision."""
    name = entity.get("name", "Untitled").strip()
    filename = (entity.get("filename") or kebab(name)).strip()
    if not filename:
        return None
    typ = entity.get("type", "concept")
    brief = entity.get("brief", "(stub — auto-generated, expand when verified)").strip()
    aliases = entity.get("aliases") or []
    relevance = entity.get("relevance", "").strip()

    folder = "entities" if typ in ("drug", "trial", "cancer", "biomarker") else "concepts"
    target_dir = WIKI / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{filename}.md"

    if target_path.exists():
        return None  # never overwrite an existing page from auto-ingest

    aliases_yaml = json.dumps(aliases) if aliases else "[]"
    entity_type_field = typ if typ != "concept" else "other"
    source_stem = Path(source_filename).stem

    body = f"""---
title: "{name}"
entity_type: {entity_type_field}
aliases: {aliases_yaml}
auto_generated: true
auto_source: "[[{source_stem}]]"
auto_date: {date.today().isoformat()}
tags: [auto-generated]
---

# {name}

> ⚠️ **Auto-generated stub** from a UI-driven grounded search. Verify and expand before relying on this for clinical decisions. The agent ingest workflow can promote this stub to a full entity/concept page.

## Brief

{brief}

## Why this matters

{relevance if relevance else "(not specified)"}

## Sources

- [[{source_stem}]] — origin search; see for full grounded citations and search queries
"""
    target_path.write_text(body, encoding="utf-8")
    return target_path


_AUTO_INGEST_INDEX_HEADER = "## Auto-generated stubs (UI-driven)"


def update_index_with_stubs(stubs: list[Path]) -> None:
    if not stubs:
        return
    index = WIKI / "index.md"
    if not index.exists():
        return
    text = index.read_text(encoding="utf-8")

    new_lines = []
    for stub in stubs:
        # Read frontmatter title for display
        content = stub.read_text(encoding="utf-8")
        m = re.search(r'^title:\s*"?([^"\n]+)"?', content, re.MULTILINE)
        title = (m.group(1) if m else stub.stem).strip()
        kind = stub.parent.name
        new_lines.append(f"- [[{stub.stem}]] — *(auto stub, {kind})* {title}")

    if _AUTO_INGEST_INDEX_HEADER not in text:
        block = (
            f"\n\n{_AUTO_INGEST_INDEX_HEADER}\n\n"
            + "\n".join(new_lines)
            + "\n\n*These pages were auto-generated from UI grounded searches. They need agent review and promotion before clinical use.*\n"
        )
        text = text.rstrip() + block
    else:
        # Insert after the header marker, preserving the rest
        marker = _AUTO_INGEST_INDEX_HEADER
        idx = text.index(marker)
        # Find the first blank-line + bullet block immediately following the header
        # We just insert a new block right after the header line
        line_end = text.index("\n", idx)
        insertion = "\n" + "\n".join(new_lines)
        text = text[: line_end + 1] + "\n" + insertion + "\n" + text[line_end + 1 :].lstrip("\n")

    index.write_text(text, encoding="utf-8")


def append_auto_ingest_log(stubs: list[Path], source_path: Path, query: str, user: str) -> None:
    if not stubs:
        return
    today = date.today().isoformat()
    pages_list = "\n".join(f"  - [[{s.stem}]] ({s.parent.name})" for s in stubs)
    entry = f"""
## [{today}] auto-ingest | UI grounded search → stub pages

- **User:** {user}
- **Triggering query:** "{query[:100]}{'...' if len(query) > 100 else ''}"
- **Source saved:** [[{source_path.stem}]]
- **Stub pages created ({len(stubs)}):**
{pages_list}
- **Note:** AUTO-GENERATED stubs from a UI grounded search. Marked `auto_generated: true` in frontmatter. Agent review and promotion to full entity/concept pages is recommended before clinical use.
"""
    log = WIKI / "log.md"
    if log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(entry)


# ---------------------------------------------------------------------------
# Preference elicitation
# ---------------------------------------------------------------------------


_MC_PROMPT = """You design preference probes to elicit a clinician's avatar — their decision style across cases.

For ALMOST ANY clinically-relevant question (informational, "how do you", or explicit decision), generate ONE multiple-choice question (2–4 options) that probes how the user would APPLY this knowledge to a patient.

Reframing rules:

- "Tell me about X" / "What's the data on Y" → "If you had a patient with [a typical scenario from the answer], would you favor X or Y?"
- "How do you select X vs Y" / "What's the role of Z" → "For [a specific patient profile mentioned in the answer], which would you choose?"
- "Should I do X for this patient?" → MC directly with the at-hand options
- Even when the answer describes a settled standard of care, surface a NUANCE (timing, sequencing, escalation thresholds, edge-case patient profiles) where reasonable clinicians could differ.

Each option must be:
- Defensible on the available evidence
- Genuinely distinct (different weighting of trade-offs — toxicity vs efficacy, off-label comfort, guideline conformity, fertility/QoL preference, etc.)
- Realistic (something a clinician might actually do)

Return STRICTLY a single JSON object:
{{
  "label": "<short kebab-case label, ≤40 chars>",
  "question": "<the MC question — frame as applied to a hypothetical or general patient profile, not as 'what do you want to know'>",
  "options": [
    {{"key": "A", "text": "<option A — concrete clinical action>"}},
    {{"key": "B", "text": "<option B>"}}
  ],
  "rationale": "<one sentence on what this MC reveals about the user's preferences — e.g., 'tests whether the user weighs CNS activity over ILD risk in adjuvant HER2-directed selection'>"
}}

Skip ONLY if the question is so trivial there is no clinical judgment in any direction (e.g., "what does AMH stand for?", "list the breast cancer subtypes"). In that case return EXACTLY:
{{"label": null}}

QUESTION:
{question}

ANSWER:
{answer}
"""


def generate_preference_mc(query: str, answer: str) -> tuple[MCQuestion | None, TokenUsage]:
    resp = _client.models.generate_content(
        model=MODEL_PRO, contents=_MC_PROMPT.format(question=query, answer=answer)
    )
    parsed = _extract_json(resp.text or "")
    if not isinstance(parsed, dict) or not parsed.get("label"):
        return None, _tokens(resp)
    try:
        return (
            MCQuestion(
                label=str(parsed["label"]),
                question=str(parsed["question"]),
                options=list(parsed.get("options") or []),
                rationale=str(parsed.get("rationale", "")),
            ),
            _tokens(resp),
        )
    except (KeyError, TypeError):
        return None, _tokens(resp)


# ---------------------------------------------------------------------------
# Audit / capture
# ---------------------------------------------------------------------------


def _ensure_avatar_files(user: str) -> tuple[Path, Path]:
    avatar = WIKI / "avatar" / user
    avatar.mkdir(parents=True, exist_ok=True)
    questions = avatar / "questions.md"
    decisions = avatar / "decisions.md"
    if not questions.exists():
        questions.write_text(
            f"---\nuser: {user}\ntitle: \"Questions — {user}\"\n---\n\n# Questions — {user}\n\n*Auto-populated by the wiki UI.*\n",
            encoding="utf-8",
        )
    if not decisions.exists():
        decisions.write_text(
            f"---\nuser: {user}\ntitle: \"Decisions — {user}\"\n---\n\n# Decisions — {user}\n\n*Auto-populated by the wiki UI.*\n",
            encoding="utf-8",
        )
    return questions, decisions


def append_question_log(turn: Turn, user: str) -> None:
    today = date.today().isoformat()
    sources_str = ", ".join(f"[[{s}]]" for s in turn.sources) if turn.sources else "none"
    safe_label = re.sub(r"[^a-z0-9]+", "-", turn.question.lower()).strip("-")[:60]

    extras = ""
    if turn.saved_search_path:
        extras += f"\n- **Search saved:** [[{Path(turn.saved_search_path).stem}]]"
    if turn.stubs_created:
        stub_links = ", ".join(f"[[{Path(s).stem}]]" for s in turn.stubs_created)
        extras += f"\n- **Stub pages auto-created:** {stub_links}"

    log_entry = f"""
## [{today}] query | {turn.question[:70]}{'...' if len(turn.question) > 70 else ''}

- **User:** {user}
- **Question:** "{turn.question}"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** {sources_str}
- **Gemini calls:** {turn.gemini_calls}
- **Answer origin:** {turn.origin}
- **Tokens (Gemini):** {turn.tokens.total}{extras}
"""
    questions_entry = f"""
### [{today}] {safe_label}

- **Question:** "{turn.question}"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** {sources_str}
- **Gemini calls:** {turn.gemini_calls}
- **Answer origin:** {turn.origin}
- **Tokens (Gemini):** {turn.tokens.total}
- **MC probe generated:** {"yes — " + turn.mc.label if turn.mc else "no"}{extras}
"""

    log = WIKI / "log.md"
    if log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(log_entry)

    questions, _ = _ensure_avatar_files(user)
    with questions.open("a", encoding="utf-8") as f:
        f.write(questions_entry)


def append_preference_capture(
    user: str, mc: MCQuestion, choice_key: str, reasoning: str, source_question: str
) -> None:
    today = date.today().isoformat()
    chosen = next((o for o in mc.options if o["key"] == choice_key), None)
    chosen_text = chosen["text"] if chosen else "(unknown)"
    options_block = "\n".join(f"  - {o['key']}. {o['text']}" for o in mc.options)
    entry = f"""
### [{today}] {mc.label} (UI preference capture)

- **Surfaced from question:** "{source_question}"
- **Probe:** {mc.question}
- **Options offered:**
{options_block}
- **Choice:** {choice_key} — {chosen_text}
- **Reasoning:** {reasoning if reasoning else "(not specified)"}
- **What this reveals:** {mc.rationale or "(no rationale supplied)"}
"""
    _, decisions = _ensure_avatar_files(user)
    with decisions.open("a", encoding="utf-8") as f:
        f.write(entry)


# ---------------------------------------------------------------------------
# (A) Session persistence
# ---------------------------------------------------------------------------


def session_file_for(user: str) -> Path:
    return SESSIONS_DIR / f"{user}-{date.today().isoformat()}.jsonl"


def _turn_to_dict(turn: Turn) -> dict:
    return {
        "idx": turn.idx,
        "ts": datetime.now(timezone.utc).isoformat(),
        "question": turn.question,
        "answer": turn.answer,
        "sources": list(turn.sources),
        "origin": turn.origin,
        "gemini_calls": turn.gemini_calls,
        "tokens": asdict(turn.tokens),
        "mc": (
            {
                "label": turn.mc.label,
                "question": turn.mc.question,
                "options": turn.mc.options,
                "rationale": turn.mc.rationale,
                "captured": turn.mc.captured,
            }
            if turn.mc
            else None
        ),
        "saved_search_path": turn.saved_search_path,
        "stubs_created": list(turn.stubs_created),
    }


def _turn_from_dict(d: dict) -> Turn:
    mc = None
    if d.get("mc"):
        mc = MCQuestion(
            label=d["mc"]["label"],
            question=d["mc"]["question"],
            options=d["mc"]["options"],
            rationale=d["mc"].get("rationale", ""),
            captured=d["mc"].get("captured", False),
        )
    tk = d.get("tokens") or {}
    return Turn(
        idx=d["idx"],
        question=d["question"],
        answer=d["answer"],
        sources=list(d.get("sources") or []),
        origin=d.get("origin", "wiki"),
        gemini_calls=d.get("gemini_calls", 0),
        tokens=TokenUsage(
            prompt=tk.get("prompt", 0),
            candidates=tk.get("candidates", 0),
            total=tk.get("total", 0),
        ),
        mc=mc,
        saved_search_path=d.get("saved_search_path"),
        stubs_created=list(d.get("stubs_created") or []),
    )


def append_turn_to_session(turn: Turn, user: str) -> None:
    f = session_file_for(user)
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a", encoding="utf-8") as h:
        h.write(json.dumps(_turn_to_dict(turn)) + "\n")


def load_today_session(user: str) -> list[Turn]:
    f = session_file_for(user)
    if not f.exists():
        return []
    turns: list[Turn] = []
    with f.open("r", encoding="utf-8") as h:
        for line in h:
            line = line.strip()
            if not line:
                continue
            try:
                turns.append(_turn_from_dict(json.loads(line)))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    return turns


# ---------------------------------------------------------------------------
# Query orchestration
# ---------------------------------------------------------------------------


def run_query_phase1(question: str, user: str):
    """Synchronous phase: route, synthesize, generate MC. Produces the user-facing answer.

    Returns (Turn, grounded_response_or_None).
    If grounded_response is not None, phase 2 (save + auto-ingest) is needed.
    """
    total_tokens = TokenUsage()
    gemini_calls = 0

    # 1. Route to relevant wiki pages (Flash)
    pages, t1 = select_relevant_pages(question)
    total_tokens = total_tokens + t1
    gemini_calls += 1

    # 2. Try wiki-only synthesis (Pro)
    page_contents = _load_pages(pages)
    answer, sufficient, t2 = synthesize_wiki_answer(question, page_contents)
    total_tokens = total_tokens + t2
    gemini_calls += 1

    origin = "wiki"
    grounded_resp = None

    if not sufficient:
        # 3. Internet fallback (grounded search synthesis, Pro)
        answer, grounded_resp, t3 = synthesize_internet_answer(question, page_contents)
        total_tokens = total_tokens + t3
        gemini_calls += 1
        origin = "internet" if not page_contents else "mixed"

    # 4. Generate MC preference probe (Pro)
    mc, t4 = generate_preference_mc(question, answer)
    total_tokens = total_tokens + t4
    gemini_calls += 1

    turn = Turn(
        idx=len(st.session_state.history),
        question=question,
        answer=answer,
        sources=pages,
        origin=origin,
        gemini_calls=gemini_calls,
        tokens=total_tokens,
        mc=mc,
        saved_search_path=None,
        stubs_created=[],
    )
    return turn, grounded_resp


def run_query_phase2(turn: Turn, grounded_resp, question: str, user: str, auto_ingest_enabled: bool) -> Turn:
    """Deferred phase: save grounded response + auto-ingest. Mutates and returns the Turn.

    Runs AFTER the answer has rendered, so the user is reading while this happens.
    """
    # B. Save grounded response → raw/searches/{slug}.md
    try:
        saved_path = save_grounded_response_to_raw(question, grounded_resp, MODEL_PRO)
        if saved_path:
            turn.saved_search_path = str(saved_path)
    except Exception as exc:
        st.warning(f"Grounded response save failed: {type(exc).__name__}: {exc}")

    # C. Auto-ingest novel entities (Flash)
    if auto_ingest_enabled and turn.saved_search_path:
        try:
            entities, te = extract_novel_entities(question, turn.answer)
            turn.tokens = turn.tokens + te
            turn.gemini_calls += 1
            created: list[Path] = []
            for entity in entities:
                p = write_entity_stub(entity, turn.saved_search_path)
                if p:
                    created.append(p)
            if created:
                update_index_with_stubs(created)
                append_auto_ingest_log(created, Path(turn.saved_search_path), question, user)
            turn.stubs_created = [str(p) for p in created]
        except Exception as exc:
            st.warning(f"Auto-ingest failed: {type(exc).__name__}: {exc}")

    return turn


# ---------------------------------------------------------------------------
# Cases — concept pages with Decision skeletons → captureable case decisions
# ---------------------------------------------------------------------------


_DECISION_SKELETON_RE = re.compile(
    r"^##\s+Decision skeleton[^\n]*\n(.*?)(?=\n##\s|\Z)",
    re.DOTALL | re.MULTILINE,
)
_OPTION_RE = re.compile(
    r"\*\*Option\s+(\d+|[A-Z])\s*[—–-]\s*([^\*]+?)\*\*\s*\n(.*?)(?=\n\*\*Option\s+\d|\n##\s|\Z)",
    re.DOTALL,
)


def find_decision_skeleton_pages() -> list[dict]:
    """Scan wiki/concepts/ for pages with a `## Decision skeleton` section.

    Returns a list of dicts:
        {
          "stem": "intermediate-rs-premenopausal-hr-positive-management",
          "title": "Intermediate-RS premenopausal HR+/HER2− adjuvant management",
          "path": Path,
          "skeleton": "<extracted skeleton section text>",
          "options": [{"key": "A", "title": "...", "details": "..."}, ...] (may be empty)
        }
    """
    out: list[dict] = []
    concepts_dir = WIKI / "concepts"
    if not concepts_dir.exists():
        return out
    for p in sorted(concepts_dir.glob("*.md")):
        try:
            content = p.read_text(encoding="utf-8")
        except OSError:
            continue
        m = _DECISION_SKELETON_RE.search(content)
        if not m:
            continue
        skeleton = m.group(1).strip()
        # Title from frontmatter
        fm, _body = parse_frontmatter(content)
        title = fm.get("title", p.stem).strip().strip('"').strip("'")
        # Try to parse options — format: **Option N — Name**\n<bullets>
        options: list[dict] = []
        for opt_m in _OPTION_RE.finditer(skeleton):
            key_raw = opt_m.group(1)
            # Map "1" → "A", "2" → "B", etc., or pass through if already letter
            if key_raw.isdigit():
                key = chr(ord("A") + int(key_raw) - 1)
            else:
                key = key_raw
            options.append({
                "key": key,
                "title": opt_m.group(2).strip(),
                "details": opt_m.group(3).strip(),
            })
        out.append({
            "stem": p.stem,
            "title": title,
            "path": p,
            "skeleton": skeleton,
            "options": options,
        })
    return out


def case_already_captured(user: str, case_stem: str) -> bool:
    """Has this case already been captured for this user? Avoid duplicate prompts."""
    decisions_file = WIKI / "avatar" / user / "decisions.md"
    if not decisions_file.exists():
        return False
    try:
        content = decisions_file.read_text(encoding="utf-8")
    except OSError:
        return False
    # Match the case_stem appearing as a "Linked concept" or label suffix
    return f"linked-concept:{case_stem}" in content or f"case:{case_stem}" in content


def append_case_decision(
    user: str,
    case: dict,
    decision_key: str,
    decision_text: str,
    reasoning: str,
    confidence: str,
    wiki_tension: str,
) -> None:
    """Write a rich case-decision entry to decisions.md (matches agent-mediated format)."""
    today = date.today().isoformat()
    options_block = (
        "\n".join(f"  - **{o['key']}.** {o['title']}" for o in case.get("options") or [])
        if case.get("options")
        else "  - *(free-form decision; see Decision skeleton on linked concept)*"
    )
    safe_label = re.sub(r"[^a-z0-9]+", "-", case["stem"].lower()).strip("-")[:60]

    entry = f"""
### [{today}] {case['title']} (case mode capture, case:{case['stem']})

- **Source concept:** [[{case['stem']}]]
- **Scenario:** {case['title']} — captured via the Cases tab in the Streamlit UI.
- **Options considered:**
{options_block}
- **Decision:** {decision_key} — {decision_text}
- **Reasoning:** {reasoning if reasoning else "(not specified)"}
- **Confidence:** {confidence}
- **Wiki tension noted:** {wiki_tension if wiki_tension else "(none flagged by user)"}
- **linked-concept:{case['stem']}**
"""

    _, decisions = _ensure_avatar_files(user)
    with decisions.open("a", encoding="utf-8") as f:
        f.write(entry)

    # Also log to wiki/log.md for audit
    log = WIKI / "log.md"
    if log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(
                f"\n## [{today}] case-decision | {case['stem']}\n\n"
                f"- **User:** {user}\n"
                f"- **Concept:** [[{case['stem']}]]\n"
                f"- **Decision:** {decision_key} — {decision_text}\n"
                f"- **Confidence:** {confidence}\n"
                f"- **Captured via:** Cases tab (Streamlit UI)\n"
            )


# ---------------------------------------------------------------------------
# Review (auto-generated stubs + saved searches)
# ---------------------------------------------------------------------------


def list_auto_generated_pages() -> list[Path]:
    """Find every wiki page with `auto_generated: true` in frontmatter, mtime-sorted desc."""
    matches: list[Path] = []
    for p in WIKI.rglob("*.md"):
        if any(part.startswith(".") for part in p.parts):
            continue
        if "avatar" in p.parts:
            continue
        try:
            head = p.read_text(encoding="utf-8")[:600]
        except OSError:
            continue
        if re.search(r"^auto_generated:\s*true\b", head, re.MULTILINE):
            matches.append(p)
    matches.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return matches


def list_recent_searches(limit: int = 50) -> list[Path]:
    """Return the most recent files in raw/searches/, mtime-sorted desc."""
    if not SEARCH_OUTPUT_DIR.exists():
        return []
    files = [
        p for p in SEARCH_OUTPUT_DIR.glob("*.md")
        if not p.name.startswith("_")
    ]
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return files[:limit]


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Crude YAML frontmatter parse — enough for our generated stubs."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm_block = text[4:end]
    body = text[end + 5 :]
    fm: dict = {}
    for line in fm_block.splitlines():
        m = re.match(r"^([a-zA-Z_][\w-]*):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        fm[key] = val
    return fm, body


def promote_stub(path: Path, user: str) -> bool:
    """Strip `auto_generated: true` and `auto-generated` tag. Log promotion."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False

    new_text = re.sub(r"^auto_generated:\s*true\s*\n", "", text, flags=re.MULTILINE)
    # Remove the auto-generated tag from `tags: [...]` if present
    new_text = re.sub(
        r"^(tags:\s*\[)([^\]]*)(\])",
        lambda m: m.group(1)
        + ", ".join(t.strip() for t in m.group(2).split(",") if t.strip() and t.strip() != "auto-generated")
        + m.group(3),
        new_text,
        flags=re.MULTILINE,
    )

    # Strip the warning callout block if present (top of body)
    new_text = re.sub(
        r"\n>\s*⚠️\s*\*\*Auto-generated stub\*\*[^\n]*\n(?:>[^\n]*\n)*",
        "\n",
        new_text,
    )

    path.write_text(new_text, encoding="utf-8")

    today = date.today().isoformat()
    log = WIKI / "log.md"
    if log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(
                f"\n## [{today}] promote | {path.stem}\n\n"
                f"- **User:** {user}\n"
                f"- **Page:** [[{path.stem}]] ({path.parent.name})\n"
                f"- **Action:** stripped `auto_generated: true` flag and warning callout — page is now treated as reviewed/promoted.\n"
                f"- **Reminder:** consider running an agent ingest to expand to full SCHEMA structure (Overview, Key facts, Related entities, Sources).\n"
            )
    return True


def reject_stub(path: Path, user: str, reason: str = "") -> bool:
    """Delete the stub page. Append a structured log entry. Recoverable via `git restore`."""
    if not path.exists():
        return False
    stem = path.stem
    parent_name = path.parent.name
    today = date.today().isoformat()
    try:
        path.unlink()
    except OSError:
        return False

    log = WIKI / "log.md"
    if log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(
                f"\n## [{today}] reject | {stem}\n\n"
                f"- **User:** {user}\n"
                f"- **Page:** `wiki/{parent_name}/{stem}.md` (deleted)\n"
                f"- **Reason:** {reason if reason else '(not specified)'}\n"
                f"- **Recovery:** `git restore wiki/{parent_name}/{stem}.md` if needed.\n"
            )
    return True


def delete_search_file(path: Path, user: str, reason: str = "") -> bool:
    """Delete a raw/searches file. Logs the deletion."""
    if not path.exists():
        return False
    name = path.name
    today = date.today().isoformat()
    try:
        path.unlink()
    except OSError:
        return False

    log = WIKI / "log.md"
    if log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(
                f"\n## [{today}] delete-search | {name}\n\n"
                f"- **User:** {user}\n"
                f"- **File:** `raw/searches/{name}` (deleted)\n"
                f"- **Reason:** {reason if reason else '(not specified)'}\n"
                f"- **Recovery:** `git restore raw/searches/{name}` if needed.\n"
            )
    return True


def write_page_content(path: Path, content: str) -> bool:
    """Save edited content back to file."""
    try:
        path.write_text(content, encoding="utf-8")
        return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------


def _render_review_card(path: Path, user: str, kind: str, key_prefix: str = "") -> None:
    """Render one review item (stub or search) with view/edit/promote/reject actions.

    kind: "stub" or "search"
    key_prefix: caller-supplied namespace to disambiguate widget keys when the
        same path is rendered in multiple places (e.g. inline-in-turn and
        Review tab simultaneously). Default empty for the Review tab.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        st.error(f"Could not read {path}")
        return

    fm, body = parse_frontmatter(content)
    title = fm.get("title", path.stem).strip().strip('"').strip("'")
    rel_path = path.relative_to(ROOT)

    st.markdown(f"#### {title}")
    st.caption(
        f"`{rel_path}`  ·  modified {datetime.fromtimestamp(path.stat().st_mtime).strftime('%Y-%m-%d %H:%M')}"
    )

    base = f"{key_prefix}{kind}_{path.stem}"
    view_key = f"view_{base}"
    editbtn_key = f"editbtn_{base}"
    edit_open_key = f"edit_open_{base}"
    edit_key = f"edit_{base}"
    save_key = f"save_{base}"
    promote_key = f"promote_{base}"
    reject_key = f"reject_{base}"
    confirm_key = f"confirm_reject_{base}"
    reason_key = f"reason_{base}"
    yes_key = f"yes_{base}"
    no_key = f"no_{base}"

    if edit_open_key not in st.session_state:
        st.session_state[edit_open_key] = False

    cols = st.columns([1, 1, 1, 1])
    with cols[0]:
        view_open = st.checkbox("View", key=view_key)
    with cols[1]:
        if st.button("Edit", key=editbtn_key):
            st.session_state[edit_open_key] = not st.session_state[edit_open_key]
    with cols[2]:
        if kind == "stub":
            if st.button("Promote", key=promote_key, type="primary"):
                if promote_stub(path, user):
                    st.success(f"Promoted: `{rel_path}` (auto-generated flag removed)")
                    st.rerun()
                else:
                    st.error("Promote failed.")
        else:
            st.write("")  # placeholder to keep column layout
    with cols[3]:
        reject_label = "Reject" if kind == "stub" else "Delete"
        if st.button(reject_label, key=reject_key):
            st.session_state[confirm_key] = True

    # Reject/delete confirmation
    if st.session_state.get(confirm_key):
        with st.container(border=True):
            st.warning(
                f"Confirm {'rejection' if kind == 'stub' else 'deletion'} of `{rel_path}`. "
                "Recoverable via `git restore` since the file is tracked."
            )
            reason = st.text_input(
                "Reason (optional, written to log.md)",
                key=reason_key,
            )
            confirm_cols = st.columns(2)
            if confirm_cols[0].button("Yes, proceed", key=yes_key, type="primary"):
                ok = (
                    reject_stub(path, user, reason)
                    if kind == "stub"
                    else delete_search_file(path, user, reason)
                )
                if ok:
                    st.success(f"{'Rejected' if kind == 'stub' else 'Deleted'}: `{rel_path}`")
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
                else:
                    st.error("Operation failed.")
            if confirm_cols[1].button("Cancel", key=no_key):
                st.session_state.pop(confirm_key, None)
                st.rerun()

    # View
    if view_open:
        with st.expander("Rendered content", expanded=True):
            st.markdown(body if body else content)

    # Edit
    if st.session_state[edit_open_key]:
        edited = st.text_area(
            "Edit raw markdown:",
            value=content,
            height=400,
            key=edit_key,
        )
        save_cols = st.columns([1, 4])
        if save_cols[0].button("Save changes", key=save_key, type="primary"):
            if write_page_content(path, edited):
                st.success(f"Saved: `{rel_path}`")
                st.session_state[edit_open_key] = False
                st.rerun()
            else:
                st.error("Save failed.")


def render_case_capture(case: dict, user: str) -> None:
    """Render the case-capture form for one concept page with a Decision skeleton."""
    options = case.get("options") or []
    has_structured = bool(options)

    st.markdown(f"### {case['title']}")
    st.caption(
        f"Source: [[{case['stem']}]] · "
        f"{'structured options parsed' if has_structured else 'free-form (no parsed options)'}"
    )

    with st.expander("📖 Decision skeleton (from concept page)", expanded=not has_structured):
        st.markdown(case["skeleton"])

    already = case_already_captured(user, case["stem"])
    if already:
        st.info(
            f"You've already captured a decision for this case (see `wiki/avatar/{user}/decisions.md`). "
            "Submitting again will append a new entry — useful for revising your reasoning."
        )

    st.markdown("---")
    st.markdown("**Your decision:**")

    base_key = f"case_{case['stem']}"

    if has_structured:
        # Radio + freeform "other" option
        choice = st.radio(
            "Pick one:",
            [o["key"] for o in options],
            format_func=lambda k: f"**{k}.** {next(o['title'] for o in options if o['key'] == k)}",
            key=f"{base_key}_choice",
        )
        chosen_text = next(o["title"] for o in options if o["key"] == choice)
    else:
        choice = "free"
        chosen_text = st.text_input(
            "Your decision (free-form):",
            placeholder="e.g., 'Proceed with T-DXd; reassess at 3 months for ILD'",
            key=f"{base_key}_choice_text",
        )

    reasoning = st.text_area(
        "Reasoning (verbatim — captured to your avatar):",
        placeholder="e.g., 'I weight CNS activity strongly in HER2+ residual disease; the brain-met reduction in DESTINY-Breast05 changes my baseline.'",
        height=120,
        key=f"{base_key}_reasoning",
    )

    confidence = st.radio(
        "Confidence:",
        ["high", "moderate", "low"],
        index=1,
        horizontal=True,
        key=f"{base_key}_conf",
    )

    wiki_tension = st.text_input(
        "Wiki tension (optional — does your decision deviate from the wiki / guidelines? note here):",
        placeholder="e.g., 'Deviates from NCCN; falls in guideline-gap area'",
        key=f"{base_key}_tension",
    )

    if st.button("Capture decision to avatar", key=f"{base_key}_save", type="primary"):
        if not chosen_text:
            st.error("Pick or enter a decision before capturing.")
        elif not reasoning.strip():
            st.warning("Reasoning is empty. Capturing anyway — but the avatar is more useful with reasoning.")
            append_case_decision(
                user=user, case=case, decision_key=choice, decision_text=chosen_text,
                reasoning=reasoning, confidence=confidence, wiki_tension=wiki_tension,
            )
            st.success(f"Captured. See `wiki/avatar/{user}/decisions.md`.")
            st.rerun()
        else:
            append_case_decision(
                user=user, case=case, decision_key=choice, decision_text=chosen_text,
                reasoning=reasoning, confidence=confidence, wiki_tension=wiki_tension,
            )
            st.success(f"Captured. See `wiki/avatar/{user}/decisions.md`.")
            st.rerun()


def render_cases_tab(user: str) -> None:
    cases = find_decision_skeleton_pages()
    if not cases:
        st.info(
            "No concept pages with a `## Decision skeleton` section found. "
            "Add a Decision skeleton to any `wiki/concepts/*.md` page (with `**Option 1 — ...**` "
            "structured headers) and it'll appear here as a captureable case."
        )
        return

    captured_stems = {c["stem"] for c in cases if case_already_captured(user, c["stem"])}
    available = [c for c in cases if c["stem"] not in captured_stems]
    captured = [c for c in cases if c["stem"] in captured_stems]

    st.caption(
        f"**{len(available)}** captureable cases · **{len(captured)}** already captured for `{user}`"
    )

    if available:
        st.markdown("### Available cases")
        for case in available:
            with st.container(border=True):
                render_case_capture(case, user)
    else:
        st.info("All available cases captured for this user. 🎉")

    if captured:
        st.markdown("---")
        st.markdown("### Already captured (revisit / revise)")
        st.caption("Capturing again appends a new entry to `decisions.md` — useful when your reasoning evolves.")
        for case in captured:
            with st.expander(f"✓ {case['title']}", expanded=False):
                render_case_capture(case, user)


def render_review_tab(user: str) -> None:
    stubs = list_auto_generated_pages()
    searches = list_recent_searches()

    st.markdown(
        f"**{len(stubs)}** auto-generated stub(s) awaiting review · "
        f"**{len(searches)}** search file(s) in `raw/searches/`"
    )

    sub = st.tabs([f"🌱 Stubs ({len(stubs)})", f"💾 Searches ({len(searches)})"])

    with sub[0]:
        if not stubs:
            st.info(
                "No auto-generated stubs in the wiki. "
                "When the UI grounded fallback fires with auto-ingest enabled, novel "
                "entity stubs land here for review before promotion."
            )
        else:
            st.caption("Recent first. Promote when verified; reject to delete (recoverable via git).")
            for p in stubs:
                with st.container(border=True):
                    _render_review_card(p, user, kind="stub")

    with sub[1]:
        if not searches:
            st.info(
                "No saved searches yet. Files are written to `raw/searches/` whenever the "
                "wiki is insufficient for a query."
            )
        else:
            st.caption("Recent first. Delete to remove the raw artifact (recoverable via git).")
            for p in searches:
                with st.container(border=True):
                    _render_review_card(p, user, kind="search")


def render_turn(turn: Turn, user: str) -> None:
    with st.chat_message("user"):
        st.write(turn.question)

    with st.chat_message("assistant"):
        badge = {
            "wiki": "🟢 Wiki only",
            "mixed": "🟡 Wiki + internet",
            "internet": "🌐 Internet only",
        }[turn.origin]
        st.caption(
            f"{badge} · {len(turn.sources)} pages consulted · "
            f"{turn.gemini_calls} Gemini calls · {turn.tokens.total:,} tokens"
        )

        st.markdown(turn.answer)

        if turn.sources:
            with st.expander(f"📄 Pages consulted ({len(turn.sources)})"):
                for s in turn.sources:
                    st.markdown(f"- `wiki/.../{s}.md`")

        if turn.saved_search_path:
            with st.expander("💾 Grounded search saved"):
                st.code(turn.saved_search_path, language="text")
                st.caption(
                    "Saved with the same format as agent-driven search.py — frontmatter, "
                    "resolved URLs, token tracking, _token_log.jsonl entry."
                )

        if turn.stubs_created:
            with st.expander(
                f"🌱 Auto-ingested ({len(turn.stubs_created)} stub pages) — review inline", expanded=False
            ):
                st.caption(
                    "Each stub is marked `auto_generated: true`. Use Promote to mark verified, "
                    "Reject to delete (recoverable via git)."
                )
                for p_str in turn.stubs_created:
                    p = Path(p_str)
                    if p.exists():
                        with st.container(border=True):
                            _render_review_card(
                                p, user, kind="stub", key_prefix=f"turn{turn.idx}_"
                            )
                    else:
                        st.markdown(f"- `{p}` — *(no longer present; reviewed elsewhere)*")

        if turn.mc and not turn.mc.captured:
            with st.expander("🧭 Preference probe — help build your avatar", expanded=True):
                st.markdown(f"**{turn.mc.question}**")
                if turn.mc.rationale:
                    st.caption(f"*Why this question:* {turn.mc.rationale}")
                option_keys = [o["key"] for o in turn.mc.options]
                option_lookup = {o["key"]: o["text"] for o in turn.mc.options}
                choice = st.radio(
                    "Pick one:",
                    option_keys,
                    format_func=lambda k: f"**{k}.** {option_lookup[k]}",
                    key=f"radio_{turn.idx}",
                )
                reasoning = st.text_input(
                    "Reasoning (optional)",
                    placeholder="e.g., 'I weight toxicity avoidance over marginal OS gain'",
                    key=f"reason_{turn.idx}",
                )
                if st.button("Save preference to avatar", key=f"save_{turn.idx}", type="primary"):
                    append_preference_capture(
                        user=user,
                        mc=turn.mc,
                        choice_key=choice,
                        reasoning=reasoning,
                        source_question=turn.question,
                    )
                    turn.mc.captured = True
                    # Re-write session to persist the captured flag
                    _rewrite_session(user)
                    st.success(f"Saved to wiki/avatar/{user}/decisions.md")
                    st.rerun()
        elif turn.mc and turn.mc.captured:
            st.success("✓ Preference captured to avatar")


def _rewrite_session(user: str) -> None:
    """Rewrite today's session JSONL from current st.session_state.history.

    Used after MC capture to persist the captured=True flag.
    """
    f = session_file_for(user)
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("w", encoding="utf-8") as h:
        for turn in st.session_state.history:
            h.write(json.dumps(_turn_to_dict(turn)) + "\n")


def main() -> None:
    st.set_page_config(page_title="Wiki LM", layout="wide", page_icon="📚")

    # Sidebar — user identity, controls, stats
    with st.sidebar:
        st.title("📚 Wiki LM")
        st.caption(
            f"Local KB + avatar capture\n\n"
            f"- Pro (synth + MC): `{MODEL_PRO}`\n"
            f"- Flash (route + extract): `{MODEL_FLASH}`"
        )

        user = st.text_input(
            "Active user",
            value=st.session_state.get("user", DEFAULT_USER),
            help="Per SCHEMA.md user identity convention",
        )

        # Persist user across reruns
        if "user" not in st.session_state or st.session_state.user != user:
            st.session_state.user = user
            # Re-load history for this user
            st.session_state.history = load_today_session(user)
            st.session_state.session_tokens = sum(
                t.tokens.total for t in st.session_state.history
            )

        st.divider()
        auto_ingest = st.toggle(
            "Auto-ingest grounded searches",
            value=True,
            help=(
                "When the wiki is insufficient, save the grounded search to "
                "raw/searches/ AND extract novel entities as auto-generated "
                "stub pages in wiki/entities|concepts/. Stubs are marked "
                "`auto_generated: true` and need agent review."
            ),
        )

        st.divider()
        st.subheader("Wiki state")
        n_pages = len(_list_wiki_pages())
        st.metric("Shared knowledge pages", n_pages)

        avatar_dir = WIKI / "avatar" / user
        if avatar_dir.exists():
            for label, fname in [
                ("Avatar decisions", "decisions.md"),
                ("Avatar questions", "questions.md"),
            ]:
                p = avatar_dir / fname
                count = p.read_text(encoding="utf-8").count("###") if p.exists() else 0
                st.metric(f"{label} ({user})", count)

        st.divider()
        st.subheader("Session")
        if "history" not in st.session_state:
            st.session_state.history = load_today_session(user)
        if "session_tokens" not in st.session_state:
            st.session_state.session_tokens = sum(
                t.tokens.total for t in st.session_state.history
            )
        st.metric("Queries this session", len(st.session_state.history))
        st.metric("Tokens this session", f"{st.session_state.session_tokens:,}")
        st.caption(
            f"Persisted to `{session_file_for(user).relative_to(ROOT)}`"
            if SESSIONS_DIR.exists() or st.session_state.history
            else "Session writes to raw/sessions/ on first query"
        )

        if st.button("Clear in-memory chat (keeps session file)"):
            st.session_state.history = []
            st.session_state.session_tokens = 0
            st.rerun()

    # Main pane — tabs: Chat | Cases | Review
    n_stubs = len(list_auto_generated_pages())
    n_searches = len(list_recent_searches())
    case_pages = find_decision_skeleton_pages()
    n_cases_avail = sum(1 for c in case_pages if not case_already_captured(user, c["stem"]))

    chat_tab, cases_tab, review_tab = st.tabs([
        "💬 Chat",
        f"📚 Cases ({n_cases_avail} available)",
        f"📋 Review ({n_stubs} stubs · {n_searches} searches)",
    ])

    with cases_tab:
        st.subheader("Captureable cases")
        st.caption(
            "Concept pages with a `## Decision skeleton` section become captureable cases. "
            "Pick one, walk through the option set, capture your decision + reasoning + "
            "confidence — same rich format as agent-mediated capture."
        )
        render_cases_tab(user)

    with review_tab:
        st.subheader("Review queue")
        st.caption(
            "Auto-generated stubs awaiting promotion + saved grounded searches. "
            "Actions log to `wiki/log.md`; deletions are recoverable via `git restore`."
        )
        render_review_tab(user)

    with chat_tab:
        st.subheader("Ask the wiki")
        st.caption(
            "Wiki-first retrieval — internet fallback only when needed. "
            "Equipoise becomes a multiple-choice probe to grow your avatar. "
            "Grounded searches save to `raw/searches/` and (with auto-ingest) "
            "create stub pages."
        )

        # Render history (existing turns visible immediately)
        for turn in st.session_state.history:
            render_turn(turn, user)

        # Phase 2: deferred ingest, runs AFTER all existing turns have rendered.
        # The user has already seen the answer above; this block does B + C with
        # a status spinner, then reruns to update the just-rendered turn's badges.
        pending = st.session_state.get("pending_ingest")
        if pending:
            turn_idx = pending["turn_idx"]
            if turn_idx < len(st.session_state.history):
                turn = st.session_state.history[turn_idx]
                with st.status(
                    "Saving grounded search + auto-ingesting novel entities…", expanded=False
                ) as status:
                    try:
                        run_query_phase2(
                            turn=turn,
                            grounded_resp=pending["grounded_resp"],
                            question=pending["question"],
                            user=pending["user"],
                            auto_ingest_enabled=pending["auto_ingest"],
                        )
                        # Audit log entries with complete saved-path + stubs fields
                        append_question_log(turn, user)
                        # Rewrite session JSONL with the now-updated turn
                        _rewrite_session(user)
                        status.update(
                            label=(
                                f"✓ Ingest complete · "
                                f"{'saved + ' if turn.saved_search_path else ''}"
                                f"{len(turn.stubs_created)} stub(s) created"
                            ),
                            state="complete",
                            expanded=False,
                        )
                    except Exception as exc:
                        status.update(
                            label=f"⚠️ Ingest failed: {type(exc).__name__}: {exc}",
                            state="error",
                        )
                        try:
                            append_question_log(turn, user)
                        except Exception:
                            pass
                st.session_state.session_tokens += turn.tokens.total - pending["initial_tokens"]
            st.session_state.pop("pending_ingest", None)
            st.rerun()

    # Phase 1: handle new input — synchronous, must complete before answer renders
    # (chat_input docks at page bottom regardless of code location)
    question = st.chat_input(
        "Ask a question (e.g., 'How would you weight T-DXd over T-DM1 in residual disease?')"
    )
    if question:
        with st.spinner("Routing through the wiki…"):
            try:
                turn, grounded_resp = run_query_phase1(question, user)
            except Exception as e:
                st.error(f"Query failed: {type(e).__name__}: {e}")
                st.stop()

        # Persist partial turn to session JSONL (A) — phase 2 will rewrite if needed
        try:
            append_turn_to_session(turn, user)
        except Exception as e:
            st.warning(f"Session persistence failed: {e}")

        st.session_state.history.append(turn)
        st.session_state.session_tokens += turn.tokens.total

        if grounded_resp is not None:
            # Defer phase 2 — answer renders this rerun, ingest runs the next rerun
            st.session_state.pending_ingest = {
                "turn_idx": turn.idx,
                "grounded_resp": grounded_resp,
                "question": question,
                "user": user,
                "auto_ingest": auto_ingest,
                "initial_tokens": turn.tokens.total,
            }
        else:
            # Wiki-only — log immediately; no phase 2 needed
            try:
                append_question_log(turn, user)
            except Exception as e:
                st.warning(f"Audit log failed: {e}")

        st.rerun()


if __name__ == "__main__":
    main()
