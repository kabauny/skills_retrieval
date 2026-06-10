"""
Wiki LM — core logic (UI-agnostic).

All retrieval, synthesis, grounded-save, auto-ingest, preference-probe, audit,
capture, session-persistence, cases, and review logic lives here as pure
functions / dataclasses with NO web-framework or UI dependency. Both the
FastAPI server (`api.py`) and any other front end build on top of this module.

Extracted from the original Streamlit `app.py`; behavior is preserved.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

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
# Auto-generated stubs are quarantined here, NOT mixed into the curated
# entities/concepts namespace. They are excluded from query synthesis until an
# agent promotes them (promotion moves the file into entities/ or concepts/).
STUBS_DIR = WIKI / "stubs"
# Auto-ingested internet answers land here as SEARCHABLE, editable pages
# (not quarantined). They carry `auto_generated: true` as a badge — not an
# exclusion signal — plus an ingest timestamp and a verified-by field.
NOTES_DIR = WIKI / "notes"
# Principle nodes — reasoning lenses & disease frameworks ("how to think about
# X"). They are synthesis-eligible and are PINNED into context when a retrieved
# entity links to them (see _pin_linked_principles), rather than scored by the
# graph — anti-hub weighting would otherwise suppress the most-linked lenses.
PRINCIPLES_DIR = WIKI / "principles"
# Institutional policy overlay — formulary status + preferred pathways ("what we
# give here"). Separate from universal evidence; injected to PREFERENCE-WEIGHT
# the recommendation at synthesis, not routed to as content.
INSTITUTION_DIR = WIKI / "institution"
_INSTITUTION_FILE = INSTITUTION_DIR / "preferences.json"
FORMULARY_STATUSES = ["preferred", "on-formulary", "restricted", "non-formulary", "biosimilar"]

# Directories under wiki/ that must never feed end-user query synthesis.
# Note: wiki/notes/ is deliberately NOT here — auto-ingested notes are
# searchable so a repeat question is answered locally instead of re-searching.
_SYNTHESIS_EXCLUDED_DIRS = {"avatar", "stubs", "institution"}

# Link contract (the ontology): required edges per entity_type. Principle links
# guarantee the reasoning lenses are reachable from real entities; entity links
# keep drugs/trials anchored to a disease. The Grow "contract gaps" strategy
# surfaces violations for propose-and-approve — nothing here auto-writes links.
LINK_CONTRACT: dict[str, dict] = {
    "drug":  {"principles": ["efficacy", "adverse-events"], "entity_types": ["cancer"]},
    "trial": {"principles": ["efficacy"], "entity_types": ["drug", "cancer"]},
    "cancer": {"principles": ["staging-and-resectability", "biomarker-testing"], "entity_types": []},
}

# Two-model split: Pro for heavy reasoning, Flash for light structured tasks.
MODEL_PRO = "gemini-3.1-pro-preview"
MODEL_FLASH = "gemini-2.5-flash"
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768
EMBED_CACHE = ROOT / ".embeddings_cache.json"
DEFAULT_USER = "jim.chen"

# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

load_dotenv()


class MissingAPIKey(RuntimeError):
    """Raised when GOOGLE_API_KEY is not configured."""


_client: genai.Client | None = None


def get_client() -> genai.Client:
    """Lazily construct the Gemini client. Raises MissingAPIKey if unconfigured."""
    global _client
    if _client is None:
        key = os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise MissingAPIKey("GOOGLE_API_KEY not set. Add it to .env and restart.")
        _client = genai.Client(api_key=key)
    return _client


def api_key_present() -> bool:
    return bool(os.environ.get("GOOGLE_API_KEY"))


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
    stubs_created: list[str] = field(default_factory=list)  # legacy: entity stub paths
    note_created: str | None = None  # wiki/notes/{slug}.md if auto-ingested
    ts: str = ""  # stable creation timestamp; unique per turn (UI key + identity)


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


def _extract_json_object(text: str):
    """Pull a JSON OBJECT specifically. Needed when the object itself contains
    an array (e.g. the MC probe's "options") — _extract_json would match the
    inner array first and return a list instead of the object."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group())
        except json.JSONDecodeError:
            return None
    return None


# ---------------------------------------------------------------------------
# Wiki retrieval
# ---------------------------------------------------------------------------


def _read_index() -> str:
    return (WIKI / "index.md").read_text(encoding="utf-8")


def list_wiki_pages() -> list[Path]:
    """Curated, synthesis-eligible pages (excludes avatar and quarantined stubs)."""
    pages: list[Path] = []
    for p in WIKI.rglob("*.md"):
        if any(part.startswith(".") for part in p.parts):
            continue
        if any(d in p.parts for d in _SYNTHESIS_EXCLUDED_DIRS):
            continue
        pages.append(p)
    return pages


def notes_curation() -> dict[str, dict]:
    """Per-note triage signals for the Review tab (no LLM — reuses the embedding
    index + link graph): graph link_count, the most-similar OTHER note (duplicate
    candidate), and the most-similar ENTITY (a note that shadows curated content).
    Returns a dict keyed by note stem."""
    build_page_embeddings()
    cache = _embed_cache_load()
    adj = build_link_graph()
    notes = list(NOTES_DIR.glob("*.md"))
    note_stems = {p.stem for p in notes}
    entity_stems = {p.stem for p in (WIKI / "entities").glob("*.md")}
    out: dict[str, dict] = {}
    for p in notes:
        stem = p.stem
        v = cache.get(stem, {}).get("vec")
        dup_note = shadow_entity = None
        dup_score = shadow_score = 0.0
        if v:
            for other, d in cache.items():
                if other == stem:
                    continue
                dv = d.get("vec")
                if not dv:
                    continue
                s = _cosine(v, dv)
                if other in note_stems and s > dup_score:
                    dup_score, dup_note = s, other
                elif other in entity_stems and s > shadow_score:
                    shadow_score, shadow_entity = s, other
        out[stem] = {
            "link_count": len(adj.get(stem, ())),
            "dup_note": dup_note,
            "dup_score": round(dup_score, 3),
            "shadow_entity": shadow_entity,
            "shadow_score": round(shadow_score, 3),
        }
    return out


# ---------------------------------------------------------------------------
# Institutional policy overlay (formulary + preferred pathways)
# ---------------------------------------------------------------------------


def load_institution() -> dict:
    """Institutional preferences: {formulary: {drug: {status, note}}, pathways:
    {disease: text}}. One shared institution (no multi-tenant scope yet)."""
    if _INSTITUTION_FILE.exists():
        try:
            d = json.loads(_INSTITUTION_FILE.read_text(encoding="utf-8"))
            d.setdefault("formulary", {})
            d.setdefault("pathways", {})
            return d
        except (json.JSONDecodeError, OSError):
            pass
    return {"formulary": {}, "pathways": {}}


def _save_institution(data: dict) -> None:
    INSTITUTION_DIR.mkdir(parents=True, exist_ok=True)
    _INSTITUTION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def set_formulary(drug: str, status: str, note: str = "") -> None:
    data = load_institution()
    if status and status in FORMULARY_STATUSES:
        data["formulary"][drug] = {"status": status, "note": note.strip()}
    else:  # empty/invalid status clears the entry
        data["formulary"].pop(drug, None)
    _save_institution(data)


def set_pathway(disease: str, text: str) -> None:
    data = load_institution()
    if text.strip():
        data["pathways"][disease] = text.strip()
    else:
        data["pathways"].pop(disease, None)
    _save_institution(data)


def institution_editor_data() -> dict:
    """Everything the Institution editor needs: current preferences + the drug
    and cancer entity lists to set statuses/pathways against."""
    data = load_institution()
    drugs, diseases = [], []
    for p in sorted((WIKI / "entities").glob("*.md")):
        try:
            fm, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
        except OSError:
            continue
        et = (fm.get("entity_type", "") or "").strip().strip('"').strip("'").lower()
        title = (fm.get("title", p.stem) or p.stem).strip().strip('"')
        if et == "drug":
            drugs.append({"stem": p.stem, "title": title})
        elif et == "cancer":
            diseases.append({"stem": p.stem, "title": title})
    return {
        "formulary": data["formulary"],
        "pathways": data["pathways"],
        "statuses": FORMULARY_STATUSES,
        "drugs": drugs,
        "diseases": diseases,
    }


def institutional_context(picked: list[str]) -> str:
    """A preference-weighting block for synthesis, built from the institutional
    overlay and scoped to the picked pages' disease(s). Includes the relevant
    preferred pathway(s) plus the full (compact) formulary so the synthesizer can
    lead with preferred options and caveat off-formulary ones. '' if none set."""
    data = load_institution()
    formulary, pathways = data.get("formulary", {}), data.get("pathways", {})
    if not formulary and not pathways:
        return ""
    diseases = set()
    for s in picked:
        d = s[: -len("-approach")] if s.endswith("-approach") else s
        if d in pathways:
            diseases.add(d)
    path_lines = [f"- {d}: {pathways[d]}" for d in sorted(diseases)]
    form_lines = [
        f"- {drug}: {v['status']}" + (f" — {v['note']}" if v.get("note") else "")
        for drug, v in sorted(formulary.items())
    ]
    blocks = []
    if path_lines:
        blocks.append("Institution preferred pathways (for the disease(s) in this question):\n"
                      + "\n".join(path_lines))
    if form_lines:
        blocks.append("Institution drug formulary status:\n" + "\n".join(form_lines))
    if not blocks:
        return ""
    return (
        "\n\nINSTITUTIONAL PREFERENCES — preference-weight the recommendation: LEAD with the "
        "institution's preferred option(s) and state formulary status inline; still present "
        "evidence-based alternatives, but caveat any that are restricted (prior-auth) or "
        "non-formulary here. Do not invent statuses beyond those listed.\n\n"
        + "\n\n".join(blocks)
    )


_SEARCH_SKIP_STEMS = {"index", "log", "overview"}


def _search_snippet(body: str, terms: list[str], width: int = 180) -> str:
    """A one-line context window around the first matched term."""
    low = body.lower()
    pos = min((i for i in (low.find(t) for t in terms) if i != -1), default=-1)
    if pos == -1:
        chunk = body.strip()[:width]
    else:
        start = max(0, pos - width // 3)
        chunk = body[start:start + width]
    return re.sub(r"\s+", " ", chunk).strip()


def search_pages(query: str, limit: int = 30) -> list[dict]:
    """Lexical known-item search over the knowledge pages. AND-matches all terms
    across stem/title/aliases/body; ranks name hits above body-frequency. No LLM,
    no embeddings — instant. Returns {id, stem, title, kind, snippet, score}."""
    terms = [t for t in re.split(r"\s+", query.strip().lower()) if t]
    if not terms:
        return []
    out: list[dict] = []
    for p in list_wiki_pages():
        if p.stem in _SEARCH_SKIP_STEMS:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        fm, body = parse_frontmatter(text)
        title = (fm.get("title", "") or p.stem).strip().strip('"').strip("'")
        aliases = " ".join(re.findall(r'"([^"]+)"', fm.get("aliases", "") or ""))
        name_hay = f"{p.stem.replace('-', ' ')} {title} {aliases}".lower()
        body_low = body.lower()
        hay = name_hay + " " + body_low
        if not all(t in hay for t in terms):
            continue
        score = 0
        for t in terms:
            if t in name_hay:
                score += 25
            score += body_low.count(t)
        out.append({
            "id": str(p.relative_to(ROOT)),
            "stem": p.stem,
            "title": title,
            "kind": p.parent.name,
            "snippet": _search_snippet(body, terms),
            "score": score,
        })
    out.sort(key=lambda r: -r["score"])
    return out[:limit]


def _synthesis_page_path(stem: str) -> Path | None:
    """Resolve a stem to a synthesis-eligible page path, or None."""
    for path in WIKI.rglob(f"{stem}.md"):
        if any(part.startswith(".") for part in path.parts):
            continue
        if any(d in path.parts for d in _SYNTHESIS_EXCLUDED_DIRS):
            continue
        return path
    return None


def _all_known_stems() -> list[str]:
    """Every stem the auto-extractor should treat as already existing — curated
    pages plus quarantined stubs (but not avatar) — so it does not re-stub."""
    stems: set[str] = set()
    for p in WIKI.rglob("*.md"):
        if any(part.startswith(".") for part in p.parts):
            continue
        if "avatar" in p.parts:
            continue
        stems.add(p.stem)
    return sorted(stems)


def _load_pages(filenames: list[str], user: str = DEFAULT_USER) -> dict[str, str]:
    contents: dict[str, str] = {}
    princ = _principle_stems()
    for f in filenames:
        # Principle stems resolve per-provider (their fork wins over the shared
        # skeleton); everything else resolves to the one shared page.
        path = resolve_principle_path(f, user) if f in princ else _synthesis_page_path(f)
        if path is None:
            continue
        try:
            contents[f] = path.read_text(encoding="utf-8")
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
    resp = get_client().models.generate_content(model=MODEL_FLASH, contents=prompt)
    parsed = _extract_json(resp.text or "")
    pages = parsed if isinstance(parsed, list) else []
    valid: list[str] = []
    for p in pages:
        if isinstance(p, str) and _synthesis_page_path(p) is not None:
            valid.append(p)
    return valid, _tokens(resp)


# ---------------------------------------------------------------------------
# Embedding-based routing (cheap, scales — no LLM call, no whole-index prompt)
# ---------------------------------------------------------------------------
#
# Replaces "send all of index.md to an LLM and ask it to pick pages" with
# "embed the question, cosine-match against per-page embeddings, take the top
# few." Routing cost drops from ~5k LLM tokens to one tiny embedding call, and
# it stops growing with corpus size. Provenance is unaffected: this only selects
# which WHOLE pages to load — synthesis still reads full pages and cites them.

# Hybrid routing: embeddings shortlist a handful of candidates cheaply, then a
# small Flash call picks among THEM (over one-line summaries, not the whole
# index). Same-domain pages embed close together, so cosine alone can't tell
# "EGFR" from "ALK" — the Flash rerank restores that precision at ~1/7th the
# routing tokens (12 summaries vs the full index).
# Shortlist size for the Flash rerank. Kept small (6): graph expansion recovers
# recall, so a smaller, cheaper rerank yields the same pages — A/B confirmed
# identical results at ~40% lower routing cost vs 12.
_EMBED_SHORTLIST = 6


def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    from google.genai import types
    resp = get_client().models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(task_type=task_type, output_dimensionality=EMBED_DIM),
    )
    return [list(e.values) for e in resp.embeddings]


def _page_embed_text(path: Path) -> str:
    """Representative text for a page: title + lead prose (enough to capture the
    topic, cheap to embed)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return path.stem
    fm, body = parse_frontmatter(text)
    title = (fm.get("title", path.stem) or path.stem).strip().strip('"').strip("'")
    # drop headings/blockquotes from the lead so we embed actual content
    prose = "\n".join(
        ln for ln in body.splitlines()
        if ln.strip() and not ln.lstrip().startswith(("#", ">", "---"))
    )
    return f"{title}\n{prose[:800]}"


def _embed_cache_load() -> dict:
    if EMBED_CACHE.exists():
        try:
            return json.loads(EMBED_CACHE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _embed_cache_save(cache: dict) -> None:
    EMBED_CACHE.write_text(json.dumps(cache), encoding="utf-8")


def build_page_embeddings(force: bool = False) -> int:
    """Embed every synthesis-eligible page whose content changed (hash-keyed).
    Incremental: a no-op when nothing changed. Returns the count re-embedded."""
    cache = _embed_cache_load()
    pages = [p for p in list_wiki_pages() if p.stem not in ("index", "log", "overview")]

    todo_text: list[str] = []
    todo_meta: list[tuple[str, str]] = []
    for p in pages:
        txt = _page_embed_text(p)
        h = hashlib.md5(txt.encode("utf-8")).hexdigest()
        if not force and cache.get(p.stem, {}).get("hash") == h:
            continue
        todo_text.append(txt)
        todo_meta.append((p.stem, h))

    for i in range(0, len(todo_text), 100):
        vecs = _embed(todo_text[i:i + 100], "RETRIEVAL_DOCUMENT")
        for (stem, h), v in zip(todo_meta[i:i + 100], vecs):
            cache[stem] = {"hash": h, "vec": v}

    valid = {p.stem for p in pages}
    cache = {k: v for k, v in cache.items() if k in valid}
    _embed_cache_save(cache)
    return len(todo_text)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _embed_shortlist(query: str, n: int = _EMBED_SHORTLIST) -> list[str]:
    build_page_embeddings()  # lazy/incremental keep-in-sync
    cache = _embed_cache_load()
    if not cache:
        return []
    qv = _embed([query], "RETRIEVAL_QUERY")[0]
    scored = sorted(
        ((stem, _cosine(qv, d["vec"])) for stem, d in cache.items()),
        key=lambda x: -x[1],
    )
    return [s for s, _ in scored[:n] if _synthesis_page_path(s) is not None]


def select_relevant_pages_embed(
    query: str, shortlist: int = _EMBED_SHORTLIST, graph: bool = True, graph_max_add: int = 3
) -> tuple[list[str], TokenUsage]:
    """Hybrid router: embedding shortlist -> Flash rerank over candidate
    summaries (NOT the whole index) -> optional graph expansion. Returns chosen
    stems + the Flash token cost (the query embedding is negligible and not
    billed like generation)."""
    candidates = _embed_shortlist(query, n=shortlist)
    if not candidates:
        return [], TokenUsage()

    catalog = "\n".join(f"- {s}: {_page_summary(_synthesis_page_path(s))}" for s in candidates)
    prompt = f"""You are a retrieval router. From the candidate pages below (already pre-filtered for similarity), return the filenames most relevant to answering the question.

Return STRICTLY a JSON array of filenames (a subset of the candidates), most-relevant first. Max 6. If none fit, return [].

QUESTION:
{query}

CANDIDATE PAGES:
{catalog}
"""
    resp = get_client().models.generate_content(model=MODEL_FLASH, contents=prompt)
    parsed = _extract_json(resp.text or "")
    allow = set(candidates)
    picked = [p for p in parsed if isinstance(p, str) and p in allow] if isinstance(parsed, list) else []
    # Retrieval floor: an empty rerank ("none fit") must not discard the reasoning
    # scaffold. Salvage the best-matched disease framework from the shortlist plus
    # the cross-cutting lenses, so even a niche query that still grounds is shaped
    # by the framework + lenses (companion-pin below then adds the framework's
    # cancer entity, which carries grounded content) -> the answer becomes mixed,
    # not web-only.
    if not picked:
        picked = _retrieval_floor(candidates)
    # Hybrid: expand the semantic picks with graph neighbors (note -> hub ->
    # related notes), so relationally-connected context the embedding missed
    # comes along. Conservative cap to bound synthesis cost.
    if graph:
        extra = graph_expand(picked, max_add=graph_max_add)
        picked = picked + [e for e in extra if e not in picked]
    # Pin the reasoning lenses any picked page links to. Pinned (not scored): a
    # lens like [[efficacy]] is linked from many drugs, so graph_expand's
    # inverse-hub weighting would suppress exactly the lenses we most want.
    pinned = _pin_linked_principles(picked)
    picked = picked + [p for p in pinned if p not in picked]
    # Companion pin: when a disease FRAMEWORK (e.g. nsclc-approach) is picked, also
    # pull in its cancer ENTITY (nsclc), which carries the grounded drug/trial
    # facts. Otherwise a disease-level question routes to the framework + lenses
    # only and re-grounds for content we already have on the entity page.
    companions = _pin_companion_entities(picked)
    picked = picked + [c for c in companions if c not in picked]
    return picked, _tokens(resp)


def _retrieval_floor(candidates: list[str]) -> list[str]:
    """Fallback when the reranker picks nothing. Returns the best-matched disease
    framework in the embedding shortlist (highest-cosine '<cancer>-approach') plus
    all cross-cutting lenses. The cross-cutting lenses are disease-agnostic, so
    they are always a safe reasoning floor; the framework targets the query's
    disease. Empty only if there are no principle pages at all."""
    princ = _principle_stems()
    lenses = sorted(s for s in princ if not s.endswith("-approach"))
    framework = next((c for c in candidates if c in princ and c.endswith("-approach")), None)
    floor = ([framework] if framework else []) + lenses
    return [s for s in floor if _synthesis_page_path(s) is not None]


def _pin_companion_entities(picked: list[str]) -> list[str]:
    """Pin the companion across the framework<->entity pair, in both directions:
    a picked disease-framework ('<cancer>-approach') pulls in its cancer entity
    (which carries grounded drug/trial facts); a picked cancer entity pulls in its
    framework (the reasoning order). This is how frameworks reach context — not via
    lens-adjacency, which would cascade to every disease."""
    princ = _principle_stems()
    out: list[str] = []
    for p in picked:
        companion = None
        if p in princ and p.endswith("-approach"):
            companion = p[: -len("-approach")]          # framework -> its cancer entity
        elif f"{p}-approach" in princ:
            companion = f"{p}-approach"                  # cancer entity -> its framework
        if (companion and companion not in picked and companion not in out
                and _synthesis_page_path(companion) is not None):
            out.append(companion)
    return out


_PRINCIPLE_STEMS: set[str] | None = None
_PRINCIPLE_SIG = None


def _principle_stems() -> set[str]:
    """Stems of all principle pages (wiki/principles/*.md), cached by dir state."""
    global _PRINCIPLE_STEMS, _PRINCIPLE_SIG
    if not PRINCIPLES_DIR.exists():
        return set()
    pages = list(PRINCIPLES_DIR.glob("*.md"))
    sig = (len(pages), max((p.stat().st_mtime for p in pages), default=0.0))
    if _PRINCIPLE_STEMS is not None and _PRINCIPLE_SIG == sig:
        return _PRINCIPLE_STEMS
    _PRINCIPLE_STEMS, _PRINCIPLE_SIG = {p.stem for p in pages}, sig
    return _PRINCIPLE_STEMS


def user_principles_dir(user: str) -> Path:
    """Per-provider lens overrides: wiki/avatar/{user}/principles/. A fork here
    wins over the shared skeleton in wiki/principles/ at both pin- and grow-time."""
    return WIKI / "avatar" / user / "principles"


def resolve_principle_path(stem: str, user: str) -> Path | None:
    """Resolve a principle stem to the page to actually USE for this provider:
    their personal fork if it exists, else the shared skeleton, else None. This is
    where a provider's standing reasoning style ('how *I* weigh toxicity') takes
    precedence — the wikilink/edge is shared, the resolved content is personal."""
    override = user_principles_dir(user) / f"{stem}.md"
    if override.exists():
        return override
    shared = PRINCIPLES_DIR / f"{stem}.md"
    return shared if shared.exists() else None


def fork_principle(stem: str, user: str) -> Path:
    """Copy the shared lens into the provider's avatar so they can flavor it.
    Idempotent: returns the existing fork if already present. Stamps `user:` and a
    `forked_from:` marker; the shared skeleton is never modified."""
    dest = user_principles_dir(user) / f"{stem}.md"
    if dest.exists():
        return dest
    src = PRINCIPLES_DIR / f"{stem}.md"
    if not src.exists():
        raise FileNotFoundError(f"No shared principle '{stem}' to fork.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = src.read_text(encoding="utf-8")
    # Insert ownership markers into the frontmatter at string level — preserves the
    # original YAML (e.g. `applies_to: [drug, trial]`) that a flatten/redump loses.
    marker = f"user: {user}\nforked_from: principles/{stem}\n"
    if text.startswith("---\n") and (end := text.find("\n---\n", 4)) != -1:
        text = text[: end + 1] + marker + text[end + 1 :]
    else:
        text = f"---\n{marker}---\n\n{text}"
    dest.write_text(text, encoding="utf-8")
    return dest


def list_principle_status(user: str) -> list[dict]:
    """Every shared lens + whether this provider has forked (personalized) it."""
    out: list[dict] = []
    for p in sorted(PRINCIPLES_DIR.glob("*.md")):
        fm, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
        out.append({
            "stem": p.stem,
            "title": (fm.get("title", p.stem) or p.stem).strip().strip('"'),
            "principle_kind": (fm.get("principle_kind", "") or "").strip().strip('"'),
            "forked": (user_principles_dir(user) / f"{p.stem}.md").exists(),
        })
    return out


def _pin_linked_principles(picked: list[str]) -> list[str]:
    """Cross-cutting LENSES directly linked (1 hop) from any picked page — always
    included so the reasoning lens travels with the entity into synthesis. Disease
    frameworks ('*-approach') are deliberately excluded here: every framework links
    the lenses, so in the undirected graph a lens is adjacent to ALL frameworks —
    pinning them would cascade to every disease. Frameworks ride in via the
    companion relationship instead (_pin_companion_entities)."""
    princ = _principle_stems()
    if not picked or not princ:
        return []
    adj = build_link_graph()
    out: list[str] = []
    for p in picked:
        for nb in adj.get(p, ()):
            if (nb in princ and not nb.endswith("-approach")
                    and nb not in out and _synthesis_page_path(nb) is not None):
                out.append(nb)
    return out


# ---------------------------------------------------------------------------
# Wikilink graph (in-core, always fresh) — used to expand retrieval with
# relationally-connected pages. Self-contained; the kg_server MCP is the
# interactive twin over the same wikilinks.
# ---------------------------------------------------------------------------

_LINK_GRAPH: dict | None = None
_LINK_GRAPH_SIG = None


def _graph_pages() -> list[Path]:
    out = []
    for p in WIKI.rglob("*.md"):
        if any(part.startswith(".") for part in p.parts):
            continue
        if "avatar" in p.parts or p.stem in ("index", "log", "overview"):
            continue
        out.append(p)  # includes stubs — they're the connecting hubs
    return out


def build_link_graph() -> dict:
    """Undirected adjacency from [[wikilinks]] across all knowledge pages.
    Cached; rebuilt when the page set or any mtime changes."""
    global _LINK_GRAPH, _LINK_GRAPH_SIG
    pages = _graph_pages()
    sig = (len(pages), max((p.stat().st_mtime for p in pages), default=0.0))
    if _LINK_GRAPH is not None and _LINK_GRAPH_SIG == sig:
        return _LINK_GRAPH
    adj: dict[str, set] = defaultdict(set)
    for p in pages:
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        for link in re.findall(r"\[\[([^\]|#]+)", text):
            t = link.strip()
            if t and t != p.stem:
                adj[p.stem].add(t)
                adj[t].add(p.stem)
    _LINK_GRAPH, _LINK_GRAPH_SIG = adj, sig
    return adj


def graph_expand(picked: list[str], max_add: int = 3, min_score: float = 0.5) -> list[str]:
    """Synthesis-eligible pages relationally connected to the picked set, scored
    by shared-hub SPECIFICITY: each hub shared between a picked page and a
    candidate contributes 1/degree(hub). So a specific hub (osimertinib, links
    only EGFR notes) is a strong signal, while a generic one (pembrolizumab,
    links many cancers) barely counts — killing cross-topic noise. Only pages
    reaching min_score are added, capped at max_add. Adaptive: hub-rich topics
    expand, isolated ones don't."""
    if not picked:
        return []
    adj = build_link_graph()
    # Principle-blind: lenses (efficacy, adverse-events, …) are linked from nearly
    # every entity, so traversing THROUGH them — or surfacing them as neighbors —
    # would bridge unrelated topics (RCC↔myeloma "share efficacy"). They reach the
    # answer only via deterministic pinning (_pin_linked_principles), never via
    # graph expansion. So we exclude them as both hubs and candidates.
    princ = _principle_stems()
    pick = set(picked)
    deg = {n: len(neigh) for n, neigh in adj.items()}
    score: dict[str, float] = defaultdict(float)
    for p in picked:
        if p in princ:  # never expand FROM a lens/framework — its undirected
            continue    # adjacency is ~the whole corpus (everything links efficacy)
        for hub in adj.get(p, ()):  # each hub the picked page links to
            if hub in princ:  # never traverse through a lens hub
                continue
            w = 1.0 / deg.get(hub, 1)  # inverse hub degree = specificity
            for cand in adj.get(hub, ()):  # other pages sharing that hub
                if (cand not in pick and cand != p and cand not in princ
                        and _synthesis_page_path(cand) is not None):
                    score[cand] += w
    ranked = sorted(score.items(), key=lambda x: -x[1])
    return [s for s, sc in ranked[:max_add] if sc >= min_score]


# ---------------------------------------------------------------------------
# Per-note entity-linking (auto-link on ingest) — connect a note to EXISTING
# entities/concepts/sources/hubs. Batch hub-creation lives in link_notes.py.
# ---------------------------------------------------------------------------


def _entity_link_keymap() -> dict[str, str]:
    m: dict[str, str] = {}
    for p in WIKI.rglob("*.md"):
        if any(part.startswith(".") for part in p.parts) or "avatar" in p.parts:
            continue
        if p.parent.name not in ("entities", "concepts", "sources", "stubs"):
            continue
        stem = p.stem
        keys = {stem.lower(), stem.replace("-", " ").lower()}
        try:
            fm, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
        except OSError:
            fm = {}
        title = (fm.get("title", "") or "").strip().strip('"').strip("'").lower()
        if title:
            keys.add(title)
        for a in re.findall(r'"([^"]+)"', fm.get("aliases", "") or ""):
            keys.add(a.lower())
        for k in keys:
            if len(k) >= 3:
                m.setdefault(k, stem)
    return m


def extract_note_entities(title: str, body: str) -> list[str]:
    prompt = (
        "List the specific named entities this clinical note discusses that each merit "
        "their own wiki page — drugs, clinical trials, biomarkers/genes, cancer types, "
        "key concepts. Return STRICTLY a JSON array of short canonical names. Max 15.\n\n"
        f"NOTE: {title}\n\n{body[:1800]}"
    )
    resp = get_client().models.generate_content(model=MODEL_FLASH, contents=prompt)
    parsed = _extract_json(resp.text or "")
    return [x for x in parsed if isinstance(x, str)] if isinstance(parsed, list) else []


def _set_related_section(text: str, stems: list[str]) -> str:
    text = re.sub(r"\n## Related\n.*?(?=\n## |\Z)", "\n", text, flags=re.DOTALL)
    block = "## Related\n\n" + "\n".join(f"- [[{s}]]" for s in stems) + "\n"
    if "## Provenance" in text:
        return text.replace("## Provenance", block + "\n## Provenance", 1)
    return text.rstrip() + "\n\n" + block


def _scan_body_for_entities(body: str, keymap: dict[str, str], exclude_stem: str) -> list[str]:
    """Deterministic backstop for note linking: whole-word match every known
    entity name/alias against the note body. Reliable where the LLM extractor is
    flaky — if the text says 'pembrolizumab', it links [[pembrolizumab]]. Min key
    length 4 + word boundaries avoid short/substring false positives."""
    low = body.lower()
    out: list[str] = []
    for key, stem in keymap.items():
        if len(key) < 4 or stem == exclude_stem:
            continue
        if re.search(r"\b" + re.escape(key) + r"\b", low):
            if stem not in out:
                out.append(stem)
    return out


def link_note_to_graph(note_path: Path) -> list[str]:
    """Link a note to EXISTING pages/hubs via a `## Related` section. Combines an
    LLM entity extraction with a deterministic keymap body-scan (the scan is the
    reliable floor; the LLM adds canonical names phrased differently). One Flash
    call. Returns the linked stems."""
    try:
        text = note_path.read_text(encoding="utf-8")
    except OSError:
        return []
    fm, body = parse_frontmatter(text)
    title = (fm.get("title", note_path.stem) or note_path.stem).strip().strip('"')
    keymap = _entity_link_keymap()
    stems: list[str] = []
    try:
        for name in extract_note_entities(title, body):
            for cand in (name.lower(), kebab(name), kebab(name).replace("-", " ")):
                if cand in keymap:
                    s = keymap[cand]
                    if s != note_path.stem and s not in stems:
                        stems.append(s)
                    break
    except Exception:  # noqa: BLE001 — LLM extraction is best-effort; scan is the floor
        pass
    # Deterministic backstop — guarantees named existing entities get linked.
    for s in _scan_body_for_entities(body, keymap, note_path.stem):
        if s not in stems:
            stems.append(s)
    if stems:
        note_path.write_text(_set_related_section(text, stems), encoding="utf-8")
    return stems


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


def synthesize_wiki_answer(
    query: str, page_contents: dict[str, str], institutional: str = ""
) -> tuple[str, bool, TokenUsage]:
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
{pages_text}{institutional}
"""
    resp = get_client().models.generate_content(model=MODEL_PRO, contents=prompt)
    answer = (resp.text or "").strip()
    sufficient = not answer.upper().startswith("INSUFFICIENT_WIKI_DATA")
    return answer, sufficient, _tokens(resp)


def synthesize_internet_answer(query: str, page_contents: dict[str, str], institutional: str = ""):
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
{pages_text}{institutional}
"""
    resp = get_client().models.generate_content(
        model=MODEL_PRO,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
        ),
    )
    return (resp.text or "").strip(), resp, _tokens(resp)


# ---------------------------------------------------------------------------
# Save grounded responses to raw/searches/ — same format as search.py
# ---------------------------------------------------------------------------


def save_grounded_response_to_raw(query: str, response, model: str):
    """Write a grounded response as a clean source file. Returns
    (path, cited_text, sources): the cited_text (inline [domain](url) citations,
    redirect URLs resolved) and resolved sources are reused to bake the SAME
    grounded citations into the wiki note — without resolving URLs twice."""
    metadata = None
    if response.candidates and response.candidates[0].grounding_metadata:
        metadata = response.candidates[0].grounding_metadata

    raw_text = response.text or ""
    text_with_cites = build_inline_citations(raw_text, metadata)
    sources = extract_sources(metadata)

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
    return filepath, text_with_cites, sources


# ---------------------------------------------------------------------------
# Auto-ingest: extract entities → write stub pages → update index + log
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
    existing = ", ".join(_all_known_stems())
    prompt = _ENTITY_EXTRACT_PROMPT.format(existing=existing, query=query, answer=answer)
    resp = get_client().models.generate_content(model=MODEL_FLASH, contents=prompt)
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

    stub_target = "entities" if typ in ("drug", "trial", "cancer", "biomarker") else "concepts"
    STUBS_DIR.mkdir(parents=True, exist_ok=True)
    target_path = STUBS_DIR / f"{filename}.md"

    if target_path.exists() or _synthesis_page_path(filename) is not None:
        return None  # never overwrite, never shadow a curated page

    aliases_yaml = json.dumps(aliases) if aliases else "[]"
    entity_type_field = typ if typ != "concept" else "other"
    source_stem = Path(source_filename).stem

    body = f"""---
title: "{name}"
entity_type: {entity_type_field}
aliases: {aliases_yaml}
auto_generated: true
stub_target: {stub_target}
auto_source: "[[{source_stem}]]"
auto_date: {date.today().isoformat()}
tags: [auto-generated]
---

# {name}

> ⚠️ **Auto-generated stub** (quarantined in `wiki/stubs/`, excluded from query synthesis). Verify and expand before relying on this for clinical decisions. Promoting it moves the page into `wiki/{stub_target}/`.

## Brief

{brief}

## Why this matters

{relevance if relevance else "(not specified)"}

## Sources

- [[{source_stem}]] — origin search; see for full grounded citations and search queries
"""
    target_path.write_text(body, encoding="utf-8")
    return target_path


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
# Re-index + auto-ingested searchable notes
# ---------------------------------------------------------------------------


def upsert_index_entry(stem: str, summary: str, section: str = "Notes") -> None:
    """Add or refresh a `- [[stem]] — summary` line under `### {section}` (or
    `## {section}`) in wiki/index.md, so the router (which reads ONLY index.md)
    can find the page. This is the "re-index" step that was missing — without
    it, a page on disk is invisible to query routing.
    """
    index_path = WIKI / "index.md"
    if not index_path.exists():
        return
    summary = " ".join(summary.split())[:140]
    bullet = f"- [[{stem}]] — {summary}"
    lines = index_path.read_text(encoding="utf-8").splitlines()

    def is_header(s: str) -> bool:
        t = s.lstrip()
        return t.startswith("## ") or t.startswith("### ")

    # Locate the section header (accept either ## or ### level).
    hdr = None
    for i, ln in enumerate(lines):
        t = ln.strip()
        if t == f"### {section}" or t == f"## {section}":
            hdr = i
            break

    if hdr is None:
        # Create the subsection under "## Sources" if present, else append.
        insert_at = len(lines)
        for i, ln in enumerate(lines):
            if ln.strip() == "## Sources":
                insert_at = i + 1
                break
        lines[insert_at:insert_at] = ["", f"### {section}", "", bullet]
        index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    end = len(lines)
    for j in range(hdr + 1, len(lines)):
        if is_header(lines[j]):
            end = j
            break

    # Replace an existing entry for this stem, if any.
    for j in range(hdr + 1, end):
        if lines[j].strip().startswith(f"- [[{stem}]]"):
            lines[j] = bullet
            index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            return

    # Otherwise insert after the header (replacing a "*(none yet)*" placeholder).
    pos = hdr + 1
    while pos < end and lines[pos].strip() == "":
        pos += 1
    if pos < end and lines[pos].strip() in ("*(none yet)*", "_(none yet)_"):
        lines[pos] = bullet
    else:
        lines.insert(pos, bullet)
    index_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _yaml_str(value: str) -> str:
    """Quote a string for single-line YAML, collapsing newlines."""
    flat = " ".join(value.split())
    return '"' + flat.replace('"', "'") + '"'


def write_answer_note(
    question: str, answer: str, source_filename: str, sources: list[dict] | None = None
) -> Path | None:
    """Write the synthesized internet answer as a SEARCHABLE, editable note page
    in wiki/notes/. `answer` should be the citation-annotated text (inline
    [domain](url) links from grounding); `sources` (resolved) is rendered as a
    numbered web-sources section, so the note carries full provenance on its own.

    Idempotent by question slug: if the note already exists it is preserved (so
    user edits / verification survive a re-ask) and None is returned while the
    caller still refreshes the index.
    """
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    slug = kebab(question)
    target = NOTES_DIR / f"{slug}.md"
    if target.exists():
        return None  # preserve existing edits/verification

    today = date.today().isoformat()
    source_stem = Path(source_filename).stem
    title = " ".join(question.split())[:120]

    sources_block = ""
    if sources:
        lines = []
        for i, s in enumerate(sources, 1):
            t = (s.get("title") or "source").strip()
            u = (s.get("url") or "").strip()
            lines.append(f"{i}. [{t}]({u})" if u else f"{i}. {t}")
        sources_block = "## Web sources (grounded)\n\n" + "\n".join(lines) + "\n\n"

    body = f"""---
title: {_yaml_str(title)}
auto_generated: true
auto_date: {today}
verified: false
verified_by: ""
verified_date: ""
source_question: {_yaml_str(title)}
raw_source: "[[{source_stem}]]"
tags: [auto-ingested]
---

# {title}

> 🌱 **Auto-ingested from an internet search on {today}.** This page is searchable and editable. It has **not** been verified — correct any fact by editing this page, then mark it verified.

{answer}

{sources_block}## Provenance

- **Ingested:** {today} (auto, unverified)
- **Raw grounded search:** [[{source_stem}]] — full citations + search queries
"""
    target.write_text(body, encoding="utf-8")
    return target


def append_note_ingest_log(note_path: Path, source_path: Path, question: str, user: str, created: bool) -> None:
    today = date.today().isoformat()
    entry = f"""
## [{today}] auto-ingest-note | searchable internet answer

- **User:** {user}
- **Triggering query:** "{question[:100]}{'...' if len(question) > 100 else ''}"
- **Note page:** [[{note_path.stem}]] (`wiki/notes/{note_path.name}`) — {'created' if created else 'already existed; index refreshed'}
- **Raw source:** [[{source_path.stem}]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.
"""
    log = WIKI / "log.md"
    if log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(entry)


def _set_frontmatter_field(text: str, key: str, value: str) -> str:
    """Set/insert a single-line frontmatter `key: value`, preserving the rest."""
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---\n", 4)
    if end == -1:
        return text
    fm = text[4:end]
    rest = text[end:]
    line = f"{key}: {value}"
    pat = re.compile(rf"(?m)^{re.escape(key)}:.*$")
    if pat.search(fm):
        fm = pat.sub(line, fm, count=1)
    else:
        fm = fm.rstrip("\n") + "\n" + line
    return "---\n" + fm + rest


def list_note_pages() -> list[Path]:
    """Auto-ingested searchable notes in wiki/notes/, mtime-sorted desc."""
    if not NOTES_DIR.exists():
        return []
    files = list(NOTES_DIR.glob("*.md"))
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return files


def remove_index_entry(stem: str) -> None:
    """Drop the `- [[stem]] — …` line from index.md, if present."""
    index_path = WIKI / "index.md"
    if not index_path.exists():
        return
    lines = index_path.read_text(encoding="utf-8").splitlines()
    kept = [ln for ln in lines if not ln.strip().startswith(f"- [[{stem}]]")]
    if len(kept) != len(lines):
        index_path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def delete_note(path: Path, user: str, reason: str = "") -> bool:
    """Delete a note page AND remove its index entry (so the router won't point
    at a missing page). Recoverable via git restore."""
    if not path.exists():
        return False
    stem = path.stem
    today = date.today().isoformat()
    try:
        path.unlink()
    except OSError:
        return False
    remove_index_entry(stem)

    log = WIKI / "log.md"
    if log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(
                f"\n## [{today}] delete-note | {stem}\n\n"
                f"- **User:** {user}\n"
                f"- **Page:** `wiki/notes/{stem}.md` (deleted; index entry removed)\n"
                f"- **Reason:** {reason if reason else '(not specified)'}\n"
                f"- **Recovery:** `git restore wiki/notes/{stem}.md` (re-index on next ingest).\n"
            )
    return True


def mark_note_verified(path: Path, user: str) -> bool:
    """Stamp a note as verified by `user` on today's date. Records the reviewer."""
    if not path.exists():
        return False
    today = date.today().isoformat()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    text = _set_frontmatter_field(text, "verified", "true")
    text = _set_frontmatter_field(text, "verified_by", user)
    text = _set_frontmatter_field(text, "verified_date", today)
    # Swap the unverified banner for a verified one (best-effort).
    text = re.sub(
        r">\s*🌱\s*\*\*Auto-ingested[^\n]*\n",
        f"> ✅ **Verified by {user} on {today}.** Auto-ingested from an internet search; reviewed and confirmed.\n",
        text,
        count=1,
    )
    path.write_text(text, encoding="utf-8")

    log = WIKI / "log.md"
    if log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(
                f"\n## [{today}] verify-note | {path.stem}\n\n"
                f"- **User:** {user}\n"
                f"- **Page:** [[{path.stem}]] (`wiki/notes/{path.name}`)\n"
                f"- **Action:** marked verified; recorded reviewer ({user}) + date ({today}).\n"
            )
    return True


def _page_summary(path: Path) -> str:
    """Build a one-line catalog summary for a page: its lead sentence (from the
    first prose paragraph, e.g. ## Brief) plus any aliases for keyword recall."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return path.stem
    fm, body = parse_frontmatter(text)

    sentence = ""
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith(">") or s.startswith("---"):
            continue
        sentence = s
        break
    # keep just the first sentence
    sentence = re.split(r"(?<=[.!?])\s", sentence)[0].strip() if sentence else ""

    aliases = re.findall(r'"([^"]+)"', fm.get("aliases", "") or "")
    title = (fm.get("title", path.stem) or path.stem).strip().strip('"').strip("'")

    summary = sentence or title
    if aliases:
        summary = f"{summary} (aka {', '.join(aliases)})"
    return summary


def index_gaps() -> list[Path]:
    """Synthesis-eligible pages that exist on disk but are NOT referenced in
    index.md — i.e. invisible to the router. (The active recall hole.)"""
    idx = _read_index()
    linked = set(re.findall(r"\[\[([^\]|#]+)", idx))
    out: list[Path] = []
    for p in list_wiki_pages():
        if p.stem in ("index", "log", "overview"):
            continue
        if p.stem in linked:
            continue
        if p.parent.name in ("entities", "concepts", "notes"):
            out.append(p)
    return out


def reconcile_index(user: str = DEFAULT_USER) -> list[str]:
    """Add an index.md entry for every synthesis-eligible page missing from it,
    so the router can reach it. Idempotent. Returns the stems added."""
    section_for = {"entities": "Entities", "concepts": "Concepts", "notes": "Notes"}
    added: list[str] = []
    for p in index_gaps():
        section = section_for.get(p.parent.name)
        if not section:
            continue
        upsert_index_entry(p.stem, _page_summary(p), section=section)
        added.append(p.stem)

    if added:
        today = date.today().isoformat()
        listing = "\n".join(f"  - [[{s}]]" for s in added)
        log = WIKI / "log.md"
        if log.exists():
            with log.open("a", encoding="utf-8") as f:
                f.write(
                    f"\n## [{today}] reconcile-index | added {len(added)} missing page(s)\n\n"
                    f"- **User:** {user}\n"
                    f"- **Why:** these pages existed on disk but were absent from index.md, so the "
                    f"router could not reach them (silent recall hole).\n"
                    f"- **Pages indexed ({len(added)}):**\n{listing}\n"
                )
    return added


# ---------------------------------------------------------------------------
# Preference elicitation
# ---------------------------------------------------------------------------


_MC_PROMPT = """You design preference probes that capture a clinician's judgment — their avatar — from how they would APPLY an answer to a real patient.

Generate ONE multiple-choice question (2–4 options) for essentially every clinically-relevant question. Bias STRONGLY toward generating a probe; skipping is rare. When in doubt, generate one.

PRIMARY RULE — if the answer presents more than one option, ALWAYS make a selection probe:
When the answer names more than one treatment, regimen, sequence, or strategy, there is ALWAYS a real preference to capture — even if every option is guideline-endorsed standard of care. Do NOT skip these as "settled." Which option a clinician favors, and why, is exactly the judgment worth capturing. Default probe:
  "For [a typical patient matching the question], which would you choose?"
with those options (drawn verbatim from the answer) as the choices.

Reframing by question type:
- "Tell me about X" / "What's the data on Y" → "For a patient with [typical scenario], would you favor X or [the alternative]?"
- "First-line / how do you select for X" → "For [specific profile], which of [the options in the answer] would you choose?"
- "Should I do X for this patient?" → MC directly with the options at hand.
- Genuinely single-option settled care → probe a real axis of variation instead: timing, sequencing, escalation threshold, treatment duration, monitoring intensity, or an edge-case patient profile where reasonable clinicians differ.

Each option must be:
- Defensible on the evidence in the answer
- Genuinely distinct (different trade-off weighting — efficacy vs toxicity, CNS vs ILD risk, off-label comfort, guideline conformity, QoL/fertility, cost/access)
- A concrete clinical action a real clinician might take

Return STRICTLY a single JSON object:
{{
  "label": "<short kebab-case label, ≤40 chars>",
  "question": "<the MC question — framed as applied to a hypothetical or general patient profile, not 'what do you want to know'>",
  "options": [
    {{"key": "A", "text": "<option A — concrete clinical action>"}},
    {{"key": "B", "text": "<option B>"}}
  ],
  "rationale": "<one sentence on what this probe reveals about the user's preferences>"
}}

Skip — return EXACTLY {{"label": null}} — ONLY for a purely factual or definitional question with no management choice in any direction (e.g., "what does AMH stand for?", "list the breast cancer subtypes", "what is the half-life of drug X?"). If the answer contains ANY treatment options or management decision, do NOT skip.

QUESTION:
{question}

ANSWER:
{answer}
"""


def generate_preference_mc(query: str, answer: str) -> tuple[MCQuestion | None, TokenUsage]:
    # Stays on Pro: the cost win is from making this LAZY (on-demand, not every
    # query), so quality matters more than per-call cost here. Flash skips too
    # readily ("label: null") for borderline-but-useful probes.
    resp = get_client().models.generate_content(
        model=MODEL_PRO, contents=_MC_PROMPT.format(question=query, answer=answer)
    )
    parsed = _extract_json_object(resp.text or "")
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
- **Trigger:** Web UI query
- **Wiki pages consulted:** {sources_str}
- **Gemini calls:** {turn.gemini_calls}
- **Answer origin:** {turn.origin}
- **Tokens (Gemini):** {turn.tokens.total}{extras}
"""
    questions_entry = f"""
### [{today}] {safe_label}

- **Question:** "{turn.question}"
- **Trigger:** Web UI query
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
# Session persistence
# ---------------------------------------------------------------------------


def session_file_for(user: str) -> Path:
    return SESSIONS_DIR / f"{user}-{date.today().isoformat()}.jsonl"


def turn_to_dict(turn: Turn) -> dict:
    return {
        "idx": turn.idx,
        "ts": turn.ts or datetime.now(timezone.utc).isoformat(),
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
        "note_created": turn.note_created,
    }


def turn_from_dict(d: dict) -> Turn:
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
        note_created=d.get("note_created"),
        ts=d.get("ts", ""),
    )


def append_turn_to_session(turn: Turn, user: str) -> None:
    f = session_file_for(user)
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("a", encoding="utf-8") as h:
        h.write(json.dumps(turn_to_dict(turn)) + "\n")


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
                turns.append(turn_from_dict(json.loads(line)))
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    return turns


def rewrite_session(user: str, turns: list[Turn]) -> None:
    """Rewrite today's session JSONL from the given turns (e.g. after MC capture)."""
    f = session_file_for(user)
    f.parent.mkdir(parents=True, exist_ok=True)
    with f.open("w", encoding="utf-8") as h:
        for turn in turns:
            h.write(json.dumps(turn_to_dict(turn)) + "\n")


# ---------------------------------------------------------------------------
# Query orchestration
# ---------------------------------------------------------------------------


def run_query_phase1(question: str, user: str, idx: int):
    """Route, synthesize, generate MC. Returns (Turn, grounded_response_or_None)."""
    total_tokens = TokenUsage()
    gemini_calls = 0

    # Cheap embedding-shortlist + Flash rerank instead of sending the whole index.
    pages, t1 = select_relevant_pages_embed(question)
    total_tokens = total_tokens + t1
    gemini_calls += 1

    page_contents = _load_pages(pages, user)
    inst = institutional_context(pages)  # preference-weight by formulary/pathways
    answer, sufficient, t2 = synthesize_wiki_answer(question, page_contents, inst)
    total_tokens = total_tokens + t2
    gemini_calls += 1

    origin = "wiki"
    grounded_resp = None

    if not sufficient:
        answer, grounded_resp, t3 = synthesize_internet_answer(question, page_contents, inst)
        total_tokens = total_tokens + t3
        gemini_calls += 1
        origin = "internet" if not page_contents else "mixed"

    # MC preference probe is now LAZY (generated on demand via /api/preference/probe),
    # not on every query — it's avatar-capture overhead unrelated to answering.
    turn = Turn(
        idx=idx,
        question=question,
        answer=answer,
        sources=pages,
        origin=origin,
        gemini_calls=gemini_calls,
        tokens=total_tokens,
        mc=None,
        saved_search_path=None,
        stubs_created=[],
        ts=datetime.now(timezone.utc).isoformat(),
    )
    return turn, grounded_resp


def run_query_phase2(
    turn: Turn, grounded_resp, question: str, user: str, auto_ingest_enabled: bool
) -> tuple[Turn, list[str]]:
    """Deferred: save grounded response + auto-ingest. Returns (turn, warnings)."""
    warnings: list[str] = []
    cited_body: str | None = None
    sources: list[dict] = []

    try:
        saved_path, cited_body, sources = save_grounded_response_to_raw(
            question, grounded_resp, MODEL_PRO
        )
        if saved_path:
            turn.saved_search_path = str(saved_path)
    except Exception as exc:
        warnings.append(f"Grounded response save failed: {type(exc).__name__}: {exc}")

    if auto_ingest_enabled and turn.saved_search_path:
        try:
            # Ingest the citation-annotated answer (inline grounded URLs + a web
            # sources section) as a SEARCHABLE, editable note, then re-index it so
            # the next identical question is answered from the wiki, not the web.
            note = write_answer_note(
                question, cited_body or turn.answer, turn.saved_search_path, sources
            )
            slug = kebab(question)
            note_path = note if note is not None else (NOTES_DIR / f"{slug}.md")
            upsert_index_entry(note_path.stem, question, section="Notes")
            append_note_ingest_log(
                note_path, Path(turn.saved_search_path), question, user, created=note is not None
            )
            # Auto-link the new note into the graph (link to existing entities/
            # hubs) so it isn't an orphan. Only for freshly-created notes.
            if note is not None:
                try:
                    link_note_to_graph(note_path)
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"Note linking failed: {type(exc).__name__}: {exc}")
            turn.note_created = str(note_path)
        except Exception as exc:
            warnings.append(f"Auto-ingest failed: {type(exc).__name__}: {exc}")

    return turn, warnings


# ---------------------------------------------------------------------------
# Cases — concept pages with Questions sections → captureable case decisions
# ---------------------------------------------------------------------------


_DECISION_SKELETON_RE = re.compile(
    r"^##\s+Decision skeleton[^\n]*\n(.*?)(?=\n##\s|\Z)",
    re.DOTALL | re.MULTILINE,
)
_QUESTIONS_SECTION_RE = re.compile(
    r"^##\s+Questions\s*\n(.*?)(?=\n##\s|\Z)",
    re.DOTALL | re.MULTILINE,
)
_QUESTION_BLOCK_RE = re.compile(
    r"^###\s+(.+?)\n(.*?)(?=\n###\s|\Z)",
    re.DOTALL | re.MULTILINE,
)
_OPTION_BULLET_RE = re.compile(
    r"^\s*-\s+([A-Z])\.\s+(.+?)$",
    re.MULTILINE,
)


def _slugify(text: str, max_len: int = 60) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return s[:max_len]


def _parse_questions_section(section_text: str) -> list[dict]:
    questions: list[dict] = []
    for m in _QUESTION_BLOCK_RE.finditer(section_text):
        q_text = m.group(1).strip()
        body = m.group(2)
        options: list[dict] = []
        for opt in _OPTION_BULLET_RE.finditer(body):
            options.append({"key": opt.group(1), "text": opt.group(2).strip()})
        if not options:
            continue
        questions.append({
            "label": _slugify(q_text),
            "text": q_text,
            "options": options,
        })
    return questions


def find_case_pages() -> list[dict]:
    """Scan wiki/concepts/ for pages with a `## Questions` section."""
    out: list[dict] = []
    concepts_dir = WIKI / "concepts"
    if not concepts_dir.exists():
        return out
    for p in sorted(concepts_dir.glob("*.md")):
        try:
            content = p.read_text(encoding="utf-8")
        except OSError:
            continue
        questions_match = _QUESTIONS_SECTION_RE.search(content)
        if not questions_match:
            continue
        questions = _parse_questions_section(questions_match.group(1))
        if not questions:
            continue

        skeleton_match = _DECISION_SKELETON_RE.search(content)
        skeleton = skeleton_match.group(1).strip() if skeleton_match else ""

        fm, _body = parse_frontmatter(content)
        title = fm.get("title", p.stem).strip().strip('"').strip("'")
        out.append({
            "stem": p.stem,
            "title": title,
            "path": str(p),
            "skeleton": skeleton,
            "questions": questions,
        })
    return out


def case_already_captured(user: str, case_stem: str) -> bool:
    decisions_file = WIKI / "avatar" / user / "decisions.md"
    if not decisions_file.exists():
        return False
    try:
        content = decisions_file.read_text(encoding="utf-8")
    except OSError:
        return False
    return f"linked-concept:{case_stem}" in content or f"case:{case_stem}" in content


def question_already_captured(user: str, case_stem: str, question_label: str) -> bool:
    decisions_file = WIKI / "avatar" / user / "decisions.md"
    if not decisions_file.exists():
        return False
    try:
        content = decisions_file.read_text(encoding="utf-8")
    except OSError:
        return False
    return f"linked-question:{case_stem}::{question_label}" in content


def append_case_question_answer(
    user: str,
    case: dict,
    question: dict,
    selected_keys: list[str],
    comment: str,
) -> None:
    """Write a single question's answer to decisions.md."""
    today = date.today().isoformat()
    options_block = "\n".join(
        f"  - {'☑' if o['key'] in selected_keys else '☐'} **{o['key']}.** {o['text']}"
        for o in question["options"]
    )
    selections_str = ", ".join(selected_keys) if selected_keys else "(none selected)"
    selected_titles = "; ".join(
        next((o["text"] for o in question["options"] if o["key"] == k), "")
        for k in selected_keys
    )

    entry = f"""
### [{today}] {case['stem']} > {question['label']} (case:{case['stem']}, q:{question['label']})

- **Source concept:** [[{case['stem']}]]
- **Question:** {question['text']}
- **Options offered:**
{options_block}
- **Selections:** {selections_str}{f' — {selected_titles}' if selected_titles else ''}
- **Comment:** {comment if comment else "(none)"}
- **linked-concept:{case['stem']}**
- **linked-question:{case['stem']}::{question['label']}**
"""

    _, decisions = _ensure_avatar_files(user)
    with decisions.open("a", encoding="utf-8") as f:
        f.write(entry)

    log = WIKI / "log.md"
    if log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(
                f"\n## [{today}] case-q-answer | {case['stem']} > {question['label']}\n\n"
                f"- **User:** {user}\n"
                f"- **Concept:** [[{case['stem']}]]\n"
                f"- **Question:** {question['text']}\n"
                f"- **Selections:** {selections_str}\n"
                f"- **Comment:** {comment[:120] + ('...' if len(comment) > 120 else '') if comment else '(none)'}\n"
                f"- **Captured via:** Cases tab (web UI)\n"
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
        if "avatar" in p.parts or "notes" in p.parts:
            # Notes are searchable auto-ingested pages with their own listing
            # (list_note_pages); don't surface them in the stub queue.
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


def _safe_resolve(rel_or_abs: str) -> Path | None:
    """Resolve a path (relative to ROOT or absolute) and ensure it stays inside ROOT."""
    p = Path(rel_or_abs)
    if not p.is_absolute():
        p = ROOT / p
    try:
        p = p.resolve()
        p.relative_to(ROOT.resolve())
    except (ValueError, OSError):
        return None
    return p


def promote_stub(path: Path, user: str) -> bool:
    """Promote a quarantined stub: strip auto-generated markers and MOVE the page
    out of wiki/stubs/ into its target folder (entities|concepts)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False

    fm, _body = parse_frontmatter(text)
    target = (fm.get("stub_target") or "").strip()
    if target not in ("entities", "concepts"):
        target = "concepts"

    new_text = re.sub(r"^auto_generated:\s*true\s*\n", "", text, flags=re.MULTILINE)
    new_text = re.sub(r"^stub_target:\s*\S+\s*\n", "", new_text, flags=re.MULTILINE)
    new_text = re.sub(
        r"^(tags:\s*\[)([^\]]*)(\])",
        lambda m: m.group(1)
        + ", ".join(t.strip() for t in m.group(2).split(",") if t.strip() and t.strip() != "auto-generated")
        + m.group(3),
        new_text,
        flags=re.MULTILINE,
    )
    new_text = re.sub(
        r"\n>\s*⚠️\s*\*\*Auto-generated stub\*\*[^\n]*\n(?:>[^\n]*\n)*",
        "\n",
        new_text,
    )

    dest_dir = WIKI / target
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / path.name
    if dest_path.exists() and dest_path.resolve() != path.resolve():
        return False

    dest_path.write_text(new_text, encoding="utf-8")
    moved = dest_path.resolve() != path.resolve()
    if moved:
        try:
            path.unlink()
        except OSError:
            pass

    # Re-index so the promoted page is actually routable (was the silent defect:
    # promotion moved the file but never added it to index.md, leaving it
    # invisible to the router).
    fm_new, _ = parse_frontmatter(new_text)
    summary = (fm_new.get("title") or path.stem).strip().strip('"').strip("'")
    upsert_index_entry(path.stem, summary, section="Concepts" if target == "concepts" else "Entities")

    today = date.today().isoformat()
    log = WIKI / "log.md"
    if log.exists():
        with log.open("a", encoding="utf-8") as f:
            f.write(
                f"\n## [{today}] promote | {path.stem}\n\n"
                f"- **User:** {user}\n"
                f"- **Page:** [[{path.stem}]] → `wiki/{target}/{path.name}`"
                f"{' (moved out of wiki/stubs/)' if moved else ''}\n"
                f"- **Action:** stripped `auto_generated`/`stub_target` markers and warning callout; promoted to the curated namespace.\n"
                f"- **Reminder:** consider an agent ingest to expand to full SCHEMA structure (Overview, Key facts, Related entities, Sources).\n"
            )
    return True


def reject_stub(path: Path, user: str, reason: str = "") -> bool:
    """Delete the stub page. Append a structured log entry. Recoverable via git restore."""
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
    try:
        path.write_text(content, encoding="utf-8")
        return True
    except OSError:
        return False
