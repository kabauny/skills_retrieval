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

## [2026-04-26] ingest | DESTINY-Breast05 + KATHERINE April 2026 update (supersession source)

- **Source:** [[destiny-breast05-april-2026-update]] (Gemini grounded search, 4,546 tokens, 18 web sources). Targeted search to test the supersede operation per SCHEMA.md.
- **Pages created (1):** sources/destiny-breast05-april-2026-update
- **Confirmed unchanged** (no supersession): T-DXd FDA status (still investigational, sBLA priority review March 9 2026, PDUFA July 7 2026); NCCN/ASCO/ESMO guideline incorporation (still anticipated, not formally updated); IDFS HR 0.47 / 53% reduction / 3-yr 92.4% vs 83.7%.
- **Triggered four supersession entries** below.

## [2026-04-26] supersede | trastuzumab-deruxtecan — brain metastasis specificity

- **Page:** [[trastuzumab-deruxtecan]]
- **Old claim:** "Brain metastasis activity: clinically meaningful reduction observed in DESTINY-Breast05 — relevant for HER2+ disease with high CNS recurrence risk"
- **Old source:** [[mrd-her2-breast-cancer-residual-disease-2026]]
- **New claim:** "Brain metastasis-free interval HR 0.64 (95% CI 0.35–1.17), 36% reduction vs T-DM1. CI crosses 1.0 — directional finding consistent with T-DXd CNS penetration but not statistically definitive at conventional threshold."
- **New source:** [[destiny-breast05-april-2026-update]]
- **Reason:** newer reporting from the same trial (DESTINY-Breast05) provides specific quantification (HR + CI) that supersedes the qualitative "clinically meaningful" phrasing from the original press-release-derived ingest.

## [2026-04-26] supersede | trastuzumab-deruxtecan — ILD specifics

- **Page:** [[trastuzumab-deruxtecan]]
- **Old claim:** "ILD/pneumonitis 9.6% in DESTINY-Breast05 vs 1.6% with T-DM1, including some Grade 5 events"
- **Old source:** [[mrd-her2-breast-cancer-residual-disease-2026]]
- **New claim:** "ILD/pneumonitis 9.6% (T-DXd) vs 1.6% (T-DM1). Two Grade 5 events on T-DXd; zero on T-DM1. Trial protocol incorporated proactive serial low-dose chest CT monitoring for early ILD detection. No incremental ILD risk observed with concurrent radiotherapy."
- **New source:** [[destiny-breast05-april-2026-update]]
- **Reason:** newer source quantifies the Grade 5 event asymmetry (2 vs 0) that "some Grade 5 events" obscured, and adds protocol-level monitoring guidance and a relevant safety null finding (no incremental risk with concurrent RT). All from the same trial.

## [2026-04-26] supersede | destiny-breast05 — CNS, ILD, primary publication

- **Page:** [[destiny-breast05]]
- **Old claim:** "CNS endpoint: clinically meaningful reduction in brain metastasis risk with T-DXd"; "Safety: ILD/pneumonitis 9.6% vs 1.6%, including some Grade 5 events"; (no primary-publication line)
- **Old source:** [[mrd-her2-breast-cancer-residual-disease-2026]]
- **New claim:** "CNS endpoint: brain metastasis-free interval HR 0.64 (95% CI 0.35–1.17), 36% reduction"; "Safety: ILD 9.6% (2 Grade 5 events) vs 1.6% (0 Grade 5); proactive serial low-dose chest CT in protocol; no incremental ILD risk with concurrent RT"; "Primary publication: NEJM following ESMO 2025 oral presentation"
- **New source:** [[destiny-breast05-april-2026-update]]
- **Reason:** quantified CNS and ILD specifics replace qualitative phrasing. Primary NEJM publication is a higher-authority source than the press release / ESMO oral chain the original wiki claims relied on.

## [2026-04-26] supersede | katherine-trial — long-term follow-up quantification

- **Page:** [[katherine-trial]]
- **Old claim:** "Long-term (8.4-year) follow-up: sustained IDFS benefit and improved overall survival with T-DM1"
- **Old source:** [[mrd-her2-breast-cancer-residual-disease-2026]]
- **New claim:** "Long-term follow-up (8.4-year median, published January 2025): sustained IDFS benefit and improved overall survival with T-DM1. 7-year IDFS: 80.8% (T-DM1) vs 67.1% (trastuzumab); 7-year OS: 89.1% vs 84.4%."
- **New source:** [[destiny-breast05-april-2026-update]]
- **Reason:** newer source quantifies the long-term follow-up update with specific 7-year IDFS and OS rates from the published January 2025 ASCO Post / Applied Clinical Trials report. Original wiki claim was qualitative-only.

## [2026-04-26] meta | Supersede operation tested end-to-end

- **What was tested:** can the agent (a) recognize when newer same-or-higher-authority data updates an existing wiki claim, (b) rewrite the affected sections with the new claim and citation, (c) preserve old-source citations for unaffected claims on the same page, and (d) produce structured per-supersession log entries.
- **Result:** 4 supersession entries from a single targeted search source. Affected 3 wiki pages ([[trastuzumab-deruxtecan]], [[destiny-breast05]], [[katherine-trial]]). Old sources retained on those pages for unaffected claims; new source added with role-distinguishing comments in the Sources sections.
- **What was NOT superseded** (correct restraint): FDA status, guideline incorporation, IDFS primary endpoint — all unchanged. The agent correctly distinguished "still pending / unchanged" from "newly quantified" claims.
- **Audit trail:** structured entries above, plus the git diff captures the byte-level rewrite for each affected file. Both layers of audit (wiki content rewrite + log-level structured diff + git history) work as designed.

## [2026-04-26] query | Q5 TNBC pCR adjuvant pembrolizumab decision (decision capture)

- **User:** jim.chen
- **Question:** "TNBC patient achieves pCR after neoadjuvant KEYNOTE-522 but had Grade 3 immune-mediated colitis requiring steroids + infliximab. Re-challenge with adjuvant pembrolizumab to maximize curative intent, or omit knowing pCR portends excellent prognosis?"
- **Trigger:** First decision-capture exercise per the planned avatar workflow.
- **Wiki pages consulted:** [[adjuvant-pembrolizumab-after-pcr-tnbc]], [[keynote-522]], [[pembrolizumab-rechallenge-after-severe-irae]], [[immune-related-adverse-events]], [[pembrolizumab]], [[infliximab]], [[triple-negative-breast-cancer]]
- **KG tools used:** none (no `knowledge-graph` MCP configured this session)
- **Gemini calls:** 0 — justified (wiki had complete option set + evidence + decision skeleton; decision-capture mode, not retrieval)
- **Answer origin:** wiki (decision-capture mode)
- **Tokens (Gemini):** 0
- **Filed back:** [[avatar/jim.chen/decisions#2026-04-26-q5-tnbc-pcr-grade-3-colitis-adjuvant-pembrolizumab-omission]]
- **Decision captured:** Option A (omit adjuvant pembrolizumab); confidence moderate
- **Wiki tension noted:** decision deviates from formal NCCN/ASCO/ESMO full-regimen recommendation; deviation falls in a guideline-gap area (irAE-driven discontinuation not specifically addressed by guidelines)
- **First decision capture in the wiki.** `wiki/avatar/jim.chen/decisions.md` populates with one entry. Future cross-cluster queries can begin to detect patterns in jim.chen's decision style (e.g., toxicity-recurrence-risk-versus-marginal-benefit weighting); preference pages will crystallize once 2–3+ decisions exhibit a coherent pattern.

## [2026-04-26] query | How do you select Tdxd based regimen (Destinybreast-11) vs TCHP for ne...

- **User:** jim.chen
- **Question:** "How do you select Tdxd based regimen (Destinybreast-11) vs TCHP for neoadjuvant her2+ breast cancer? "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[her2-positive-breast-cancer]], [[trastuzumab-deruxtecan]], [[destiny-breast05]]
- **Gemini calls:** 4
- **Answer origin:** mixed
- **Tokens (Gemini):** 13818

## [2026-04-26] query | NO destiny breast breast 11 is a new publish data. Can you take a look...

- **User:** jim.chen
- **Question:** "NO destiny breast breast 11 is a new publish data. Can you take a look? "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[destiny-breast05-april-2026-update]], [[destiny-breast05]], [[trastuzumab-deruxtecan]], [[katherine-trial]], [[trastuzumab-emtansine]], [[her2-positive-breast-cancer]], [[adjuvant-her2-positive-breast-cancer]]
- **Gemini calls:** 4
- **Answer origin:** mixed
- **Tokens (Gemini):** 22399

## [2026-04-26] query | Tell me about Destiny Breast 11 and how it changes the management of n...

- **User:** jim.chen
- **Question:** "Tell me about Destiny Breast 11 and how it changes the management of neoadjuvant breast cancer? "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[destiny-breast05-april-2026-update]], [[destiny-breast05]], [[katherine-trial]], [[trastuzumab-deruxtecan]], [[trastuzumab-emtansine]], [[adjuvant-her2-positive-breast-cancer]], [[her2-positive-breast-cancer]], [[residual-disease-vs-mrd-positivity]]
- **Gemini calls:** 4
- **Answer origin:** mixed
- **Tokens (Gemini):** 39012

## [2026-04-26] auto-ingest | UI grounded search → stub pages

- **User:** jim.chen
- **Triggering query:** "MRD testing for colon  cancer. If MRD is positive, but no evidence of disease, what's the current ev..."
- **Source saved:** [[mrd-testing-for-colon-cancer-if-mrd-is-positive-but-no-evidence-of-disease-whats]]
- **Stub pages created (5):**
  - [[cobra-trial]] (entities)
  - [[altair-trial]] (entities)
  - [[dynamic-trial]] (entities)
  - [[trifluridine-tipiracil]] (entities)
  - [[colon-cancer]] (entities)
- **Note:** AUTO-GENERATED stubs from a UI grounded search. Marked `auto_generated: true` in frontmatter. Agent review and promotion to full entity/concept pages is recommended before clinical use.

## [2026-04-26] query | MRD testing for colon  cancer. If MRD is positive, but no evidence of ...

