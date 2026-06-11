# Oncology Care Wiki

An LLM-maintained oncology knowledge base: a markdown wiki of interlinked drug /
cancer / trial / biomarker pages, **reasoning lenses** and per-disease frameworks,
**institutional & payer preference programs** (formulary + pathways), and a
**graph** over the wikilinks — served through a FastAPI backend and a Next.js
web app.

> Deeper docs: **`SCHEMA.md`** (wiki structure, page types, conventions) and
> **`CLAUDE.md`** (how the LLM operates the wiki, model split, app capabilities).

---

## Prerequisites

- **Python 3.11+**
- **Node 18+** (for the web app)
- A **Google Gemini API key** (the app uses `gemini-3.1-pro-preview`,
  `gemini-2.5-flash`, and `gemini-embedding-001`)

---

## 1. Backend setup (Python)

From the repo root:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Create a **`.env`** in the repo root with your key:

```bash
GOOGLE_API_KEY=your-key-here
```

## 2. Frontend setup (web app)

```bash
cd web
npm install
cd ..
```

---

## Running the app

### Easiest — both servers at once

```bash
./dev.sh
```

This starts the **FastAPI backend on `:8000`** and the **Next.js frontend on
`:3100`** (and runs `npm install` for the web app if needed). Then open:

> **http://localhost:3100**

Keep the terminal open — closing it (or this process being killed) stops the
servers and the site becomes unreachable.

### Or run them separately (two terminals)

```bash
# terminal 1 — backend
.venv/bin/uvicorn api:app --port 8000 --reload

# terminal 2 — frontend
cd web && npm run dev
```

The frontend calls the backend directly at `http://localhost:8000`. If your
backend runs elsewhere, set `NEXT_PUBLIC_API_BASE` before `npm run dev`.

---

## The web app at a glance

| Tab | What it does |
|-----|--------------|
| 💬 **Chat** | Ask the wiki. Wiki-first retrieval (embedding + graph), internet fallback when needed, preference-weighted by your institution + payer programs. |
| 📚 **Cases** | Capture your clinical judgment on decision questions (avatar). |
| 📋 **Review** | Triage auto-ingested notes (verify/edit/delete) with duplicate/overlap flags; reconcile the index. |
| 🌱 **Grow** | An agent proposes gap-questions (judgment / breadth / structure) to grow the wiki. |
| 🧭 **Lenses** | Reasoning frameworks ("how to weigh efficacy/toxicity"); fork any to your own style. |
| 🏥 **Institution** | Formulary + preferred pathways for your institution (primary) and payer programs like Evolent (secondary). |
| 🔎 **Search** | Instant lexical lookup over all pages (no AI). |

**Auto-ingest** (sidebar, **on by default**): internet-fallback answers are saved
as searchable, indexed, graph-linked notes, so re-asking is answered locally.

---

## Optional extras

**Knowledge-graph MCP server** (for Claude Code) — already registered in
`.mcp.json`; its deps install with `requirements.txt`. Tools (`kg_search`,
`kg_neighbors`, `kg_index`, …) are available in any Claude Code session in this
repo. Rebuild the graph after ingests:

```bash
# inside Claude Code: call the kg_index tool
.venv/bin/python kg_server.py --stats     # standalone graph stats
```

**CLI grounded search** — save a Gemini grounded search to `raw/searches/`:

```bash
.venv/bin/python search.py "your clinical question"
```

**Legacy Streamlit UI** (superseded by the web app):

```bash
.venv/bin/streamlit run app.py
```

---

## Where things live

```
wiki/            # the knowledge base (you/the LLM own this)
  entities/      #   drugs, cancers, trials, biomarkers
  principles/    #   reasoning lenses + per-disease frameworks
  concepts/      #   mechanisms, paradigms, system docs
  notes/         #   auto-ingested grounded answers (searchable)
  institution/   #   preference programs (formulary + pathways) — your config
  avatar/{user}/ #   per-provider questions, decisions, preferences, lens forks
  index.md       #   router catalog · log.md  operation log
raw/             # immutable sources: papers/, guidelines/, searches/, sessions/
api.py           # FastAPI backend          web/        # Next.js frontend
core.py          # all retrieval/synthesis/graph logic
```

---

## Troubleshooting

- **"This site can't be reached" at :3100** — the dev servers aren't running.
  Re-run `./dev.sh` and leave the terminal open.
- **`GOOGLE_API_KEY not configured`** — add it to `.env` (repo root) and restart
  the backend.
- **`unknown error … low max file descriptors` (macOS)** — raise the limit in the
  shell before launching: `ulimit -n 65536`.
- **Backend port in use** — change `--port`, and set `NEXT_PUBLIC_API_BASE` to
  match for the frontend.
