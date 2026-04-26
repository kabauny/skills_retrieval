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

## [2026-04-24] query | ILD trade-off T-DM1 vs T-DXd adjuvantly

- **User:** jim.chen
- **Question:** "What's the ILD trade-off in switching from T-DM1 to T-DXd adjuvantly?"
- **Trigger:** wiki-first retrieval test following Q3 ingest — probes whether the wiki can answer a Q3-adjacent question without Gemini.
- **Wiki pages consulted:** [[trastuzumab-deruxtecan]], [[trastuzumab-emtansine]], [[destiny-breast05]], [[adjuvant-her2-positive-breast-cancer]]
- **KG tools used:** none (no `knowledge-graph` MCP configured this session)
- **Gemini calls:** 0 — justified (wiki had specific numbers 9.6% vs 1.6% + clinical decision framing + provenance chain; no genuine gap)
- **Answer origin:** wiki
- **Tokens (Gemini):** 0
- **Filed back:** none (synthesis already captured in [[adjuvant-her2-positive-breast-cancer]] decision skeleton; not a new reusable page)
- **Decision captured:** none (retrieval test, no clinical judgment made by user)

## [2026-04-25] ingest | Premenopausal intermediate-RS HR+/HER2− adjuvant decision (Q4 source)

- **Source:** [[premenopausal-intermediate-oncotype-2026]] (Gemini grounded search, 5,262 tokens, 32 web sources; URL resolution applied inline)
- **Pages created (12):**
  - sources: [[premenopausal-intermediate-oncotype-2026]]
  - entities (trials): [[tailorx-trial]], [[rxponder-trial]], [[ofset-trial]]
  - entities (drugs/treatments): [[ovarian-function-suppression]], [[aromatase-inhibitor]], [[tamoxifen]]
  - entities (cancer): [[hr-positive-her2-negative-breast-cancer]]
  - entities (biomarkers): [[oncotype-dx-recurrence-score]], [[anti-mullerian-hormone]]
  - concepts: [[chemotherapy-induced-ovarian-suppression]], [[intermediate-rs-premenopausal-hr-positive-management]], [[node-negative-vs-node-positive-genomic-trial-scoping]]
- **Pages updated (4):**
  - [[circulating-tumor-dna]] — appended HR+/HER2− section (DARE/TRACKER/SURVIVE/OFSET trials, parallel HER2+ structure). Cross-ingest accretion working as designed.
  - [[overview]] — added Q4 cluster + cross-cluster synthesis
  - [[index]] — added new pages, expanded biomarkers and trials sections
  - [[log]] — this entry
- **Disambiguation introduced:** [[node-negative-vs-node-positive-genomic-trial-scoping]] — TAILORx (node-negative, governs Q4) vs RxPONDER (node-positive, spawns CIOS debate but does not directly govern Q4). Parallel pattern to [[residual-disease-vs-mrd-positivity]] from Q3.
- **Provenance:** every claim wikilinked to [[premenopausal-intermediate-oncotype-2026]]. The [[circulating-tumor-dna]] update cites both Q3 and Q4 sources.
- **No supersession this ingest** — no claims from Q3 ingest were overwritten. Q4 added an entirely new disease-cluster scope plus cross-reference to ctDNA. The supersede operation will be exercised in a future ingest where claims from earlier sources are updated by newer ones.
- **kg_index:** not yet run (no MCP server configured this session).

## [2026-04-26] query | ctDNA-MRD across breast cancer subtypes (cross-cluster)

- **User:** jim.chen
- **Question:** "How does ctDNA-MRD status currently inform adjuvant decisions across breast cancer subtypes?"
- **Trigger:** post-Q4 cross-cluster wiki-first retrieval test — probes whether the wiki, now spanning two disease clusters, can answer a unified-view question without Gemini.
- **Wiki pages consulted:** [[circulating-tumor-dna]], [[mrd-guided-therapy-escalation]], [[zest-trial]], [[ofset-trial]], [[residual-disease-vs-mrd-positivity]]
- **KG tools used:** none (no `knowledge-graph` MCP configured this session)
- **Gemini calls:** 0 — justified (wiki had unified view across both subtypes after the Q4 update to [[circulating-tumor-dna]]; no genuine gap)
- **Answer origin:** wiki (cross-cluster)
- **Tokens (Gemini):** 0
- **Filed back:** none (the synthesis is already captured in [[mrd-guided-therapy-escalation]] and the updated [[circulating-tumor-dna]] page)
- **Decision captured:** none (retrieval test, no clinical judgment by user)
- **What this validates:** cross-ingest accretion produced a coherent unified answer. The Q4 update to [[circulating-tumor-dna]] (HR+/HER2− section appended without rewriting HER2+ content) created exactly the cross-cluster reference the architecture is designed to support.

## [2026-04-26] ingest | TNBC pCR after KEYNOTE-522 with severe irAE (Q5 source)

- **Source:** [[tnbc-keynote-522-irae-rechallenge-2026]] (Gemini grounded search, 6,319 tokens, 29 web sources; URL resolution applied inline)
- **Pages created (9):**
  - sources: [[tnbc-keynote-522-irae-rechallenge-2026]]
  - entities (cancer): [[triple-negative-breast-cancer]]
  - entities (drugs): [[pembrolizumab]], [[infliximab]]
  - entities (trials): [[keynote-522]]
  - entities (biomarkers): [[tumor-mutational-burden]]
  - concepts: [[immune-related-adverse-events]], [[pembrolizumab-rechallenge-after-severe-irae]], [[adjuvant-pembrolizumab-after-pcr-tnbc]]
- **Pages updated (4):**
  - [[circulating-tumor-dna]] — appended TNBC section (NCT07327021) with cross-subtype summary table. ctDNA-MRD page now spans **all three** breast cancer subtypes (HER2+, HR+/HER2−, TNBC) with consistent prognostic-not-predictive framing.
  - [[overview]] — added Q5 cluster + cross-cluster synthesis updated to three subtypes
  - [[index]] — added new pages
  - [[log]] — this entry
- **Disambiguation introduced:** [[adjuvant-pembrolizumab-after-pcr-tnbc]] makes explicit a distinction the search lightly conflated — **reactive de-escalation after irAE** (Q5 case) vs. **proactive biomarker-guided de-escalation** in untreated patients. The trial isolates neither, but the data each speaks to is different.
- **No supersession this ingest.** No prior wiki claims contradicted by Q5. TNBC is a new subtype; existing pages (HER2+, HR+/HER2−) made no TNBC-specific claims. Supersede operation remains untested in practice — will be exercised when a future ingest updates earlier claims (e.g., when the DESTINY-Breast05 primary publication drops and replaces press-release-citation chains in [[trastuzumab-deruxtecan]]).
- **Provenance:** every claim wikilinked to [[tnbc-keynote-522-irae-rechallenge-2026]]. The [[circulating-tumor-dna]] update cites all three Q3/Q4/Q5 sources.
- **kg_index:** not yet run (no MCP server configured this session).