- **User:** jim.chen
- **Question:** "MRD testing for colon  cancer. If MRD is positive, but no evidence of disease, what's the current evidence for starting chemotherapy vs just observe until measurable disease can be detected "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 5
- **Answer origin:** internet
- **Tokens (Gemini):** 12043
- **Search saved:** [[mrd-testing-for-colon-cancer-if-mrd-is-positive-but-no-evidence-of-disease-whats]]
- **Stub pages auto-created:** [[cobra-trial]], [[altair-trial]], [[dynamic-trial]], [[trifluridine-tipiracil]], [[colon-cancer]]

## [2026-04-26] query | Tell me about RxPONDER trial and results  

- **User:** jim.chen
- **Question:** "Tell me about RxPONDER trial and results  "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[rxponder-trial]], [[premenopausal-intermediate-oncotype-2026]], [[chemotherapy-induced-ovarian-suppression]], [[intermediate-rs-premenopausal-hr-positive-management]], [[node-negative-vs-node-positive-genomic-trial-scoping]]
- **Gemini calls:** 3
- **Answer origin:** wiki
- **Tokens (Gemini):** 13133

## [2026-04-26] auto-ingest | UI grounded search → stub pages

- **User:** jim.chen
- **Triggering query:** "Tell me about Destiny breast 011 "
- **Source saved:** [[tell-me-about-destiny-breast-011]]
- **Stub pages created (5):**
  - [[destiny-breast11]] (entities)
  - [[neoadjuvant-treatment]] (concepts)
  - [[pathologic-complete-response]] (concepts)
  - [[trastuzumab]] (entities)
  - [[pertuzumab]] (entities)
- **Note:** AUTO-GENERATED stubs from a UI grounded search. Marked `auto_generated: true` in frontmatter. Agent review and promotion to full entity/concept pages is recommended before clinical use.

## [2026-04-26] query | Tell me about Destiny breast 011 

- **User:** jim.chen
- **Question:** "Tell me about Destiny breast 011 "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[destiny-breast05]], [[destiny-breast05-april-2026-update]], [[trastuzumab-deruxtecan]], [[trastuzumab-emtansine]], [[katherine-trial]], [[her2-positive-breast-cancer]], [[adjuvant-her2-positive-breast-cancer]], [[residual-disease-vs-mrd-positivity]]
- **Gemini calls:** 5
- **Answer origin:** mixed
- **Tokens (Gemini):** 33037
- **Search saved:** [[tell-me-about-destiny-breast-011]]
- **Stub pages auto-created:** [[destiny-breast11]], [[neoadjuvant-treatment]], [[pathologic-complete-response]], [[trastuzumab]], [[pertuzumab]]

## [2026-04-26] auto-ingest | UI grounded search → stub pages

- **User:** jim.chen
- **Triggering query:** "What are treatment options for second line multiple myeloma treatment after progressing on dara VRD?"
- **Source saved:** [[what-are-treatment-options-for-second-line-multiple-myeloma-treatment-after-prog]]
- **Stub pages created (5):**
  - [[ciltacabtagene-autoleucel]] (entities)
  - [[majestec-3-trial]] (entities)
  - [[belantamab-mafodotin]] (entities)
  - [[dreamm-7-trial]] (entities)
  - [[b-cell-maturation-antigen]] (entities)
- **Note:** AUTO-GENERATED stubs from a UI grounded search. Marked `auto_generated: true` in frontmatter. Agent review and promotion to full entity/concept pages is recommended before clinical use.

## [2026-04-26] query | What are treatment options for second line multiple myeloma treatment ...

- **User:** jim.chen
- **Question:** "What are treatment options for second line multiple myeloma treatment after progressing on dara VRD?"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 5
- **Answer origin:** internet
- **Tokens (Gemini):** 15610
- **Search saved:** [[what-are-treatment-options-for-second-line-multiple-myeloma-treatment-after-prog]]
- **Stub pages auto-created:** [[ciltacabtagene-autoleucel]], [[majestec-3-trial]], [[belantamab-mafodotin]], [[dreamm-7-trial]], [[b-cell-maturation-antigen]]

## [2026-04-26] auto-ingest | UI grounded search → stub pages

- **User:** jim.chen
- **Triggering query:** "What are some treatment options for paraganglioma that is not resectable? "
- **Source saved:** [[what-are-some-treatment-options-for-paraganglioma-that-is-not-resectable]]
- **Stub pages created (5):**
  - [[paraganglioma]] (entities)
  - [[i-131-iobenguane]] (entities)
  - [[peptide-receptor-radionuclide-therapy]] (concepts)
  - [[belzutifan]] (entities)
  - [[cvd-regimen]] (concepts)
- **Note:** AUTO-GENERATED stubs from a UI grounded search. Marked `auto_generated: true` in frontmatter. Agent review and promotion to full entity/concept pages is recommended before clinical use.

## [2026-04-26] query | What are some treatment options for paraganglioma that is not resectab...

- **User:** jim.chen
- **Question:** "What are some treatment options for paraganglioma that is not resectable? "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 5
- **Answer origin:** internet
- **Tokens (Gemini):** 15121
- **Search saved:** [[what-are-some-treatment-options-for-paraganglioma-that-is-not-resectable]]
- **Stub pages auto-created:** [[paraganglioma]], [[i-131-iobenguane]], [[peptide-receptor-radionuclide-therapy]], [[belzutifan]], [[cvd-regimen]]

## [2026-04-26] case-q-answer | adjuvant-her2-positive-breast-cancer > after-the-july-2026-pdufa-would-you-switch-to-t-dxd-as-your-

- **User:** jim.chen
- **Concept:** [[adjuvant-her2-positive-breast-cancer]]
- **Question:** After the July 2026 PDUFA, would you switch to T-DXd as your default adjuvant for HER2+ residual disease?
- **Selections:** B
- **Comment:** TDXD have proven itself to be a superior regimen in all cases, I would offer it as front line. Although a consideration ...
- **Captured via:** Cases tab (Streamlit UI)

## [2026-04-26] query | Is there a significant difference in ILD for patient recieving TDXD vs...

- **User:** jim.chen
- **Question:** "Is there a significant difference in ILD for patient recieving TDXD vs TDM1?"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[destiny-breast05-april-2026-update]], [[destiny-breast05]], [[katherine-trial]], [[trastuzumab-deruxtecan]], [[trastuzumab-emtansine]]
- **Gemini calls:** 3
- **Answer origin:** wiki
- **Tokens (Gemini):** 12647

## [2026-05-29] promote (batch) | 20 stubs promoted from wiki/stubs/

- **User:** jim.chen
- **Action:** stripped `auto_generated`/`stub_target` markers, `auto-generated` tag, and warning callout; moved each page into the curated namespace per its `stub_target`.
- **Pages:**
  - altair-trial -> wiki/entities/altair-trial.md
  - b-cell-maturation-antigen -> wiki/entities/b-cell-maturation-antigen.md
  - belantamab-mafodotin -> wiki/entities/belantamab-mafodotin.md
  - belzutifan -> wiki/entities/belzutifan.md
  - ciltacabtagene-autoleucel -> wiki/entities/ciltacabtagene-autoleucel.md
  - cobra-trial -> wiki/entities/cobra-trial.md
  - colon-cancer -> wiki/entities/colon-cancer.md
  - cvd-regimen -> wiki/concepts/cvd-regimen.md
  - destiny-breast11 -> wiki/entities/destiny-breast11.md
  - dreamm-7-trial -> wiki/entities/dreamm-7-trial.md
  - dynamic-trial -> wiki/entities/dynamic-trial.md
  - i-131-iobenguane -> wiki/entities/i-131-iobenguane.md
  - majestec-3-trial -> wiki/entities/majestec-3-trial.md
  - neoadjuvant-treatment -> wiki/concepts/neoadjuvant-treatment.md
  - paraganglioma -> wiki/entities/paraganglioma.md
  - pathologic-complete-response -> wiki/concepts/pathologic-complete-response.md
  - peptide-receptor-radionuclide-therapy -> wiki/concepts/peptide-receptor-radionuclide-therapy.md
  - pertuzumab -> wiki/entities/pertuzumab.md
  - trastuzumab -> wiki/entities/trastuzumab.md
  - trifluridine-tipiracil -> wiki/entities/trifluridine-tipiracil.md
- **Reminder:** consider an agent ingest to expand each to full SCHEMA structure (Overview, Key facts, Related entities, Sources).

## [2026-06-05] log-reconstructed | rebuilt from session JSONL after accidental `git checkout` of log.md

- **Note:** the entries below were regenerated faithfully from `raw/sessions/jim.chen-2026-06-05.jsonl` (source of truth). Wording matches the original app output; ordering is by session index.


## [2026-06-05] query | What is the new indication for durvalumab in non muscle invasive bladd...

- **User:** jim.chen
- **Question:** "What is the new indication for durvalumab in non muscle invasive bladder cancer? "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 4
- **Answer origin:** internet
- **Tokens (Gemini):** 5170
- **Search saved:** [[what-is-the-new-indication-for-durvalumab-in-non-muscle-invasive-bladder-cancer]]

## [2026-06-05] query | Waht is the The 3-year IDFS rate was for T-DXd compared to T-DM1 for b...

- **User:** jim.chen
- **Question:** "Waht is the The 3-year IDFS rate was for T-DXd compared to T-DM1 for breast cancer in the adjuvant setting "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[destiny-breast05]], [[destiny-breast05-april-2026-update]], [[katherine-trial]], [[trastuzumab-deruxtecan]], [[trastuzumab-emtansine]], [[adjuvant-her2-positive-breast-cancer]], [[her2-positive-breast-cancer]]
- **Gemini calls:** 3
- **Answer origin:** wiki
- **Tokens (Gemini):** 13532

## [2026-06-05] query | What are some highlights from ASCO 2026 regarding pancreatic cancer? 

- **User:** jim.chen
- **Question:** "What are some highlights from ASCO 2026 regarding pancreatic cancer? "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 4
- **Answer origin:** internet
- **Tokens (Gemini):** 8432
- **Search saved:** [[what-are-some-highlights-from-asco-2026-regarding-pancreatic-cancer]]

## [2026-06-05] query | What is the mechanism for atebimetinib? 

- **User:** jim.chen
- **Question:** "What is the mechanism for atebimetinib? "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 4
- **Answer origin:** internet
- **Tokens (Gemini):** 5594
- **Search saved:** [[what-is-the-mechanism-for-atebimetinib]]

## [2026-06-05] query | What is the work up for glioblastoma? What biomakers do I need. How do...

