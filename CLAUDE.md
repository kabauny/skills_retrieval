# Oncology Care Wiki

This is an LLM-maintained oncology knowledge base. Read `SCHEMA.md` for full instructions on how to operate the wiki — it defines the directory structure, page types, conventions, and workflows.

Always read `SCHEMA.md` before performing any wiki operation (ingest, search, query, lint).

## Search tool

`search.py` calls the Gemini API with Google Search grounding to retrieve web information and save it as markdown in `raw/searches/`. Usage:

```bash
python search.py "your query here"
python search.py "your query here" --prompt "focus on phase 3 trials"
```

Requires `GOOGLE_API_KEY` in `.env` or environment. Install deps: `pip install -r requirements.txt`.

## Graph tools

The `knowledge-graph` MCP server provides graph-based retrieval over the wiki's wikilink structure. Tools like `kg_search`, `kg_node`, `kg_neighbors`, `kg_paths`, and `kg_communities` are available in every Claude Code session. Run `kg_index` after every ingest to keep the graph current. See the "Graph tools" section in `SCHEMA.md` for full documentation.
