"""
Wiki LM — FastAPI backend.

Exposes core.py as a JSON API for the Next.js front end. The two-phase query
flow from the original Streamlit app is preserved: POST /api/query returns the
answer immediately; if a grounded (internet) search ran, the non-serializable
Gemini response is held server-side keyed by a token, and the client calls
POST /api/query/finalize to run the deferred save + auto-ingest.

Run:
    .venv/bin/uvicorn api:app --reload --port 8000
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import core
import question_agent

app = FastAPI(title="Wiki LM API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory hold for grounded Gemini responses awaiting phase-2 finalize.
# Keyed by f"{user}:{turn_idx}". Lives only as long as the server process — a
# pending finalize lost to a restart simply skips the deferred save/ingest.
_PENDING: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def _turn_payload(turn: core.Turn) -> dict:
    return core.turn_to_dict(turn)


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(core.ROOT.resolve()))
    except ValueError:
        return str(path)


def _review_item(path: Path, kind: str) -> dict:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        content = ""
    fm, _body = core.parse_frontmatter(content)
    title = fm.get("title", path.stem).strip().strip('"').strip("'")
    return {
        "id": _rel(path),
        "stem": path.stem,
        "title": title,
        "kind": kind,
        "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat()
        if path.exists()
        else None,
        # Surfaced for note cards: verification state + ingest date.
        "verified": str(fm.get("verified", "")).strip().lower() == "true",
        "verified_by": fm.get("verified_by", "").strip().strip('"').strip("'"),
        "verified_date": fm.get("verified_date", "").strip().strip('"').strip("'"),
        "auto_date": fm.get("auto_date", "").strip(),
    }


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    question: str
    user: str = core.DEFAULT_USER
    auto_ingest: bool = False


class FinalizeRequest(BaseModel):
    token: str
    user: str = core.DEFAULT_USER


class PreferenceRequest(BaseModel):
    user: str
    turn_idx: int
    choice_key: str
    reasoning: str = ""


class CaseAnswerRequest(BaseModel):
    user: str
    case_stem: str
    question_label: str
    selected_keys: list[str] = []
    comment: str = ""


class PageSaveRequest(BaseModel):
    id: str  # path relative to ROOT
    content: str


class StubActionRequest(BaseModel):
    id: str
    user: str = core.DEFAULT_USER
    reason: str = ""


# ---------------------------------------------------------------------------
# Health / state
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict:
    return {
        "ok": True,
        "api_key_present": core.api_key_present(),
        "model_pro": core.MODEL_PRO,
        "model_flash": core.MODEL_FLASH,
        "default_user": core.DEFAULT_USER,
    }


@app.get("/api/state")
def state(user: str = core.DEFAULT_USER) -> dict:
    turns = core.load_today_session(user)
    session_tokens = sum(t.tokens.total for t in turns)

    avatar_dir = core.WIKI / "avatar" / user
    decisions_count = questions_count = 0
    if avatar_dir.exists():
        dp = avatar_dir / "decisions.md"
        qp = avatar_dir / "questions.md"
        if dp.exists():
            decisions_count = dp.read_text(encoding="utf-8").count("###")
        if qp.exists():
            questions_count = qp.read_text(encoding="utf-8").count("###")

    case_pages = core.find_case_pages()
    cases_available = sum(
        1 for c in case_pages if not core.case_already_captured(user, c["stem"])
    )

    return {
        "user": user,
        "history": [_turn_payload(t) for t in turns],
        "stats": {
            "wiki_pages": len(core.list_wiki_pages()),
            "decisions": decisions_count,
            "questions": questions_count,
            "session_queries": len(turns),
            "session_tokens": session_tokens,
            "stubs": len(core.list_auto_generated_pages()),
            "searches": len(core.list_recent_searches()),
            "notes": len(core.list_note_pages()),
            "index_gaps": len(core.index_gaps()),
            "cases_available": cases_available,
        },
        "session_file": str(core.session_file_for(user).relative_to(core.ROOT)),
    }


# ---------------------------------------------------------------------------
# Query (two-phase)
# ---------------------------------------------------------------------------


@app.post("/api/query")
def query(req: QueryRequest) -> dict:
    if not req.question.strip():
        raise HTTPException(400, "Empty question.")
    if not core.api_key_present():
        raise HTTPException(503, "GOOGLE_API_KEY not configured on the server.")

    idx = len(core.load_today_session(req.user))
    try:
        turn, grounded_resp = core.run_query_phase1(req.question, req.user, idx)
    except core.MissingAPIKey as exc:
        raise HTTPException(503, str(exc))
    except Exception as exc:  # noqa: BLE001 — surface model/network failures
        raise HTTPException(500, f"{type(exc).__name__}: {exc}")

    # Persist the (partial) turn immediately, mirroring the original app.
    core.append_turn_to_session(turn, req.user)

    needs_ingest = grounded_resp is not None
    token = None
    if needs_ingest:
        token = f"{req.user}:{turn.idx}"
        _PENDING[token] = {
            "grounded_resp": grounded_resp,
            "question": req.question,
            "user": req.user,
            "auto_ingest": req.auto_ingest,
        }
    else:
        # Wiki-only — log immediately; no phase 2 needed.
        try:
            core.append_question_log(turn, req.user)
        except Exception:  # noqa: BLE001
            pass

    return {
        "turn": _turn_payload(turn),
        "needs_ingest": needs_ingest,
        "token": token,
    }


@app.post("/api/query/finalize")
def finalize(req: FinalizeRequest) -> dict:
    pending = _PENDING.pop(req.token, None)
    if pending is None:
        raise HTTPException(404, "No pending ingest for that token (already finalized?).")

    turns = core.load_today_session(pending["user"])
    _, idx_str = req.token.split(":", 1)
    idx = int(idx_str)
    turn = next((t for t in turns if t.idx == idx), None)
    if turn is None:
        raise HTTPException(404, "Turn not found in session.")

    turn, warnings = core.run_query_phase2(
        turn=turn,
        grounded_resp=pending["grounded_resp"],
        question=pending["question"],
        user=pending["user"],
        auto_ingest_enabled=pending["auto_ingest"],
    )
    try:
        core.append_question_log(turn, pending["user"])
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Audit log failed: {exc}")

    # Persist the now-complete turn back into the session file.
    for i, t in enumerate(turns):
        if t.idx == idx:
            turns[i] = turn
            break
    core.rewrite_session(pending["user"], turns)

    return {"turn": _turn_payload(turn), "warnings": warnings}


class ProbeRequest(BaseModel):
    user: str
    turn_idx: int


class GrowProposeRequest(BaseModel):
    depth_sample: int = 6
    top: int = 30
    covered: float = 0.82


_GROW_FILE = core.RAW / "grow_proposal.json"


def _grow_fresh(items: list[dict]) -> list[dict]:
    """Drop candidates already turned into notes (so a reloaded proposal doesn't
    re-show questions you've since run)."""
    return [
        it for it in items
        if not (core.NOTES_DIR / f"{core.kebab(it['q'])}.md").exists()
    ]


@app.get("/api/grow/proposal")
def grow_proposal() -> dict:
    """Return the last saved proposal (no LLM call) — so the Grow tab survives
    tab switches and reloads without regenerating."""
    if not _GROW_FILE.exists():
        return {"items": [], "saved": False}
    try:
        items = json.loads(_GROW_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"items": [], "saved": False}
    return {"items": _grow_fresh(items), "saved": True}


@app.post("/api/grow/propose")
def grow_propose(req: GrowProposeRequest) -> dict:
    """Run the question agent: propose ranked gap-questions to grow the wiki.
    Slow (LLM harvest + embedding dedup); the client shows a spinner. The result
    is persisted so it survives navigation. Approved questions are then run via
    the normal /api/query + /finalize pipeline."""
    if not core.api_key_present():
        raise HTTPException(503, "GOOGLE_API_KEY not configured.")
    try:
        items = question_agent.propose(
            depth_sample=req.depth_sample, top=req.top, covered=req.covered
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"{type(exc).__name__}: {exc}")
    try:
        _GROW_FILE.write_text(json.dumps(items), encoding="utf-8")
    except OSError:
        pass
    return {"items": items}


@app.post("/api/preference/probe")
def preference_probe(req: ProbeRequest) -> dict:
    """Generate the MC preference probe for a turn ON DEMAND (it's no longer made
    on every query). Persists it onto the turn so it survives reload."""
    turns = core.load_today_session(req.user)
    turn = next((t for t in turns if t.idx == req.turn_idx), None)
    if turn is None:
        raise HTTPException(404, "Turn not found.")
    if turn.mc is None:
        mc, _ = core.generate_preference_mc(turn.question, turn.answer)
        turn.mc = mc
        core.rewrite_session(req.user, turns)
    return {"turn": _turn_payload(turn)}


@app.post("/api/preference")
def preference(req: PreferenceRequest) -> dict:
    turns = core.load_today_session(req.user)
    turn = next((t for t in turns if t.idx == req.turn_idx), None)
    if turn is None or turn.mc is None:
        raise HTTPException(404, "Turn or MC probe not found.")

    core.append_preference_capture(
        user=req.user,
        mc=turn.mc,
        choice_key=req.choice_key,
        reasoning=req.reasoning,
        source_question=turn.question,
    )
    turn.mc.captured = True
    core.rewrite_session(req.user, turns)
    return {"ok": True, "turn": _turn_payload(turn)}


# ---------------------------------------------------------------------------
# Cases
# ---------------------------------------------------------------------------


@app.get("/api/cases")
def cases(user: str = core.DEFAULT_USER) -> dict:
    out = []
    for case in core.find_case_pages():
        questions = []
        for q in case["questions"]:
            questions.append({
                **q,
                "captured": core.question_already_captured(user, case["stem"], q["label"]),
            })
        out.append({
            "stem": case["stem"],
            "title": case["title"],
            "skeleton": case["skeleton"],
            "questions": questions,
            "captured": core.case_already_captured(user, case["stem"]),
        })
    return {"cases": out}


@app.post("/api/cases/answer")
def case_answer(req: CaseAnswerRequest) -> dict:
    case = next((c for c in core.find_case_pages() if c["stem"] == req.case_stem), None)
    if case is None:
        raise HTTPException(404, "Case not found.")
    question = next(
        (q for q in case["questions"] if q["label"] == req.question_label), None
    )
    if question is None:
        raise HTTPException(404, "Question not found in case.")
    if not req.selected_keys and not req.comment.strip():
        raise HTTPException(400, "Pick at least one option or leave a comment.")

    core.append_case_question_answer(
        user=req.user,
        case=case,
        question=question,
        selected_keys=req.selected_keys,
        comment=req.comment,
    )
    return {"ok": True}


# ---------------------------------------------------------------------------
# Review
# ---------------------------------------------------------------------------


@app.get("/api/review/stubs")
def review_stubs() -> dict:
    return {"items": [_review_item(p, "stub") for p in core.list_auto_generated_pages()]}


@app.get("/api/review/searches")
def review_searches() -> dict:
    return {"items": [_review_item(p, "search") for p in core.list_recent_searches()]}


@app.get("/api/review/notes")
def review_notes() -> dict:
    return {"items": [_review_item(p, "note") for p in core.list_note_pages()]}


@app.get("/api/review/index-gaps")
def review_index_gaps() -> dict:
    return {"gaps": [p.stem for p in core.index_gaps()]}


@app.post("/api/review/reconcile")
def reconcile(req: StubActionRequest) -> dict:
    added = core.reconcile_index(req.user)
    return {"ok": True, "added": added}


@app.post("/api/review/verify")
def verify_note(req: StubActionRequest) -> dict:
    path = core._safe_resolve(req.id)
    if path is None or not path.exists():
        raise HTTPException(404, "Note not found.")
    if not core.mark_note_verified(path, req.user):
        raise HTTPException(500, "Verify failed.")
    return {"ok": True}


@app.get("/api/page")
def get_page(id: str) -> dict:
    path = core._safe_resolve(id)
    if path is None or not path.exists():
        raise HTTPException(404, "Page not found.")
    content = path.read_text(encoding="utf-8")
    fm, body = core.parse_frontmatter(content)
    title = fm.get("title", path.stem).strip().strip('"').strip("'")
    return {
        "id": _rel(path),
        "title": title,
        "content": content,
        "body": body,
        "frontmatter": fm,
        "mtime": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
    }


@app.post("/api/page")
def save_page(req: PageSaveRequest) -> dict:
    path = core._safe_resolve(req.id)
    if path is None or not path.exists():
        raise HTTPException(404, "Page not found.")
    if not core.write_page_content(path, req.content):
        raise HTTPException(500, "Save failed.")
    return {"ok": True}


class PrincipleForkRequest(BaseModel):
    stem: str
    user: str = core.DEFAULT_USER


class PrincipleSaveRequest(BaseModel):
    stem: str
    user: str = core.DEFAULT_USER
    content: str


@app.get("/api/principles")
def principles(user: str = core.DEFAULT_USER) -> dict:
    """All shared reasoning lenses + whether this provider has forked each one."""
    return {"items": core.list_principle_status(user)}


@app.get("/api/principle")
def get_principle(stem: str, user: str = core.DEFAULT_USER) -> dict:
    """Resolve a lens for this provider: their fork if present, else the shared
    skeleton. `forked` tells the UI whether edits will fork-on-save."""
    path = core.resolve_principle_path(stem, user)
    if path is None:
        raise HTTPException(404, f"No principle '{stem}'.")
    content = path.read_text(encoding="utf-8")
    fm, _ = core.parse_frontmatter(content)
    return {
        "stem": stem,
        "title": (fm.get("title", stem) or stem).strip().strip('"').strip("'"),
        "principle_kind": (fm.get("principle_kind", "") or "").strip().strip('"'),
        "content": content,
        "forked": (core.user_principles_dir(user) / f"{stem}.md").exists(),
        "id": _rel(path),
    }


@app.post("/api/principle/fork")
def fork_principle(req: PrincipleForkRequest) -> dict:
    """Create the provider's personal fork of a shared lens (idempotent)."""
    try:
        path = core.fork_principle(req.stem, req.user)
    except FileNotFoundError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True, "id": _rel(path)}