- **User:** jim.chen
- **Question:** "What is the work up for glioblastoma? What biomakers do I need. How do I stage it, what is the initial therapy? "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 4
- **Answer origin:** internet
- **Tokens (Gemini):** 8075
- **Search saved:** [[what-is-the-work-up-for-glioblastoma-what-biomakers-do-i-need-how-do-i-stage-it-]]

## [2026-06-05] query | What is the regimen for adjuvant and maintantence TMZ?

- **User:** jim.chen
- **Question:** "What is the regimen for adjuvant and maintantence TMZ?"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 5
- **Answer origin:** internet
- **Tokens (Gemini):** 11341
- **Search saved:** [[what-is-the-regimen-for-adjuvant-and-maintantence-tmz]]
- **Stub pages auto-created:** [[stupp-protocol]], [[glioblastoma]], [[temozolomide]], [[absolute-neutrophil-count]], [[ondansetron]]

## [2026-06-05] query | What is the new indication for durvalumab in non muscle invasive bladd...

- **User:** jim.chen
- **Question:** "What is the new indication for durvalumab in non muscle invasive bladder cancer?"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 5
- **Answer origin:** internet
- **Tokens (Gemini):** 9082
- **Search saved:** [[what-is-the-new-indication-for-durvalumab-in-non-muscle-invasive-bladder-cancer-2]]
- **Stub pages auto-created:** [[durvalumab]], [[non-muscle-invasive-bladder-cancer]], [[bacillus-calmette-guerin]], [[potomac-trial]], [[high-risk-non-muscle-invasive-bladder-cancer]]

## [2026-06-05] query | Waht is the The 3-year IDFS rate was for T-DXd compared to T-DM1 for b...

- **User:** jim.chen
- **Question:** "Waht is the The 3-year IDFS rate was for T-DXd compared to T-DM1 for breast cancer in the adjuvant setting"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[destiny-breast05]], [[destiny-breast05-april-2026-update]], [[katherine-trial]], [[trastuzumab-deruxtecan]], [[trastuzumab-emtansine]], [[adjuvant-her2-positive-breast-cancer]]
- **Gemini calls:** 3
- **Answer origin:** wiki
- **Tokens (Gemini):** 12884

## [2026-06-05] query | What is the new indication for durvalumab in non muscle invasive bladd...

- **User:** jim.chen
- **Question:** "What is the new indication for durvalumab in non muscle invasive bladder cancer?"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 5
- **Answer origin:** internet
- **Tokens (Gemini):** 8563
- **Search saved:** [[what-is-the-new-indication-for-durvalumab-in-non-muscle-invasive-bladder-cancer-3]]
- **Stub pages auto-created:** [[bcg-naive-high-risk-non-muscle-invasive-bladder-cancer]], [[disease-free-survival]]

## [2026-06-05] query | What is the new indication for durvalumab in non muscle invasive bladd...

- **User:** jim.chen
- **Question:** "What is the new indication for durvalumab in non muscle invasive bladder cancer?"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 4
- **Answer origin:** internet
- **Tokens (Gemini):** 5014
- **Search saved:** [[what-is-the-new-indication-for-durvalumab-in-non-muscle-invasive-bladder-cancer-4]]

## [2026-06-05] query | What is the new indication for durvalumab in non muscle invasive bladd...

- **User:** jim.chen
- **Question:** "What is the new indication for durvalumab in non muscle invasive bladder cancer?"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 4
- **Answer origin:** internet
- **Tokens (Gemini):** 5913

## [2026-06-05] query | Waht is the The 3-year IDFS rate was for T-DXd compared to T-DM1 for b...

- **User:** jim.chen
- **Question:** "Waht is the The 3-year IDFS rate was for T-DXd compared to T-DM1 for breast cancer in the adjuvant setting"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[destiny-breast05]], [[destiny-breast05-april-2026-update]], [[trastuzumab-deruxtecan]], [[trastuzumab-emtansine]], [[katherine-trial]], [[adjuvant-her2-positive-breast-cancer]]
- **Gemini calls:** 3
- **Answer origin:** wiki
- **Tokens (Gemini):** 12830

## [2026-06-05] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the mechanism of action of amivantamab?"
- **Note page:** [[what-is-the-mechanism-of-action-of-amivantamab]] (`wiki/notes/what-is-the-mechanism-of-action-of-amivantamab.md`) — created
- **Raw source:** [[what-is-the-mechanism-of-action-of-amivantamab]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-05] query | What is the mechanism of action of amivantamab?

- **User:** jim.chen
- **Question:** "What is the mechanism of action of amivantamab?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 4
- **Answer origin:** internet
- **Tokens (Gemini):** 7716
- **Search saved:** [[what-is-the-mechanism-of-action-of-amivantamab]]

## [2026-06-05] query | What is the mechanism of action of amivantamab?

- **User:** jim.chen
- **Question:** "What is the mechanism of action of amivantamab?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[what-is-the-mechanism-of-action-of-amivantamab]]
- **Gemini calls:** 3
- **Answer origin:** wiki
- **Tokens (Gemini):** 6699

## [2026-06-07] query | Tell me about AKT pathway drugs available for NSCLC

- **User:** jim.chen
- **Question:** "Tell me about AKT pathway drugs available for NSCLC"
- **Trigger:** Web UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 4
- **Answer origin:** internet
- **Tokens (Gemini):** 8018
- **Search saved:** [[tell-me-about-akt-pathway-drugs-available-for-nsclc]]

## [2026-06-07] query | Tell me about AKT pathway drugs available for NSCLC

- **User:** jim.chen
- **Question:** "Tell me about AKT pathway drugs available for NSCLC"
- **Trigger:** Web UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 4
- **Answer origin:** internet
- **Tokens (Gemini):** 6394
- **Search saved:** [[tell-me-about-akt-pathway-drugs-available-for-nsclc-2]]

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "Tell me about AKT pathway drugs available for NSCLC"
- **Note page:** [[tell-me-about-akt-pathway-drugs-available-for-nsclc]] (`wiki/notes/tell-me-about-akt-pathway-drugs-available-for-nsclc.md`) — created
- **Raw source:** [[tell-me-about-akt-pathway-drugs-available-for-nsclc-3]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] query | Tell me about AKT pathway drugs available for NSCLC

- **User:** jim.chen
- **Question:** "Tell me about AKT pathway drugs available for NSCLC"
- **Trigger:** Web UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 4
- **Answer origin:** internet
- **Tokens (Gemini):** 8513
- **Search saved:** [[tell-me-about-akt-pathway-drugs-available-for-nsclc-3]]

## [2026-06-07] query | Tell me about AKT pathway drugs available for NSCLC

- **User:** jim.chen
- **Question:** "Tell me about AKT pathway drugs available for NSCLC"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[tell-me-about-akt-pathway-drugs-available-for-nsclc]]
- **Gemini calls:** 3
- **Answer origin:** wiki
- **Tokens (Gemini):** 8346

## [2026-06-07] reconcile-index | added 31 missing page(s)

