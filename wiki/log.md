---
title: Wiki Log
---

# Log

Chronological record of wiki operations. Append-only.

Format: `## [YYYY-MM-DD] operation | Title`

---

## [2026-04-12] init | Wiki created

Initialized the oncology care wiki with directory structure, schema, index, and log.

## [2026-04-24] schema | Avatar layer + supersede + query log

- Added User identity section (default user `jim.chen`, switchable per session)
- Added Avatar page type (`wiki/avatar/{user}/`) with provenance carve-out
- Added Supersede operation (vs. peer-level contradiction flagging)
- Added structured Query log entry format (makes wiki-first / Gemini-justified auditable)
- Patched `search.py` with token tracking → frontmatter + `raw/searches/_token_log.jsonl`

## [2026-04-24] init | Avatar scaffolded for jim.chen

Created `wiki/avatar/jim.chen/{questions.md, decisions.md, preferences/}`.

## [2026-04-24] session | jim.chen active

Session active user: `jim.chen` (default per CLAUDE.md).
