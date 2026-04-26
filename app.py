"""
Wiki LM — Streamlit MVP.

Five capabilities (per the build spec):
  1. Ask questions of the wiki
  2. If the wiki is insufficient, fall back to internet (Gemini grounded search)
  3. Interactions are written back as audit + the user's avatar
  4. Agent generates multiple-choice questions to elicit user preferences
  5. Preferences captured to wiki/avatar/{user}/

Run:
    streamlit run app.py

Requires:
    GOOGLE_API_KEY in .env
    Wiki populated under wiki/ per SCHEMA.md
"""

from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROOT = Path(__file__).parent
WIKI = ROOT / "wiki"
RAW = ROOT / "raw"
MODEL = "gemini-2.5-flash"
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
    options: list[dict]  # [{"key": "A", "text": "..."}, ...]
    rationale: str
    captured: bool = False


@dataclass
class Turn:
    idx: int
    question: str
    answer: str
    sources: list[str] = field(default_factory=list)  # wiki page filenames consulted
    origin: str = "wiki"  # "wiki" | "internet" | "mixed"
    gemini_calls: int = 0
    tokens: TokenUsage = field(default_factory=TokenUsage)
    mc: MCQuestion | None = None


# ---------------------------------------------------------------------------
# Token helpers
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
    """Pull the first JSON object/array from a model response. Returns None on failure."""
    # Try array first
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    # Try object
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            pass
    return None


# ---------------------------------------------------------------------------
# Wiki retrieval
# ---------------------------------------------------------------------------


def _read_index() -> str:
    return (WIKI / "index.md").read_text(encoding="utf-8")


def _list_wiki_pages() -> list[Path]:
    """All .md pages under wiki/ excluding hidden directories and avatar (per-user)."""
    pages: list[Path] = []
    for p in WIKI.rglob("*.md"):
        if any(part.startswith(".") for part in p.parts):
            continue
        if "avatar" in p.parts:
            continue  # avatar pages are per-user, not part of shared knowledge
        pages.append(p)
    return pages


def _load_pages(filenames: list[str]) -> dict[str, str]:
    """Resolve filenames (without extension) to wiki paths and load content."""
    contents: dict[str, str] = {}
    for f in filenames:
        # Try every plausible location; first match wins
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
    """Use Gemini to pick relevant page filenames from the wiki index."""
    index = _read_index()
    prompt = f"""You are a wiki retrieval router. Given the user's question and the wiki index below, list the page filenames (without paths or .md extension) most relevant to answering the question.

Return STRICTLY a JSON array of strings — page filenames only. Maximum 8. If no pages are relevant, return [].

QUESTION:
{query}

WIKI INDEX:
{index}
"""
    resp = _client.models.generate_content(model=MODEL, contents=prompt)
    parsed = _extract_json(resp.text or "")
    pages = parsed if isinstance(parsed, list) else []
    # Filter to filenames that actually exist
    valid: list[str] = []
    for p in pages:
        if not isinstance(p, str):
            continue
        if list(WIKI.rglob(f"{p}.md")):
            valid.append(p)
    return valid, _tokens(resp)


# ---------------------------------------------------------------------------
# Synthesis
# ---------------------------------------------------------------------------


_WIKI_ONLY_INSTRUCTIONS = """You are a clinical knowledge assistant answering strictly from the provided wiki pages. Do not use external knowledge.

If the wiki does NOT contain enough information to answer the question well, respond with EXACTLY this token on its own line at the start: INSUFFICIENT_WIKI_DATA

After the verdict, you may write a brief explanation of what is missing.

If the wiki IS sufficient:
  - Give a clear, structured answer
  - Use [[wiki-page-name]] inline citations for every factual claim
  - Cite only pages that actually appear in the input below — do NOT invent page names
  - End with a short "Sources" line listing the pages cited
"""