- **User:** jim.chen
- **Why:** these pages existed on disk but were absent from index.md, so the router could not reach them (silent recall hole).
- **Pages indexed (31):**
  - [[peptide-receptor-radionuclide-therapy]]
  - [[disease-free-survival]]
  - [[cvd-regimen]]
  - [[neoadjuvant-treatment]]
  - [[pathologic-complete-response]]
  - [[dreamm-7-trial]]
  - [[altair-trial]]
  - [[glioblastoma]]
  - [[cobra-trial]]
  - [[belzutifan]]
  - [[b-cell-maturation-antigen]]
  - [[ciltacabtagene-autoleucel]]
  - [[destiny-breast11]]
  - [[colon-cancer]]
  - [[temozolomide]]
  - [[durvalumab]]
  - [[ondansetron]]
  - [[belantamab-mafodotin]]
  - [[trastuzumab]]
  - [[non-muscle-invasive-bladder-cancer]]
  - [[trifluridine-tipiracil]]
  - [[absolute-neutrophil-count]]
  - [[dynamic-trial]]
  - [[bcg-naive-high-risk-non-muscle-invasive-bladder-cancer]]
  - [[high-risk-non-muscle-invasive-bladder-cancer]]
  - [[bacillus-calmette-guerin]]
  - [[majestec-3-trial]]
  - [[i-131-iobenguane]]
  - [[paraganglioma]]
  - [[potomac-trial]]
  - [[pertuzumab]]

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the first-line treatment for EGFR exon 19 deletion metastatic NSCLC?"
- **Note page:** [[what-is-the-first-line-treatment-for-egfr-exon-19-deletion-metastatic-nsclc]] (`wiki/notes/what-is-the-first-line-treatment-for-egfr-exon-19-deletion-metastatic-nsclc.md`) — created
- **Raw source:** [[what-is-the-first-line-treatment-for-egfr-exon-19-deletion-metastatic-nsclc]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "How do you treat ALK-positive metastatic NSCLC in the first line?"
- **Note page:** [[how-do-you-treat-alk-positive-metastatic-nsclc-in-the-first-line]] (`wiki/notes/how-do-you-treat-alk-positive-metastatic-nsclc-in-the-first-line.md`) — created
- **Raw source:** [[how-do-you-treat-alk-positive-metastatic-nsclc-in-the-first-line]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the role of adjuvant osimertinib in resected EGFR-mutant NSCLC (ADAURA trial)?"
- **Note page:** [[what-is-the-role-of-adjuvant-osimertinib-in-resected-egfr-mutant-nsclc-adaura-tr]] (`wiki/notes/what-is-the-role-of-adjuvant-osimertinib-in-resected-egfr-mutant-nsclc-adaura-tr.md`) — created
- **Raw source:** [[what-is-the-role-of-adjuvant-osimertinib-in-resected-egfr-mutant-nsclc-adaura-tr]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What are the treatment options for KRAS G12C-mutated NSCLC after progression on first-line therapy?"
- **Note page:** [[what-are-the-treatment-options-for-kras-g12c-mutated-nsclc-after-progression-on-]] (`wiki/notes/what-are-the-treatment-options-for-kras-g12c-mutated-nsclc-after-progression-on-.md`) — created
- **Raw source:** [[what-are-the-treatment-options-for-kras-g12c-mutated-nsclc-after-progression-on-]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "How is PD-L1 expression used to guide first-line immunotherapy in metastatic NSCLC?"
- **Note page:** [[how-is-pd-l1-expression-used-to-guide-first-line-immunotherapy-in-metastatic-nsc]] (`wiki/notes/how-is-pd-l1-expression-used-to-guide-first-line-immunotherapy-in-metastatic-nsc.md`) — created
- **Raw source:** [[how-is-pd-l1-expression-used-to-guide-first-line-immunotherapy-in-metastatic-nsc]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the standard treatment for limited-stage small cell lung cancer?"
- **Note page:** [[what-is-the-standard-treatment-for-limited-stage-small-cell-lung-cancer]] (`wiki/notes/what-is-the-standard-treatment-for-limited-stage-small-cell-lung-cancer.md`) — created
- **Raw source:** [[what-is-the-standard-treatment-for-limited-stage-small-cell-lung-cancer]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the role of consolidation durvalumab after chemoradiation in unresectable stage III NSCLC (P..."
- **Note page:** [[what-is-the-role-of-consolidation-durvalumab-after-chemoradiation-in-unresectabl]] (`wiki/notes/what-is-the-role-of-consolidation-durvalumab-after-chemoradiation-in-unresectabl.md`) — created
- **Raw source:** [[what-is-the-role-of-consolidation-durvalumab-after-chemoradiation-in-unresectabl]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "How do you treat ROS1-rearranged metastatic NSCLC?"
- **Note page:** [[how-do-you-treat-ros1-rearranged-metastatic-nsclc]] (`wiki/notes/how-do-you-treat-ros1-rearranged-metastatic-nsclc.md`) — created
- **Raw source:** [[how-do-you-treat-ros1-rearranged-metastatic-nsclc]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the first-line treatment for metastatic MSI-high colorectal cancer?"
- **Note page:** [[what-is-the-first-line-treatment-for-metastatic-msi-high-colorectal-cancer]] (`wiki/notes/what-is-the-first-line-treatment-for-metastatic-msi-high-colorectal-cancer.md`) — created
- **Raw source:** [[what-is-the-first-line-treatment-for-metastatic-msi-high-colorectal-cancer]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "How do you treat HER2-positive metastatic gastric or gastroesophageal cancer?"
- **Note page:** [[how-do-you-treat-her2-positive-metastatic-gastric-or-gastroesophageal-cancer]] (`wiki/notes/how-do-you-treat-her2-positive-metastatic-gastric-or-gastroesophageal-cancer.md`) — created
- **Raw source:** [[how-do-you-treat-her2-positive-metastatic-gastric-or-gastroesophageal-cancer]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the FOLFIRINOX regimen and its role in pancreatic cancer?"
- **Note page:** [[what-is-the-folfirinox-regimen-and-its-role-in-pancreatic-cancer]] (`wiki/notes/what-is-the-folfirinox-regimen-and-its-role-in-pancreatic-cancer.md`) — created
- **Raw source:** [[what-is-the-folfirinox-regimen-and-its-role-in-pancreatic-cancer]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the first-line treatment for advanced hepatocellular carcinoma (atezolizumab plus bevacizuma..."
- **Note page:** [[what-is-the-first-line-treatment-for-advanced-hepatocellular-carcinoma-atezolizu]] (`wiki/notes/what-is-the-first-line-treatment-for-advanced-hepatocellular-carcinoma-atezolizu.md`) — created
- **Raw source:** [[what-is-the-first-line-treatment-for-advanced-hepatocellular-carcinoma-atezolizu]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "Which biomarkers should be tested in metastatic colorectal cancer to guide therapy?"
- **Note page:** [[which-biomarkers-should-be-tested-in-metastatic-colorectal-cancer-to-guide-thera]] (`wiki/notes/which-biomarkers-should-be-tested-in-metastatic-colorectal-cancer-to-guide-thera.md`) — created
- **Raw source:** [[which-biomarkers-should-be-tested-in-metastatic-colorectal-cancer-to-guide-thera]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the first-line treatment for advanced biliary tract cancer / cholangiocarcinoma?"
- **Note page:** [[what-is-the-first-line-treatment-for-advanced-biliary-tract-cancer-cholangiocarc]] (`wiki/notes/what-is-the-first-line-treatment-for-advanced-biliary-tract-cancer-cholangiocarc.md`) — created
- **Raw source:** [[what-is-the-first-line-treatment-for-advanced-biliary-tract-cancer-cholangiocarc]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "How do you treat BRAF V600E-mutated metastatic colorectal cancer?"
- **Note page:** [[how-do-you-treat-braf-v600e-mutated-metastatic-colorectal-cancer]] (`wiki/notes/how-do-you-treat-braf-v600e-mutated-metastatic-colorectal-cancer.md`) — created
- **Raw source:** [[how-do-you-treat-braf-v600e-mutated-metastatic-colorectal-cancer]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the first-line treatment for metastatic castration-resistant prostate cancer?"
- **Note page:** [[what-is-the-first-line-treatment-for-metastatic-castration-resistant-prostate-ca]] (`wiki/notes/what-is-the-first-line-treatment-for-metastatic-castration-resistant-prostate-ca.md`) — created
- **Raw source:** [[what-is-the-first-line-treatment-for-metastatic-castration-resistant-prostate-ca]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "How do you treat metastatic hormone-sensitive prostate cancer with triplet therapy?"
- **Note page:** [[how-do-you-treat-metastatic-hormone-sensitive-prostate-cancer-with-triplet-thera]] (`wiki/notes/how-do-you-treat-metastatic-hormone-sensitive-prostate-cancer-with-triplet-thera.md`) — created
- **Raw source:** [[how-do-you-treat-metastatic-hormone-sensitive-prostate-cancer-with-triplet-thera]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the role of PARP inhibitors in metastatic prostate cancer with HRR mutations?"
- **Note page:** [[what-is-the-role-of-parp-inhibitors-in-metastatic-prostate-cancer-with-hrr-mutat]] (`wiki/notes/what-is-the-role-of-parp-inhibitors-in-metastatic-prostate-cancer-with-hrr-mutat.md`) — created
- **Raw source:** [[what-is-the-role-of-parp-inhibitors-in-metastatic-prostate-cancer-with-hrr-mutat]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the first-line treatment for metastatic clear cell renal cell carcinoma?"
- **Note page:** [[what-is-the-first-line-treatment-for-metastatic-clear-cell-renal-cell-carcinoma]] (`wiki/notes/what-is-the-first-line-treatment-for-metastatic-clear-cell-renal-cell-carcinoma.md`) — created
- **Raw source:** [[what-is-the-first-line-treatment-for-metastatic-clear-cell-renal-cell-carcinoma]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "How do you treat metastatic urothelial carcinoma with enfortumab vedotin plus pembrolizumab?"
- **Note page:** [[how-do-you-treat-metastatic-urothelial-carcinoma-with-enfortumab-vedotin-plus-pe]] (`wiki/notes/how-do-you-treat-metastatic-urothelial-carcinoma-with-enfortumab-vedotin-plus-pe.md`) — created
- **Raw source:** [[how-do-you-treat-metastatic-urothelial-carcinoma-with-enfortumab-vedotin-plus-pe]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "How is non-clear-cell renal cell carcinoma treated?"
- **Note page:** [[how-is-non-clear-cell-renal-cell-carcinoma-treated]] (`wiki/notes/how-is-non-clear-cell-renal-cell-carcinoma-treated.md`) — created
- **Raw source:** [[how-is-non-clear-cell-renal-cell-carcinoma-treated]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the first-line treatment for diffuse large B-cell lymphoma?"
- **Note page:** [[what-is-the-first-line-treatment-for-diffuse-large-b-cell-lymphoma]] (`wiki/notes/what-is-the-first-line-treatment-for-diffuse-large-b-cell-lymphoma.md`) — created
- **Raw source:** [[what-is-the-first-line-treatment-for-diffuse-large-b-cell-lymphoma]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "How do you treat relapsed or refractory DLBCL with CAR-T cell therapy?"
- **Note page:** [[how-do-you-treat-relapsed-or-refractory-dlbcl-with-car-t-cell-therapy]] (`wiki/notes/how-do-you-treat-relapsed-or-refractory-dlbcl-with-car-t-cell-therapy.md`) — created
- **Raw source:** [[how-do-you-treat-relapsed-or-refractory-dlbcl-with-car-t-cell-therapy]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the frontline treatment for chronic lymphocytic leukemia (CLL)?"
- **Note page:** [[what-is-the-frontline-treatment-for-chronic-lymphocytic-leukemia-cll]] (`wiki/notes/what-is-the-frontline-treatment-for-chronic-lymphocytic-leukemia-cll.md`) — created
- **Raw source:** [[what-is-the-frontline-treatment-for-chronic-lymphocytic-leukemia-cll]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "How do you treat newly diagnosed multiple myeloma in transplant-eligible patients?"
- **Note page:** [[how-do-you-treat-newly-diagnosed-multiple-myeloma-in-transplant-eligible-patient]] (`wiki/notes/how-do-you-treat-newly-diagnosed-multiple-myeloma-in-transplant-eligible-patient.md`) — created
- **Raw source:** [[how-do-you-treat-newly-diagnosed-multiple-myeloma-in-transplant-eligible-patient]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the first-line treatment for advanced Hodgkin lymphoma?"
- **Note page:** [[what-is-the-first-line-treatment-for-advanced-hodgkin-lymphoma]] (`wiki/notes/what-is-the-first-line-treatment-for-advanced-hodgkin-lymphoma.md`) — created
- **Raw source:** [[what-is-the-first-line-treatment-for-advanced-hodgkin-lymphoma]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "How do you treat acute myeloid leukemia with FLT3 mutations?"
- **Note page:** [[how-do-you-treat-acute-myeloid-leukemia-with-flt3-mutations]] (`wiki/notes/how-do-you-treat-acute-myeloid-leukemia-with-flt3-mutations.md`) — created
- **Raw source:** [[how-do-you-treat-acute-myeloid-leukemia-with-flt3-mutations]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the standard first-line management of follicular lymphoma?"
- **Note page:** [[what-is-the-standard-first-line-management-of-follicular-lymphoma]] (`wiki/notes/what-is-the-standard-first-line-management-of-follicular-lymphoma.md`) — created
- **Raw source:** [[what-is-the-standard-first-line-management-of-follicular-lymphoma]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] verify-note | what-is-the-standard-first-line-management-of-follicular-lymphoma

- **User:** jim.chen
- **Page:** [[what-is-the-standard-first-line-management-of-follicular-lymphoma]] (`wiki/notes/what-is-the-standard-first-line-management-of-follicular-lymphoma.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-first-line-treatment-for-advanced-hodgkin-lymphoma

- **User:** jim.chen
- **Page:** [[what-is-the-first-line-treatment-for-advanced-hodgkin-lymphoma]] (`wiki/notes/what-is-the-first-line-treatment-for-advanced-hodgkin-lymphoma.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | how-do-you-treat-acute-myeloid-leukemia-with-flt3-mutations

- **User:** jim.chen
- **Page:** [[how-do-you-treat-acute-myeloid-leukemia-with-flt3-mutations]] (`wiki/notes/how-do-you-treat-acute-myeloid-leukemia-with-flt3-mutations.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | how-do-you-treat-newly-diagnosed-multiple-myeloma-in-transplant-eligible-patient

- **User:** jim.chen
- **Page:** [[how-do-you-treat-newly-diagnosed-multiple-myeloma-in-transplant-eligible-patient]] (`wiki/notes/how-do-you-treat-newly-diagnosed-multiple-myeloma-in-transplant-eligible-patient.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-frontline-treatment-for-chronic-lymphocytic-leukemia-cll

- **User:** jim.chen
- **Page:** [[what-is-the-frontline-treatment-for-chronic-lymphocytic-leukemia-cll]] (`wiki/notes/what-is-the-frontline-treatment-for-chronic-lymphocytic-leukemia-cll.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | how-do-you-treat-relapsed-or-refractory-dlbcl-with-car-t-cell-therapy

- **User:** jim.chen
- **Page:** [[how-do-you-treat-relapsed-or-refractory-dlbcl-with-car-t-cell-therapy]] (`wiki/notes/how-do-you-treat-relapsed-or-refractory-dlbcl-with-car-t-cell-therapy.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-first-line-treatment-for-diffuse-large-b-cell-lymphoma

- **User:** jim.chen
- **Page:** [[what-is-the-first-line-treatment-for-diffuse-large-b-cell-lymphoma]] (`wiki/notes/what-is-the-first-line-treatment-for-diffuse-large-b-cell-lymphoma.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | how-is-non-clear-cell-renal-cell-carcinoma-treated

- **User:** jim.chen
- **Page:** [[how-is-non-clear-cell-renal-cell-carcinoma-treated]] (`wiki/notes/how-is-non-clear-cell-renal-cell-carcinoma-treated.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | how-do-you-treat-metastatic-urothelial-carcinoma-with-enfortumab-vedotin-plus-pe

- **User:** jim.chen
- **Page:** [[how-do-you-treat-metastatic-urothelial-carcinoma-with-enfortumab-vedotin-plus-pe]] (`wiki/notes/how-do-you-treat-metastatic-urothelial-carcinoma-with-enfortumab-vedotin-plus-pe.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-first-line-treatment-for-metastatic-clear-cell-renal-cell-carcinoma

- **User:** jim.chen
- **Page:** [[what-is-the-first-line-treatment-for-metastatic-clear-cell-renal-cell-carcinoma]] (`wiki/notes/what-is-the-first-line-treatment-for-metastatic-clear-cell-renal-cell-carcinoma.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-role-of-parp-inhibitors-in-metastatic-prostate-cancer-with-hrr-mutat

- **User:** jim.chen
- **Page:** [[what-is-the-role-of-parp-inhibitors-in-metastatic-prostate-cancer-with-hrr-mutat]] (`wiki/notes/what-is-the-role-of-parp-inhibitors-in-metastatic-prostate-cancer-with-hrr-mutat.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | how-do-you-treat-metastatic-hormone-sensitive-prostate-cancer-with-triplet-thera

- **User:** jim.chen
- **Page:** [[how-do-you-treat-metastatic-hormone-sensitive-prostate-cancer-with-triplet-thera]] (`wiki/notes/how-do-you-treat-metastatic-hormone-sensitive-prostate-cancer-with-triplet-thera.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-first-line-treatment-for-metastatic-castration-resistant-prostate-ca

- **User:** jim.chen
- **Page:** [[what-is-the-first-line-treatment-for-metastatic-castration-resistant-prostate-ca]] (`wiki/notes/what-is-the-first-line-treatment-for-metastatic-castration-resistant-prostate-ca.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | how-do-you-treat-braf-v600e-mutated-metastatic-colorectal-cancer

- **User:** jim.chen
- **Page:** [[how-do-you-treat-braf-v600e-mutated-metastatic-colorectal-cancer]] (`wiki/notes/how-do-you-treat-braf-v600e-mutated-metastatic-colorectal-cancer.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-first-line-treatment-for-advanced-biliary-tract-cancer-cholangiocarc

- **User:** jim.chen
- **Page:** [[what-is-the-first-line-treatment-for-advanced-biliary-tract-cancer-cholangiocarc]] (`wiki/notes/what-is-the-first-line-treatment-for-advanced-biliary-tract-cancer-cholangiocarc.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | which-biomarkers-should-be-tested-in-metastatic-colorectal-cancer-to-guide-thera

- **User:** jim.chen
- **Page:** [[which-biomarkers-should-be-tested-in-metastatic-colorectal-cancer-to-guide-thera]] (`wiki/notes/which-biomarkers-should-be-tested-in-metastatic-colorectal-cancer-to-guide-thera.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-first-line-treatment-for-advanced-hepatocellular-carcinoma-atezolizu

- **User:** jim.chen
- **Page:** [[what-is-the-first-line-treatment-for-advanced-hepatocellular-carcinoma-atezolizu]] (`wiki/notes/what-is-the-first-line-treatment-for-advanced-hepatocellular-carcinoma-atezolizu.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-folfirinox-regimen-and-its-role-in-pancreatic-cancer

- **User:** jim.chen
- **Page:** [[what-is-the-folfirinox-regimen-and-its-role-in-pancreatic-cancer]] (`wiki/notes/what-is-the-folfirinox-regimen-and-its-role-in-pancreatic-cancer.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | how-do-you-treat-her2-positive-metastatic-gastric-or-gastroesophageal-cancer

- **User:** jim.chen
- **Page:** [[how-do-you-treat-her2-positive-metastatic-gastric-or-gastroesophageal-cancer]] (`wiki/notes/how-do-you-treat-her2-positive-metastatic-gastric-or-gastroesophageal-cancer.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-first-line-treatment-for-metastatic-msi-high-colorectal-cancer

- **User:** jim.chen
- **Page:** [[what-is-the-first-line-treatment-for-metastatic-msi-high-colorectal-cancer]] (`wiki/notes/what-is-the-first-line-treatment-for-metastatic-msi-high-colorectal-cancer.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | how-do-you-treat-ros1-rearranged-metastatic-nsclc

- **User:** jim.chen
- **Page:** [[how-do-you-treat-ros1-rearranged-metastatic-nsclc]] (`wiki/notes/how-do-you-treat-ros1-rearranged-metastatic-nsclc.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-role-of-consolidation-durvalumab-after-chemoradiation-in-unresectabl

- **User:** jim.chen
- **Page:** [[what-is-the-role-of-consolidation-durvalumab-after-chemoradiation-in-unresectabl]] (`wiki/notes/what-is-the-role-of-consolidation-durvalumab-after-chemoradiation-in-unresectabl.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-mechanism-of-action-of-amivantamab

- **User:** jim.chen
- **Page:** [[what-is-the-mechanism-of-action-of-amivantamab]] (`wiki/notes/what-is-the-mechanism-of-action-of-amivantamab.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | tell-me-about-akt-pathway-drugs-available-for-nsclc

- **User:** jim.chen
- **Page:** [[tell-me-about-akt-pathway-drugs-available-for-nsclc]] (`wiki/notes/tell-me-about-akt-pathway-drugs-available-for-nsclc.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-first-line-treatment-for-egfr-exon-19-deletion-metastatic-nsclc

- **User:** jim.chen
- **Page:** [[what-is-the-first-line-treatment-for-egfr-exon-19-deletion-metastatic-nsclc]] (`wiki/notes/what-is-the-first-line-treatment-for-egfr-exon-19-deletion-metastatic-nsclc.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | how-do-you-treat-alk-positive-metastatic-nsclc-in-the-first-line

- **User:** jim.chen
- **Page:** [[how-do-you-treat-alk-positive-metastatic-nsclc-in-the-first-line]] (`wiki/notes/how-do-you-treat-alk-positive-metastatic-nsclc-in-the-first-line.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-role-of-adjuvant-osimertinib-in-resected-egfr-mutant-nsclc-adaura-tr

- **User:** jim.chen
- **Page:** [[what-is-the-role-of-adjuvant-osimertinib-in-resected-egfr-mutant-nsclc-adaura-tr]] (`wiki/notes/what-is-the-role-of-adjuvant-osimertinib-in-resected-egfr-mutant-nsclc-adaura-tr.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | how-is-pd-l1-expression-used-to-guide-first-line-immunotherapy-in-metastatic-nsc

- **User:** jim.chen
- **Page:** [[how-is-pd-l1-expression-used-to-guide-first-line-immunotherapy-in-metastatic-nsc]] (`wiki/notes/how-is-pd-l1-expression-used-to-guide-first-line-immunotherapy-in-metastatic-nsc.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-standard-treatment-for-limited-stage-small-cell-lung-cancer

- **User:** jim.chen
- **Page:** [[what-is-the-standard-treatment-for-limited-stage-small-cell-lung-cancer]] (`wiki/notes/what-is-the-standard-treatment-for-limited-stage-small-cell-lung-cancer.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-are-the-treatment-options-for-kras-g12c-mutated-nsclc-after-progression-on-

- **User:** jim.chen
- **Page:** [[what-are-the-treatment-options-for-kras-g12c-mutated-nsclc-after-progression-on-]] (`wiki/notes/what-are-the-treatment-options-for-kras-g12c-mutated-nsclc-after-progression-on-.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] promote | stupp-protocol

- **User:** jim.chen
- **Page:** [[stupp-protocol]] → `wiki/concepts/stupp-protocol.md` (moved out of wiki/stubs/)
- **Action:** stripped `auto_generated`/`stub_target` markers and warning callout; promoted to the curated namespace.
- **Reminder:** consider an agent ingest to expand to full SCHEMA structure (Overview, Key facts, Related entities, Sources).

## [2026-06-07] query | First line treatment for EGFR mutated NSCLC metastatic

- **User:** jim.chen
- **Question:** "First line treatment for EGFR mutated NSCLC metastatic"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[what-is-the-first-line-treatment-for-egfr-exon-19-deletion-metastatic-nsclc]]
- **Gemini calls:** 3
- **Answer origin:** wiki
- **Tokens (Gemini):** 10539

## [2026-06-07] query | First line treatment for EGFR mutated NSCLC metastatic

- **User:** jim.chen
- **Question:** "First line treatment for EGFR mutated NSCLC metastatic"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[what-is-the-first-line-treatment-for-egfr-exon-19-deletion-metastatic-nsclc]]
- **Gemini calls:** 2
- **Answer origin:** wiki
- **Tokens (Gemini):** 4482

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What are some options for second line treatment for EGFR mutated NSCLC after progression on osimerti..."
- **Note page:** [[what-are-some-options-for-second-line-treatment-for-egfr-mutated-nsclc-after-pro]] (`wiki/notes/what-are-some-options-for-second-line-treatment-for-egfr-mutated-nsclc-after-pro.md`) — created
- **Raw source:** [[what-are-some-options-for-second-line-treatment-for-egfr-mutated-nsclc-after-pro]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] query | What are some options for second line treatment for EGFR mutated NSCLC...

- **User:** jim.chen
- **Question:** "What are some options for second line treatment for EGFR mutated NSCLC after progression on osimertinib"
- **Trigger:** Web UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 3
- **Answer origin:** internet
- **Tokens (Gemini):** 6075
- **Search saved:** [[what-are-some-options-for-second-line-treatment-for-egfr-mutated-nsclc-after-pro]]

## [2026-06-07] verify-note | what-are-some-options-for-second-line-treatment-for-egfr-mutated-nsclc-after-pro

- **User:** jim.chen
- **Page:** [[what-are-some-options-for-second-line-treatment-for-egfr-mutated-nsclc-after-pro]] (`wiki/notes/what-are-some-options-for-second-line-treatment-for-egfr-mutated-nsclc-after-pro.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What are treatment options for metastatic colon cancer with BRAF V600E mutation who have progressed ..."
- **Note page:** [[what-are-treatment-options-for-metastatic-colon-cancer-with-braf-v600e-mutation-]] (`wiki/notes/what-are-treatment-options-for-metastatic-colon-cancer-with-braf-v600e-mutation-.md`) — created
- **Raw source:** [[what-are-treatment-options-for-metastatic-colon-cancer-with-braf-v600e-mutation-]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] query | What are treatment options for metastatic colon cancer with BRAF V600E...

- **User:** jim.chen
- **Question:** "What are treatment options for metastatic colon cancer with BRAF V600E mutation who have progressed on FOLFOX + dabrafenib and trametinib?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[how-do-you-treat-braf-v600e-mutated-metastatic-colorectal-cancer]], [[trifluridine-tipiracil]]
- **Gemini calls:** 3
- **Answer origin:** mixed
- **Tokens (Gemini):** 11773
- **Search saved:** [[what-are-treatment-options-for-metastatic-colon-cancer-with-braf-v600e-mutation-]]

## [2026-06-07] query | IS there a role for immunothearpy for metastatic colon cancer with BRA...

- **User:** jim.chen
- **Question:** "IS there a role for immunothearpy for metastatic colon cancer with BRAF V600E mutation after progressing on Encorafenib plus Cetuximab + FOLFOX?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[what-are-treatment-options-for-metastatic-colon-cancer-with-braf-v600e-mutation-]], [[what-is-the-first-line-treatment-for-metastatic-msi-high-colorectal-cancer]], [[how-do-you-treat-braf-v600e-mutated-metastatic-colorectal-cancer]], [[which-biomarkers-should-be-tested-in-metastatic-colorectal-cancer-to-guide-thera]]
- **Gemini calls:** 2
- **Answer origin:** wiki
- **Tokens (Gemini):** 10462

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the first-line treatment for BRAF V600E-mutated metastatic melanoma?"
- **Note page:** [[what-is-the-first-line-treatment-for-braf-v600e-mutated-metastatic-melanoma]] (`wiki/notes/what-is-the-first-line-treatment-for-braf-v600e-mutated-metastatic-melanoma.md`) — created
- **Raw source:** [[what-is-the-first-line-treatment-for-braf-v600e-mutated-metastatic-melanoma]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "With PMID's what are some updates with NSCLC that was recently published at ASCO?"
- **Note page:** [[with-pmids-what-are-some-updates-with-nsclc-that-was-recently-published-at-asco]] (`wiki/notes/with-pmids-what-are-some-updates-with-nsclc-that-was-recently-published-at-asco.md`) — created
- **Raw source:** [[with-pmids-what-are-some-updates-with-nsclc-that-was-recently-published-at-asco]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] query | With PMID's what are some updates with NSCLC that was recently publish...

- **User:** jim.chen
- **Question:** "With PMID's what are some updates with NSCLC that was recently published at ASCO?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[what-is-the-first-line-treatment-for-egfr-exon-19-deletion-metastatic-nsclc]], [[what-is-the-role-of-adjuvant-osimertinib-in-resected-egfr-mutant-nsclc-adaura-tr]], [[what-are-some-options-for-second-line-treatment-for-egfr-mutated-nsclc-after-pro]], [[what-are-the-treatment-options-for-kras-g12c-mutated-nsclc-after-progression-on-]]
- **Gemini calls:** 3
- **Answer origin:** mixed
- **Tokens (Gemini):** 17287
- **Search saved:** [[with-pmids-what-are-some-updates-with-nsclc-that-was-recently-published-at-asco]]

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "With PMID's what are some updates with pancreatic cancer that was recently published at ASCO?"
- **Note page:** [[with-pmids-what-are-some-updates-with-pancreatic-cancer-that-was-recently-publis]] (`wiki/notes/with-pmids-what-are-some-updates-with-pancreatic-cancer-that-was-recently-publis.md`) — created
- **Raw source:** [[with-pmids-what-are-some-updates-with-pancreatic-cancer-that-was-recently-publis]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] query | With PMID's what are some updates with pancreatic cancer that was rece...

- **User:** jim.chen
- **Question:** "With PMID's what are some updates with pancreatic cancer that was recently published at ASCO?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 3
- **Answer origin:** internet
- **Tokens (Gemini):** 7222
- **Search saved:** [[with-pmids-what-are-some-updates-with-pancreatic-cancer-that-was-recently-publis]]

## [2026-06-07] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "Tell me about the publication associated with the RASolute 302 trial"
- **Note page:** [[tell-me-about-the-publication-associated-with-the-rasolute-302-trial]] (`wiki/notes/tell-me-about-the-publication-associated-with-the-rasolute-302-trial.md`) — created
- **Raw source:** [[tell-me-about-the-publication-associated-with-the-rasolute-302-trial]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-07] query | Tell me about the publication associated with the RASolute 302 trial

- **User:** jim.chen
- **Question:** "Tell me about the publication associated with the RASolute 302 trial"
- **Trigger:** Web UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 3
- **Answer origin:** internet
- **Tokens (Gemini):** 3048
- **Search saved:** [[tell-me-about-the-publication-associated-with-the-rasolute-302-trial]]

## [2026-06-07] query | Tell me about the publication associated with the RASolute 302 trial. ...

- **User:** jim.chen
- **Question:** "Tell me about the publication associated with the RASolute 302 trial. What is the pubmed ID ?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[tell-me-about-the-publication-associated-with-the-rasolute-302-trial]]
- **Gemini calls:** 2
- **Answer origin:** wiki
- **Tokens (Gemini):** 5168

## [2026-06-07] verify-note | tell-me-about-the-publication-associated-with-the-rasolute-302-trial

- **User:** jim.chen
- **Page:** [[tell-me-about-the-publication-associated-with-the-rasolute-302-trial]] (`wiki/notes/tell-me-about-the-publication-associated-with-the-rasolute-302-trial.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | with-pmids-what-are-some-updates-with-pancreatic-cancer-that-was-recently-publis

- **User:** jim.chen
- **Page:** [[with-pmids-what-are-some-updates-with-pancreatic-cancer-that-was-recently-publis]] (`wiki/notes/with-pmids-what-are-some-updates-with-pancreatic-cancer-that-was-recently-publis.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | with-pmids-what-are-some-updates-with-nsclc-that-was-recently-published-at-asco

- **User:** jim.chen
- **Page:** [[with-pmids-what-are-some-updates-with-nsclc-that-was-recently-published-at-asco]] (`wiki/notes/with-pmids-what-are-some-updates-with-nsclc-that-was-recently-published-at-asco.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-is-the-first-line-treatment-for-braf-v600e-mutated-metastatic-melanoma

- **User:** jim.chen
- **Page:** [[what-is-the-first-line-treatment-for-braf-v600e-mutated-metastatic-melanoma]] (`wiki/notes/what-is-the-first-line-treatment-for-braf-v600e-mutated-metastatic-melanoma.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-07] verify-note | what-are-treatment-options-for-metastatic-colon-cancer-with-braf-v600e-mutation-

- **User:** jim.chen
- **Page:** [[what-are-treatment-options-for-metastatic-colon-cancer-with-braf-v600e-mutation-]] (`wiki/notes/what-are-treatment-options-for-metastatic-colon-cancer-with-braf-v600e-mutation-.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-07).

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "Please provide any FDA indication for cancer treatment in May and June 2026"
- **Note page:** [[please-provide-any-fda-indication-for-cancer-treatment-in-may-and-june-2026]] (`wiki/notes/please-provide-any-fda-indication-for-cancer-treatment-in-may-and-june-2026.md`) — created
- **Raw source:** [[please-provide-any-fda-indication-for-cancer-treatment-in-may-and-june-2026]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | Please provide any FDA indication for cancer treatment in May and June...

- **User:** jim.chen
- **Question:** "Please provide any FDA indication for cancer treatment in May and June 2026"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[premenopausal-intermediate-oncotype-2026]]
- **Gemini calls:** 3
- **Answer origin:** mixed
- **Tokens (Gemini):** 10185
- **Search saved:** [[please-provide-any-fda-indication-for-cancer-treatment-in-may-and-june-2026]]

## [2026-06-08] verify-note | please-provide-any-fda-indication-for-cancer-treatment-in-may-and-june-2026

- **User:** jim.chen
- **Page:** [[please-provide-any-fda-indication-for-cancer-treatment-in-may-and-june-2026]] (`wiki/notes/please-provide-any-fda-indication-for-cancer-treatment-in-may-and-june-2026.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] query | What is CAR-T? Summarize its design and key results.

- **User:** jim.chen
- **Question:** "What is CAR-T? Summarize its design and key results."
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[ciltacabtagene-autoleucel]], [[how-do-you-treat-relapsed-or-refractory-dlbcl-with-car-t-cell-therapy]], [[b-cell-maturation-antigen]]
- **Gemini calls:** 2
- **Answer origin:** wiki
- **Tokens (Gemini):** 7258

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "For Sonrotoclax's accelerated approval in relapsed/refractory MCL, what are the details regarding th..."
- **Note page:** [[for-sonrotoclaxs-accelerated-approval-in-relapsedrefractory-mcl-what-are-the-det]] (`wiki/notes/for-sonrotoclaxs-accelerated-approval-in-relapsedrefractory-mcl-what-are-the-det.md`) — created
- **Raw source:** [[for-sonrotoclaxs-accelerated-approval-in-relapsedrefractory-mcl-what-are-the-det]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | For Sonrotoclax's accelerated approval in relapsed/refractory MCL, wha...

- **User:** jim.chen
- **Question:** "For Sonrotoclax's accelerated approval in relapsed/refractory MCL, what are the details regarding the planned confirmatory trials, and are there specific considerations for managing tumor lysis syndrome given its BCL-2 inhibitor mechanism?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 3
- **Answer origin:** internet
- **Tokens (Gemini):** 4743
- **Search saved:** [[for-sonrotoclaxs-accelerated-approval-in-relapsedrefractory-mcl-what-are-the-det]]

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What are the common or dose-limiting toxicities observed with daraxonrasib and the MEK inhibitor-bas..."
- **Note page:** [[what-are-the-common-or-dose-limiting-toxicities-observed-with-daraxonrasib-and-t]] (`wiki/notes/what-are-the-common-or-dose-limiting-toxicities-observed-with-daraxonrasib-and-t.md`) — created
- **Raw source:** [[what-are-the-common-or-dose-limiting-toxicities-observed-with-daraxonrasib-and-t]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | What are the common or dose-limiting toxicities observed with daraxonr...

- **User:** jim.chen
- **Question:** "What are the common or dose-limiting toxicities observed with daraxonrasib and the MEK inhibitor-based combinatorial therapies, and what are the recommended management strategies?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[what-are-treatment-options-for-metastatic-colon-cancer-with-braf-v600e-mutation-]]
- **Gemini calls:** 3
- **Answer origin:** mixed
- **Tokens (Gemini):** 10681
- **Search saved:** [[what-are-the-common-or-dose-limiting-toxicities-observed-with-daraxonrasib-and-t]]

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What are the specific toxicity profiles and recommended management strategies for Vepdegestrant, par..."
- **Note page:** [[what-are-the-specific-toxicity-profiles-and-recommended-management-strategies-fo]] (`wiki/notes/what-are-the-specific-toxicity-profiles-and-recommended-management-strategies-fo.md`) — created
- **Raw source:** [[what-are-the-specific-toxicity-profiles-and-recommended-management-strategies-fo]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | What are the specific toxicity profiles and recommended management str...

- **User:** jim.chen
- **Question:** "What are the specific toxicity profiles and recommended management strategies for Vepdegestrant, particularly considering its novel PROTAC mechanism of action?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 3
- **Answer origin:** internet
- **Tokens (Gemini):** 3802
- **Search saved:** [[what-are-the-specific-toxicity-profiles-and-recommended-management-strategies-fo]]

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the detailed safety and tolerability profile of sunvozertinib, and how does it compare to pl..."
- **Note page:** [[what-is-the-detailed-safety-and-tolerability-profile-of-sunvozertinib-and-how-do]] (`wiki/notes/what-is-the-detailed-safety-and-tolerability-profile-of-sunvozertinib-and-how-do.md`) — created
- **Raw source:** [[what-is-the-detailed-safety-and-tolerability-profile-of-sunvozertinib-and-how-do]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | What is the detailed safety and tolerability profile of sunvozertinib,...

- **User:** jim.chen
- **Question:** "What is the detailed safety and tolerability profile of sunvozertinib, and how does it compare to platinum-based chemotherapy or other EGFR exon 20 insertion inhibitors?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 3
- **Answer origin:** internet
- **Tokens (Gemini):** 5915
- **Search saved:** [[what-is-the-detailed-safety-and-tolerability-profile-of-sunvozertinib-and-how-do]]

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the recommended sequencing of Vepdegestrant relative to other non-endocrine targeted therapi..."
- **Note page:** [[what-is-the-recommended-sequencing-of-vepdegestrant-relative-to-other-non-endocr]] (`wiki/notes/what-is-the-recommended-sequencing-of-vepdegestrant-relative-to-other-non-endocr.md`) — created
- **Raw source:** [[what-is-the-recommended-sequencing-of-vepdegestrant-relative-to-other-non-endocr]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | What is the recommended sequencing of Vepdegestrant relative to other ...

- **User:** jim.chen
- **Question:** "What is the recommended sequencing of Vepdegestrant relative to other non-endocrine targeted therapies (e.g., PI3K inhibitors, mTOR inhibitors) for ER+, HER2-, ESR1-mutated breast cancer patients who have progressed on prior endocrine therapy?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[what-are-the-specific-toxicity-profiles-and-recommended-management-strategies-fo]]
- **Gemini calls:** 3
- **Answer origin:** mixed
- **Tokens (Gemini):** 12133
- **Search saved:** [[what-is-the-recommended-sequencing-of-vepdegestrant-relative-to-other-non-endocr]]

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "Were any mechanisms of resistance to daraxonrasib or the MEK inhibitor-based therapies identified in..."
- **Note page:** [[were-any-mechanisms-of-resistance-to-daraxonrasib-or-the-mek-inhibitor-based-the]] (`wiki/notes/were-any-mechanisms-of-resistance-to-daraxonrasib-or-the-mek-inhibitor-based-the.md`) — created
- **Raw source:** [[were-any-mechanisms-of-resistance-to-daraxonrasib-or-the-mek-inhibitor-based-the]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | Were any mechanisms of resistance to daraxonrasib or the MEK inhibitor...

- **User:** jim.chen
- **Question:** "Were any mechanisms of resistance to daraxonrasib or the MEK inhibitor-based therapies identified in the trials, and what are the implications for long-term efficacy or subsequent treatment choices?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[what-are-treatment-options-for-metastatic-colon-cancer-with-braf-v600e-mutation-]], [[what-are-the-treatment-options-for-kras-g12c-mutated-nsclc-after-progression-on-]]
- **Gemini calls:** 3
- **Answer origin:** mixed
- **Tokens (Gemini):** 15129
- **Search saved:** [[were-any-mechanisms-of-resistance-to-daraxonrasib-or-the-mek-inhibitor-based-the]]

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What were the specific median overall survival values, hazard ratios, progression-free survival, and..."
- **Note page:** [[what-were-the-specific-median-overall-survival-values-hazard-ratios-progression-]] (`wiki/notes/what-were-the-specific-median-overall-survival-values-hazard-ratios-progression-.md`) — created
- **Raw source:** [[what-were-the-specific-median-overall-survival-values-hazard-ratios-progression-]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | What were the specific median overall survival values, hazard ratios, ...

- **User:** jim.chen
- **Question:** "What were the specific median overall survival values, hazard ratios, progression-free survival, and overall response rates observed in the daraxonrasib and standard-of-care arms?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[tell-me-about-the-publication-associated-with-the-rasolute-302-trial]]
- **Gemini calls:** 3
- **Answer origin:** mixed
- **Tokens (Gemini):** 10651
- **Search saved:** [[what-were-the-specific-median-overall-survival-values-hazard-ratios-progression-]]

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What factors (e.g., prior toxicities, comorbidities, specific disease characteristics) should guide ..."
- **Note page:** [[what-factors-eg-prior-toxicities-comorbidities-specific-disease-characteristics-]] (`wiki/notes/what-factors-eg-prior-toxicities-comorbidities-specific-disease-characteristics-.md`) — created
- **Raw source:** [[what-factors-eg-prior-toxicities-comorbidities-specific-disease-characteristics-]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | What factors (e.g., prior toxicities, comorbidities, specific disease ...

- **User:** jim.chen
- **Question:** "What factors (e.g., prior toxicities, comorbidities, specific disease characteristics) should guide the choice between bevacizumab, ramucirumab, or aflibercept when combined with FOLFIRI?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 3
- **Answer origin:** internet
- **Tokens (Gemini):** 7028
- **Search saved:** [[what-factors-eg-prior-toxicities-comorbidities-specific-disease-characteristics-]]

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is CAR-T? Summarize its design and key results."
- **Note page:** [[what-is-car-t-summarize-its-design-and-key-results]] (`wiki/notes/what-is-car-t-summarize-its-design-and-key-results.md`) — created
- **Raw source:** [[what-is-car-t-summarize-its-design-and-key-results]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | What is CAR-T? Summarize its design and key results.

- **User:** jim.chen
- **Question:** "What is CAR-T? Summarize its design and key results."
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[ciltacabtagene-autoleucel]], [[how-do-you-treat-relapsed-or-refractory-dlbcl-with-car-t-cell-therapy]], [[b-cell-maturation-antigen]]
- **Gemini calls:** 3
- **Answer origin:** mixed
- **Tokens (Gemini):** 12420
- **Search saved:** [[what-is-car-t-summarize-its-design-and-key-results]]

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "Are there specific patient selection criteria or biomarkers beyond general RAS mutation that predict..."
- **Note page:** [[are-there-specific-patient-selection-criteria-or-biomarkers-beyond-general-ras-m]] (`wiki/notes/are-there-specific-patient-selection-criteria-or-biomarkers-beyond-general-ras-m.md`) — created
- **Raw source:** [[are-there-specific-patient-selection-criteria-or-biomarkers-beyond-general-ras-m]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | Are there specific patient selection criteria or biomarkers beyond gen...

- **User:** jim.chen
- **Question:** "Are there specific patient selection criteria or biomarkers beyond general RAS mutation that predict response to daraxonrasib, and what are the known resistance mechanisms or recommended subsequent therapies?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[were-any-mechanisms-of-resistance-to-daraxonrasib-or-the-mek-inhibitor-based-the]]
- **Gemini calls:** 3
- **Answer origin:** mixed
- **Tokens (Gemini):** 12702
- **Search saved:** [[are-there-specific-patient-selection-criteria-or-biomarkers-beyond-general-ras-m]]

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the biomarker testing to guide therapy for multiple myeloma?"
- **Note page:** [[what-is-the-biomarker-testing-to-guide-therapy-for-multiple-myeloma]] (`wiki/notes/what-is-the-biomarker-testing-to-guide-therapy-for-multiple-myeloma.md`) — created
- **Raw source:** [[what-is-the-biomarker-testing-to-guide-therapy-for-multiple-myeloma]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | What is the biomarker testing to guide therapy for multiple myeloma?

- **User:** jim.chen
- **Question:** "What is the biomarker testing to guide therapy for multiple myeloma?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[mrd-guided-therapy-escalation]], [[b-cell-maturation-antigen]], [[circulating-tumor-dna]], [[ciltacabtagene-autoleucel]], [[belantamab-mafodotin]], [[majestec-3-trial]]
- **Gemini calls:** 3
- **Answer origin:** mixed
- **Tokens (Gemini):** 13867
- **Search saved:** [[what-is-the-biomarker-testing-to-guide-therapy-for-multiple-myeloma]]

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the second-line treatment after progression for advanced gastric cancer?"
- **Note page:** [[what-is-the-second-line-treatment-after-progression-for-advanced-gastric-cancer]] (`wiki/notes/what-is-the-second-line-treatment-after-progression-for-advanced-gastric-cancer.md`) — created
- **Raw source:** [[what-is-the-second-line-treatment-after-progression-for-advanced-gastric-cancer]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | What is the second-line treatment after progression for advanced gastr...

- **User:** jim.chen
- **Question:** "What is the second-line treatment after progression for advanced gastric cancer?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 3
- **Answer origin:** internet
- **Tokens (Gemini):** 5336
- **Search saved:** [[what-is-the-second-line-treatment-after-progression-for-advanced-gastric-cancer]]

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the managing acquired resistance for triple-negative breast cancer?"
- **Note page:** [[what-is-the-managing-acquired-resistance-for-triple-negative-breast-cancer]] (`wiki/notes/what-is-the-managing-acquired-resistance-for-triple-negative-breast-cancer.md`) — created
- **Raw source:** [[what-is-the-managing-acquired-resistance-for-triple-negative-breast-cancer]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | What is the managing acquired resistance for triple-negative breast ca...

- **User:** jim.chen
- **Question:** "What is the managing acquired resistance for triple-negative breast cancer?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[triple-negative-breast-cancer]], [[were-any-mechanisms-of-resistance-to-daraxonrasib-or-the-mek-inhibitor-based-the]]
- **Gemini calls:** 3
- **Answer origin:** mixed
- **Tokens (Gemini):** 16627
- **Search saved:** [[what-is-the-managing-acquired-resistance-for-triple-negative-breast-cancer]]

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the managing acquired resistance for advanced gastric cancer?"
- **Note page:** [[what-is-the-managing-acquired-resistance-for-advanced-gastric-cancer]] (`wiki/notes/what-is-the-managing-acquired-resistance-for-advanced-gastric-cancer.md`) — created
- **Raw source:** [[what-is-the-managing-acquired-resistance-for-advanced-gastric-cancer]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | What is the managing acquired resistance for advanced gastric cancer?

- **User:** jim.chen
- **Question:** "What is the managing acquired resistance for advanced gastric cancer?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[what-is-the-second-line-treatment-after-progression-for-advanced-gastric-cancer]]
- **Gemini calls:** 3
- **Answer origin:** mixed
- **Tokens (Gemini):** 12175
- **Search saved:** [[what-is-the-managing-acquired-resistance-for-advanced-gastric-cancer]]

## [2026-06-08] auto-ingest-note | searchable internet answer

- **User:** jim.chen
- **Triggering query:** "What is the second-line treatment after progression for metastatic pancreatic cancer?"
- **Note page:** [[what-is-the-second-line-treatment-after-progression-for-metastatic-pancreatic-ca]] (`wiki/notes/what-is-the-second-line-treatment-after-progression-for-metastatic-pancreatic-ca.md`) — created
- **Raw source:** [[what-is-the-second-line-treatment-after-progression-for-metastatic-pancreatic-ca]]
- **Status:** SEARCHABLE + indexed, `auto_generated: true`, unverified. Editable; mark verified to record reviewer + date.

## [2026-06-08] query | What is the second-line treatment after progression for metastatic pan...

- **User:** jim.chen
- **Question:** "What is the second-line treatment after progression for metastatic pancreatic cancer?"
- **Trigger:** Web UI query
- **Wiki pages consulted:** [[with-pmids-what-are-some-updates-with-pancreatic-cancer-that-was-recently-publis]]
- **Gemini calls:** 3
- **Answer origin:** mixed
- **Tokens (Gemini):** 10499
- **Search saved:** [[what-is-the-second-line-treatment-after-progression-for-metastatic-pancreatic-ca]]

## [2026-06-08] verify-note | what-is-the-second-line-treatment-after-progression-for-metastatic-pancreatic-ca

- **User:** jim.chen
- **Page:** [[what-is-the-second-line-treatment-after-progression-for-metastatic-pancreatic-ca]] (`wiki/notes/what-is-the-second-line-treatment-after-progression-for-metastatic-pancreatic-ca.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] verify-note | what-is-the-managing-acquired-resistance-for-advanced-gastric-cancer

- **User:** jim.chen
- **Page:** [[what-is-the-managing-acquired-resistance-for-advanced-gastric-cancer]] (`wiki/notes/what-is-the-managing-acquired-resistance-for-advanced-gastric-cancer.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] verify-note | what-is-the-managing-acquired-resistance-for-triple-negative-breast-cancer

- **User:** jim.chen
- **Page:** [[what-is-the-managing-acquired-resistance-for-triple-negative-breast-cancer]] (`wiki/notes/what-is-the-managing-acquired-resistance-for-triple-negative-breast-cancer.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] verify-note | what-is-the-second-line-treatment-after-progression-for-advanced-gastric-cancer

- **User:** jim.chen
- **Page:** [[what-is-the-second-line-treatment-after-progression-for-advanced-gastric-cancer]] (`wiki/notes/what-is-the-second-line-treatment-after-progression-for-advanced-gastric-cancer.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] verify-note | what-is-the-biomarker-testing-to-guide-therapy-for-multiple-myeloma

- **User:** jim.chen
- **Page:** [[what-is-the-biomarker-testing-to-guide-therapy-for-multiple-myeloma]] (`wiki/notes/what-is-the-biomarker-testing-to-guide-therapy-for-multiple-myeloma.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] verify-note | for-sonrotoclaxs-accelerated-approval-in-relapsedrefractory-mcl-what-are-the-det

- **User:** jim.chen
- **Page:** [[for-sonrotoclaxs-accelerated-approval-in-relapsedrefractory-mcl-what-are-the-det]] (`wiki/notes/for-sonrotoclaxs-accelerated-approval-in-relapsedrefractory-mcl-what-are-the-det.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] verify-note | what-are-the-common-or-dose-limiting-toxicities-observed-with-daraxonrasib-and-t

- **User:** jim.chen
- **Page:** [[what-are-the-common-or-dose-limiting-toxicities-observed-with-daraxonrasib-and-t]] (`wiki/notes/what-are-the-common-or-dose-limiting-toxicities-observed-with-daraxonrasib-and-t.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] verify-note | what-are-the-specific-toxicity-profiles-and-recommended-management-strategies-fo

- **User:** jim.chen
- **Page:** [[what-are-the-specific-toxicity-profiles-and-recommended-management-strategies-fo]] (`wiki/notes/what-are-the-specific-toxicity-profiles-and-recommended-management-strategies-fo.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] verify-note | what-is-the-detailed-safety-and-tolerability-profile-of-sunvozertinib-and-how-do

- **User:** jim.chen
- **Page:** [[what-is-the-detailed-safety-and-tolerability-profile-of-sunvozertinib-and-how-do]] (`wiki/notes/what-is-the-detailed-safety-and-tolerability-profile-of-sunvozertinib-and-how-do.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] verify-note | what-is-the-recommended-sequencing-of-vepdegestrant-relative-to-other-non-endocr

- **User:** jim.chen
- **Page:** [[what-is-the-recommended-sequencing-of-vepdegestrant-relative-to-other-non-endocr]] (`wiki/notes/what-is-the-recommended-sequencing-of-vepdegestrant-relative-to-other-non-endocr.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] verify-note | were-any-mechanisms-of-resistance-to-daraxonrasib-or-the-mek-inhibitor-based-the

- **User:** jim.chen
- **Page:** [[were-any-mechanisms-of-resistance-to-daraxonrasib-or-the-mek-inhibitor-based-the]] (`wiki/notes/were-any-mechanisms-of-resistance-to-daraxonrasib-or-the-mek-inhibitor-based-the.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] verify-note | what-were-the-specific-median-overall-survival-values-hazard-ratios-progression-

- **User:** jim.chen
- **Page:** [[what-were-the-specific-median-overall-survival-values-hazard-ratios-progression-]] (`wiki/notes/what-were-the-specific-median-overall-survival-values-hazard-ratios-progression-.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] verify-note | what-factors-eg-prior-toxicities-comorbidities-specific-disease-characteristics-

- **User:** jim.chen
- **Page:** [[what-factors-eg-prior-toxicities-comorbidities-specific-disease-characteristics-]] (`wiki/notes/what-factors-eg-prior-toxicities-comorbidities-specific-disease-characteristics-.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] verify-note | what-is-car-t-summarize-its-design-and-key-results

- **User:** jim.chen
- **Page:** [[what-is-car-t-summarize-its-design-and-key-results]] (`wiki/notes/what-is-car-t-summarize-its-design-and-key-results.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).

## [2026-06-08] verify-note | are-there-specific-patient-selection-criteria-or-biomarkers-beyond-general-ras-m

- **User:** jim.chen
- **Page:** [[are-there-specific-patient-selection-criteria-or-biomarkers-beyond-general-ras-m]] (`wiki/notes/are-there-specific-patient-selection-criteria-or-biomarkers-beyond-general-ras-m.md`)
- **Action:** marked verified; recorded reviewer (jim.chen) + date (2026-06-08).
