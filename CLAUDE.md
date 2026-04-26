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

A minimal Streamlit app for end-user query + avatar capture. Five capabilities:

1. Ask questions of the wiki
2. Internet fallback (Gemini grounded search) when wiki is insufficient
3. Every interaction is audited back to `wiki/log.md` and `wiki/avatar/{user}/questions.md`
4. Agent generates a multiple-choice preference probe for any answer that surfaces genuine clinical equipoise
5. User picks an option → preference captured to `wiki/avatar/{user}/decisions.md`

Run:

```bash
streamlit run app.py
```

The app runs locally (default `http://localhost:8501`) and writes to the same wiki layer the agent uses. Defaults to user `jim.chen`; switch via the sidebar.