def synthesize_wiki_answer(query: str, page_contents: dict[str, str]) -> tuple[str, bool, TokenUsage]:
    """Try to answer from wiki only. Returns (answer, sufficient, tokens)."""
    if not page_contents:
        return "INSUFFICIENT_WIKI_DATA\nNo relevant wiki pages were found for this question.", False, TokenUsage()

    pages_text = "\n\n---\n\n".join(
        f"## wiki/{name}\n\n{content}" for name, content in page_contents.items()
    )
    prompt = f"""{_WIKI_ONLY_INSTRUCTIONS}

QUESTION:
{query}

WIKI PAGES:
{pages_text}
"""
    resp = _client.models.generate_content(model=MODEL, contents=prompt)
    answer = (resp.text or "").strip()
    sufficient = not answer.upper().startswith("INSUFFICIENT_WIKI_DATA")
    return answer, sufficient, _tokens(resp)


def synthesize_internet_answer(query: str, page_contents: dict[str, str]) -> tuple[str, TokenUsage]:
    """Wiki was insufficient — augment with grounded Google search."""
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

End with a short "Sources" line listing the wiki pages cited (if any) and noting that web search was used.

QUESTION:
{query}

WIKI CONTEXT:
{pages_text}
"""
    resp = _client.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    return (resp.text or "").strip(), _tokens(resp)


# ---------------------------------------------------------------------------
# Preference elicitation
# ---------------------------------------------------------------------------


_MC_PROMPT = """You design preference probes to elicit a clinician's avatar.

Given the user's question and the answer just provided, identify the principal CLINICAL JUDGMENT the user would face if they applied this information to a real patient. Generate ONE multiple-choice question with 2–4 distinct, defensible options.

Rules:
  - Only generate an MC if there is genuine equipoise — i.e., reasonable clinicians could disagree
  - Do NOT generate an MC for purely factual questions or settled standards of care
  - Each option must be defensible on the available evidence
  - Each option should reflect a different weighting of trade-offs (toxicity vs. efficacy, off-label comfort, guideline conformity, etc.)

Return STRICTLY a single JSON object:
{{
  "label": "<short kebab-case label, e.g. 'tnbc-pcr-irae-rechallenge'>",
  "question": "<the MC question>",
  "options": [
    {{"key": "A", "text": "<option A>"}},
    {{"key": "B", "text": "<option B>"}}
  ],
  "rationale": "<one sentence on what this MC reveals about the user's preferences>"
}}

If no genuine equipoise exists, return EXACTLY:
{{"label": null}}

QUESTION:
{question}

ANSWER:
{answer}
"""


def generate_preference_mc(query: str, answer: str) -> tuple[MCQuestion | None, TokenUsage]:
    resp = _client.models.generate_content(
        model=MODEL, contents=_MC_PROMPT.format(question=query, answer=answer)
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
    """Write to wiki/log.md AND wiki/avatar/{user}/questions.md."""
    today = date.today().isoformat()
    sources_str = (
        ", ".join(f"[[{s}]]" for s in turn.sources) if turn.sources else "none"
    )
    safe_label = re.sub(r"[^a-z0-9]+", "-", turn.question.lower()).strip("-")[:60]

    log_entry = f"""
## [{today}] query | {turn.question[:70]}{'...' if len(turn.question) > 70 else ''}

- **User:** {user}
- **Question:** "{turn.question}"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** {sources_str}
- **Gemini calls:** {turn.gemini_calls}
- **Answer origin:** {turn.origin}
- **Tokens (Gemini):** {turn.tokens.total}
"""

    questions_entry = f"""
### [{today}] {safe_label}

- **Question:** "{turn.question}"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** {sources_str}
- **Gemini calls:** {turn.gemini_calls}
- **Answer origin:** {turn.origin}
- **Tokens (Gemini):** {turn.tokens.total}
- **MC probe generated:** {"yes — " + turn.mc.label if turn.mc else "no"}
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
    """Write the user's MC answer to avatar/decisions.md."""
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
# UI
# ---------------------------------------------------------------------------