@app.post("/api/principle")
def save_principle(req: PrincipleSaveRequest) -> dict:
    """Save edits to a provider's lens. Fork-on-save: writes to the user's avatar
    override, never to the shared skeleton — a provider's flavor stays personal."""
    dest = core.user_principles_dir(req.user) / f"{req.stem}.md"
    if not dest.exists():  # first edit forks from the shared skeleton
        try:
            core.fork_principle(req.stem, req.user)
        except FileNotFoundError as exc:
            raise HTTPException(404, str(exc))
    if not core.write_page_content(dest, req.content):
        raise HTTPException(500, "Save failed.")
    return {"ok": True, "id": _rel(dest)}


@app.post("/api/review/promote")
def promote(req: StubActionRequest) -> dict:
    path = core._safe_resolve(req.id)
    if path is None or not path.exists():
        raise HTTPException(404, "Stub not found.")
    if not core.promote_stub(path, req.user):
        raise HTTPException(500, "Promote failed (target may already exist).")
    return {"ok": True}


@app.post("/api/review/reject")
def reject(req: StubActionRequest) -> dict:
    path = core._safe_resolve(req.id)
    if path is None or not path.exists():
        raise HTTPException(404, "Stub not found.")
    if not core.reject_stub(path, req.user, req.reason):
        raise HTTPException(500, "Reject failed.")
    return {"ok": True}


@app.post("/api/review/delete-search")
def delete_search(req: StubActionRequest) -> dict:
    path = core._safe_resolve(req.id)
    if path is None or not path.exists():
        raise HTTPException(404, "Search file not found.")
    if not core.delete_search_file(path, req.user, req.reason):
        raise HTTPException(500, "Delete failed.")
    return {"ok": True}


@app.post("/api/review/delete-note")
def delete_note(req: StubActionRequest) -> dict:
    path = core._safe_resolve(req.id)
    if path is None or not path.exists():
        raise HTTPException(404, "Note not found.")
    if not core.delete_note(path, req.user, req.reason):
        raise HTTPException(500, "Delete failed.")
    return {"ok": True}
