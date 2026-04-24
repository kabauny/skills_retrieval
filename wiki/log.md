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

## [2026-04-24] ingest | MRD+ HER2+ breast cancer, residual disease post-TCHP (Q3 source)

- **Source:** [[mrd-her2-breast-cancer-residual-disease-2026]] (Gemini grounded search, 5,416 tokens, 28 web sources)
- **Pages created:**
  - sources: [[mrd-her2-breast-cancer-residual-disease-2026]]
  - entities (drugs): [[trastuzumab-emtansine]], [[trastuzumab-deruxtecan]], [[tucatinib]]
  - entities (trials): [[katherine-trial]], [[destiny-breast05]], [[her2climb-05]], [[zest-trial]]
  - entities (cancer/biomarker): [[her2-positive-breast-cancer]], [[circulating-tumor-dna]]
  - concepts: [[adjuvant-her2-positive-breast-cancer]], [[mrd-guided-therapy-escalation]], [[residual-disease-vs-mrd-positivity]]
- **Pages updated:** [[overview]], [[index]]
- **Total new pages:** 13 (1 source + 9 entities + 3 concepts)
- **Wiki content size after ingest:** ~32 KB (all pages 1.7–5.4 KB; well within grep-retrieval territory)
- **Disambiguation introduced:** [[residual-disease-vs-mrd-positivity]] addresses a conflation in the search response between residual disease (histopath, KATHERINE eligibility) and MRD-positivity (ctDNA, additional risk stratifier). They are nested strata, not synonyms.
- **Provenance:** every claim wikilinked to the source summary per the schema's provenance rule.
- **kg_index:** not yet run (no MCP server configured in this session — to be run when graph tools are available).
