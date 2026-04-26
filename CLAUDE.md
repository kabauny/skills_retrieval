# Oncology Care Wiki

This is an LLM-maintained oncology knowledge base. Read `SCHEMA.md` for full instructions on how to operate the wiki — it defines the directory structure, page types, conventions, and workflows.

Always read `SCHEMA.md` before performing any wiki operation (ingest, search, query, supersede, lint).

## Active user

**Default user: `jim.chen`.** All avatar operations (decisions, preferences, question-capture) target `wiki/avatar/jim.chen/` unless the session explicitly switches users with *"switch to user X"*. See SCHEMA.md § User identity for the full convention.

## Search tool

`search.py` calls the Gemini API with Google Search grounding to retrieve web information and save it as markdown in `raw/searches/`. Usage:

```bash
python search.py "your query here"
python search.py "your query here" --prompt "focus on phase 3 trials"
```

Requires `GOOGLE_API_KEY` in `.env` or environment. Install deps: `pip install -r requirements.txt`.

## Graph tools

The `knowledge-graph` MCP server provides graph-based retrieval over the wiki's wikilink structure. Tools like `kg_search`, `kg_node`, `kg_neighbors`, `kg_paths`, and `kg_communities` are available in every Claude Code session. Run `kg_index` after every ingest to keep the graph current. See the "Graph tools" section in `SCHEMA.md` for full documentation.

## Streamlit UI (`app.py`)

A Streamlit app for end-user query + avatar capture.

**Two-model split:**
- **`gemini-3.1-pro-preview`** (Pro) — wiki + internet synthesis, MC preference probe (heavy reasoning + avatar quality)
- **`gemini-2.5-flash`** (Flash) — page routing, entity extraction (pattern-matching + structured output)

**Render-first deferred ingest:** answer + MC probe render immediately after Phase 1 (route + synth + MC). Phase 2 (save grounded response to `raw/searches/` + auto-ingest novel entities) runs after rendering, with a status spinner. The user reads the answer while save + ingest happen.

Capabilities:

1. **Ask questions of the wiki** — index-based routing + per-page synthesis
2. **Internet fallback** (Gemini grounded search) when the wiki is insufficient
3. **Audit-back-to-wiki** — every query writes to `wiki/log.md` and `wiki/avatar/{user}/questions.md`
4. **MC preference probes** — agent surfaces genuine equipoise as a multiple-choice question
5. **Avatar capture** — picked option + reasoning written to `wiki/avatar/{user}/decisions.md`

Persistent extensions:

- **Session persistence** — every turn (Q + A + sources + MC + token counts) saved as JSONL to `raw/sessions/{user}-{date}.jsonl`. Reloaded on app start so chat history survives browser reload.
- **Grounded searches save** — when the internet fallback fires, the grounded response is saved to `raw/searches/{slug}.md` using the same format as agent-driven `python search.py` (frontmatter, resolved URLs, token tracking, `_token_log.jsonl`).
- **Auto-ingest** (toggle in sidebar, default ON) — for each grounded search, extract novel entities and write `auto_generated: true` stub pages to `wiki/entities/` or `wiki/concepts/`. Stubs are added to a "Auto-generated stubs (UI-driven)" section in `wiki/index.md` and logged in `wiki/log.md` as `## [date] auto-ingest |`. Stubs require agent review before clinical use.

Run:

```bash
streamlit run app.py
```

The app runs locally (default `http://localhost:8501`). Defaults to user `jim.chen`; switch via the sidebar (history reloads from that user's session file).
