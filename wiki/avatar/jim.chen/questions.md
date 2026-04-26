---
user: jim.chen
title: "Questions — jim.chen"
---

# Questions — jim.chen

A curated, categorized log of queries posed by `jim.chen`. Updated on every non-trivial Query per the schema.

## Breast cancer — HER2+ adjuvant

### [2026-04-24] ILD trade-off T-DM1 vs T-DXd adjuvantly

- **Question:** "What's the ILD trade-off in switching from T-DM1 to T-DXd adjuvantly?"
- **Trigger:** Pipeline test following Q3 ingest — probing whether the wiki can answer a Q3-adjacent question without a Gemini call.
- **Wiki pages consulted:** [[trastuzumab-deruxtecan]], [[trastuzumab-emtansine]], [[destiny-breast05]], [[adjuvant-her2-positive-breast-cancer]]
- **KG tools used:** none
- **Gemini calls:** 0 — *justified*
- **Answer origin:** wiki
- **Tokens (Gemini):** 0
- **Filed back:** none

### [2026-04-26] ctDNA-MRD across breast cancer subtypes (cross-cluster)

- **Question:** "How does ctDNA-MRD status currently inform adjuvant decisions across breast cancer subtypes?"
- **Trigger:** Post-Q4 cross-cluster retrieval test — probing whether the wiki spans both clusters coherently without re-searching.
- **Wiki pages consulted:** [[circulating-tumor-dna]], [[mrd-guided-therapy-escalation]], [[zest-trial]], [[ofset-trial]], [[residual-disease-vs-mrd-positivity]]
- **KG tools used:** none
- **Gemini calls:** 0 — *justified*
- **Answer origin:** wiki (cross-cluster)
- **Tokens (Gemini):** 0
- **Filed back:** none (already captured in [[mrd-guided-therapy-escalation]] + updated [[circulating-tumor-dna]])

## TNBC adjuvant management

### [2026-04-26] Q5 TNBC pCR adjuvant pembrolizumab decision

- **Question:** "TNBC patient achieves pCR after neoadjuvant KEYNOTE-522 but had Grade 3 immune-mediated colitis requiring steroids + infliximab. Re-challenge with adjuvant pembrolizumab to maximize curative intent, or omit knowing pCR portends excellent prognosis?"
- **Trigger:** First decision-capture exercise per the planned workflow. Q5 case from the test battery.
- **Wiki pages consulted:** [[adjuvant-pembrolizumab-after-pcr-tnbc]], [[keynote-522]], [[pembrolizumab-rechallenge-after-severe-irae]], [[immune-related-adverse-events]], [[pembrolizumab]], [[infliximab]], [[triple-negative-breast-cancer]]
- **KG tools used:** none
- **Gemini calls:** 0 — *justified* (decision-capture mode; wiki had full option set + evidence + decision skeleton)
- **Answer origin:** wiki (decision-capture mode)
- **Tokens (Gemini):** 0
- **Filed back:** [[decisions#2026-04-26-q5-tnbc-pcr-grade-3-colitis-adjuvant-pembrolizumab-omission]] — decision captured: Option A (omit), confidence moderate
