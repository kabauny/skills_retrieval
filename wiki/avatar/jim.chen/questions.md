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

### [2026-04-26] how-do-you-select-tdxd-based-regimen-destinybreast-11-vs-tch

- **Question:** "How do you select Tdxd based regimen (Destinybreast-11) vs TCHP for neoadjuvant her2+ breast cancer? "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[her2-positive-breast-cancer]], [[trastuzumab-deruxtecan]], [[destiny-breast05]]
- **Gemini calls:** 4
- **Answer origin:** mixed
- **Tokens (Gemini):** 13818
- **MC probe generated:** no

### [2026-04-26] no-destiny-breast-breast-11-is-a-new-publish-data-can-you-ta

- **Question:** "NO destiny breast breast 11 is a new publish data. Can you take a look? "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[destiny-breast05-april-2026-update]], [[destiny-breast05]], [[trastuzumab-deruxtecan]], [[katherine-trial]], [[trastuzumab-emtansine]], [[her2-positive-breast-cancer]], [[adjuvant-her2-positive-breast-cancer]]
- **Gemini calls:** 4
- **Answer origin:** mixed
- **Tokens (Gemini):** 22399
- **MC probe generated:** no

### [2026-04-26] tell-me-about-destiny-breast-11-and-how-it-changes-the-manag

- **Question:** "Tell me about Destiny Breast 11 and how it changes the management of neoadjuvant breast cancer? "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[destiny-breast05-april-2026-update]], [[destiny-breast05]], [[katherine-trial]], [[trastuzumab-deruxtecan]], [[trastuzumab-emtansine]], [[adjuvant-her2-positive-breast-cancer]], [[her2-positive-breast-cancer]], [[residual-disease-vs-mrd-positivity]]
- **Gemini calls:** 4
- **Answer origin:** mixed
- **Tokens (Gemini):** 39012
- **MC probe generated:** no

### [2026-04-26] mrd-testing-for-colon-cancer-if-mrd-is-positive-but-no-evide

- **Question:** "MRD testing for colon  cancer. If MRD is positive, but no evidence of disease, what's the current evidence for starting chemotherapy vs just observe until measurable disease can be detected "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 5
- **Answer origin:** internet
- **Tokens (Gemini):** 12043
- **MC probe generated:** no
- **Search saved:** [[mrd-testing-for-colon-cancer-if-mrd-is-positive-but-no-evidence-of-disease-whats]]
- **Stub pages auto-created:** [[cobra-trial]], [[altair-trial]], [[dynamic-trial]], [[trifluridine-tipiracil]], [[colon-cancer]]

### [2026-04-26] tell-me-about-rxponder-trial-and-results

- **Question:** "Tell me about RxPONDER trial and results  "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[rxponder-trial]], [[premenopausal-intermediate-oncotype-2026]], [[chemotherapy-induced-ovarian-suppression]], [[intermediate-rs-premenopausal-hr-positive-management]], [[node-negative-vs-node-positive-genomic-trial-scoping]]
- **Gemini calls:** 3
- **Answer origin:** wiki
- **Tokens (Gemini):** 13133
- **MC probe generated:** no

### [2026-04-26] tell-me-about-destiny-breast-011

- **Question:** "Tell me about Destiny breast 011 "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[destiny-breast05]], [[destiny-breast05-april-2026-update]], [[trastuzumab-deruxtecan]], [[trastuzumab-emtansine]], [[katherine-trial]], [[her2-positive-breast-cancer]], [[adjuvant-her2-positive-breast-cancer]], [[residual-disease-vs-mrd-positivity]]
- **Gemini calls:** 5
- **Answer origin:** mixed
- **Tokens (Gemini):** 33037
- **MC probe generated:** no
- **Search saved:** [[tell-me-about-destiny-breast-011]]
- **Stub pages auto-created:** [[destiny-breast11]], [[neoadjuvant-treatment]], [[pathologic-complete-response]], [[trastuzumab]], [[pertuzumab]]

### [2026-04-26] what-are-treatment-options-for-second-line-multiple-myeloma-

- **Question:** "What are treatment options for second line multiple myeloma treatment after progressing on dara VRD?"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 5
- **Answer origin:** internet
- **Tokens (Gemini):** 15610
- **MC probe generated:** no
- **Search saved:** [[what-are-treatment-options-for-second-line-multiple-myeloma-treatment-after-prog]]
- **Stub pages auto-created:** [[ciltacabtagene-autoleucel]], [[majestec-3-trial]], [[belantamab-mafodotin]], [[dreamm-7-trial]], [[b-cell-maturation-antigen]]

### [2026-04-26] what-are-some-treatment-options-for-paraganglioma-that-is-no

- **Question:** "What are some treatment options for paraganglioma that is not resectable? "
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** none
- **Gemini calls:** 5
- **Answer origin:** internet
- **Tokens (Gemini):** 15121
- **MC probe generated:** no
- **Search saved:** [[what-are-some-treatment-options-for-paraganglioma-that-is-not-resectable]]
- **Stub pages auto-created:** [[paraganglioma]], [[i-131-iobenguane]], [[peptide-receptor-radionuclide-therapy]], [[belzutifan]], [[cvd-regimen]]

### [2026-04-26] is-there-a-significant-difference-in-ild-for-patient-recievi

- **Question:** "Is there a significant difference in ILD for patient recieving TDXD vs TDM1?"
- **Trigger:** Streamlit UI query
- **Wiki pages consulted:** [[destiny-breast05-april-2026-update]], [[destiny-breast05]], [[katherine-trial]], [[trastuzumab-deruxtecan]], [[trastuzumab-emtansine]]
- **Gemini calls:** 3
- **Answer origin:** wiki
- **Tokens (Gemini):** 12647
- **MC probe generated:** no