def run_query(question: str, user: str) -> Turn:
    total_tokens = TokenUsage()
    gemini_calls = 0

    # Step 1: pick relevant pages
    pages, t1 = select_relevant_pages(question)
    total_tokens = total_tokens + t1
    gemini_calls += 1

    # Step 2: load content + try wiki-only synthesis
    page_contents = _load_pages(pages)
    answer, sufficient, t2 = synthesize_wiki_answer(question, page_contents)
    total_tokens = total_tokens + t2
    gemini_calls += 1

    origin = "wiki"
    if not sufficient:
        # Step 3: internet fallback
        answer, t3 = synthesize_internet_answer(question, page_contents)
        total_tokens = total_tokens + t3
        gemini_calls += 1
        origin = "internet" if not page_contents else "mixed"

    # Step 4: generate preference MC
    mc, t4 = generate_preference_mc(question, answer)
    total_tokens = total_tokens + t4
    gemini_calls += 1

    return Turn(
        idx=len(st.session_state.history),
        question=question,
        answer=answer,
        sources=pages,
        origin=origin,
        gemini_calls=gemini_calls,
        tokens=total_tokens,
        mc=mc,
    )


def render_turn(turn: Turn, user: str) -> None:
    with st.chat_message("user"):
        st.write(turn.question)

    with st.chat_message("assistant"):
        # Origin badge
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

        # MC preference probe
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
                    st.success(f"Saved to wiki/avatar/{user}/decisions.md")
                    st.rerun()
        elif turn.mc and turn.mc.captured:
            st.success("✓ Preference captured to avatar")


def main() -> None:
    st.set_page_config(page_title="Wiki LM", layout="wide", page_icon="📚")

    # Sidebar — user identity + stats
    with st.sidebar:
        st.title("📚 Wiki LM")
        st.caption("Local knowledge base + avatar capture")

        user = st.text_input("Active user", value=DEFAULT_USER, help="Per SCHEMA.md user identity convention")

        st.divider()
        st.subheader("Wiki state")
        n_pages = len(_list_wiki_pages())
        st.metric("Shared knowledge pages", n_pages)

        avatar_dir = WIKI / "avatar" / user
        if avatar_dir.exists():
            n_decisions_file = avatar_dir / "decisions.md"
            n_decisions = (
                n_decisions_file.read_text(encoding="utf-8").count("###")
                if n_decisions_file.exists()
                else 0
            )
            n_questions_file = avatar_dir / "questions.md"
            n_questions = (
                n_questions_file.read_text(encoding="utf-8").count("###")
                if n_questions_file.exists()
                else 0
            )
            st.metric(f"Avatar decisions ({user})", n_decisions)
            st.metric(f"Avatar questions ({user})", n_questions)

        st.divider()
        st.subheader("Session")
        if "history" not in st.session_state:
            st.session_state.history = []
        if "session_tokens" not in st.session_state:
            st.session_state.session_tokens = 0
        st.metric("Queries this session", len(st.session_state.history))
        st.metric("Tokens this session", f"{st.session_state.session_tokens:,}")

        if st.button("Clear chat history"):
            st.session_state.history = []
            st.session_state.session_tokens = 0
            st.rerun()

    # Main pane
    st.title("Ask the wiki")
    st.caption(
        "Wiki-first retrieval — internet fallback only when needed. "
        "Equipoise becomes a multiple-choice probe to grow your avatar."
    )

    # History
    for turn in st.session_state.history:
        render_turn(turn, user)

    # Input
    question = st.chat_input("Ask a question (e.g., 'How would you weight T-DXd over T-DM1 in residual disease?')")
    if question:
        with st.spinner("Routing through the wiki…"):
            try:
                turn = run_query(question, user)
            except Exception as e:
                st.error(f"Query failed: {type(e).__name__}: {e}")
                st.stop()

        # Audit the query
        try:
            append_question_log(turn, user)
        except Exception as e:
            st.warning(f"Query succeeded but audit log failed: {e}")

        st.session_state.history.append(turn)
        st.session_state.session_tokens += turn.tokens.total
        st.rerun()


if __name__ == "__main__":
    main()
