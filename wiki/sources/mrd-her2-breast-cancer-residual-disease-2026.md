---
title: "Search: MRD-positive HR+/HER2+ breast cancer with residual disease post-neoadjuvant TCHP — adjuvant T-DM1 vs T-DXd vs tucatinib (2025–2026)"
authors: ["Gemini grounded search"]
year: 2026
source_type: search
journal: "n/a — Gemini synthesis of 28 grounded sources"
tags: [cancer/breast, biomarker/HER2, biomarker/ctDNA, therapy/ADC, therapy/targeted, "guideline/NCCN", "guideline/ASCO", "guideline/ESMO", search-sourced]
date_ingested: 2026-04-24
raw_file: "raw/searches/management-of-ctdna-mrd-positive-hrher2-breast-cancer-with-residual-disease-post.md"
gemini_tokens_total: 5416
---

# Source summary: MRD+ HER2+ breast cancer adjuvant management (2025–2026)

## Summary

A Gemini grounded search synthesizing 28 sources (NCCN, ASCO, ESMO, peer-reviewed PMC, oncology trade press, sponsor press releases) on adjuvant management of HR+/HER2+ early breast cancer with residual disease after neoadjuvant TCHP, specifically considering ctDNA MRD-positivity. T-DM1 remains the on-label standard per [[katherine-trial]]. T-DXd is poised to supersede it based on [[destiny-breast05]] (53% IDFS reduction vs T-DM1; PDUFA July 7, 2026). Tucatinib is metastatic-only; [[her2climb-05]] does not extend to adjuvant use. ctDNA MRD-guided escalation remains investigational — no current NCCN/ASCO/ESMO recommendation, and the [[zest-trial]] closed early.

## Key findings

- **Adjuvant T-DM1 is the current standard** for HER2+ residual disease after neoadjuvant therapy, per [[katherine-trial]] (50% IDFS reduction vs trastuzumab; 8.4-year follow-up confirmed sustained IDFS and OS benefit). Category 1 NCCN, supported by ASCO and ESMO guidelines.
- **T-DXd is the emerging standard.** [[destiny-breast05]] (Phase 3, presented ESMO 2025 and SABCS 2025): T-DXd vs T-DM1 in high-risk HER2+ residual disease post-neoadjuvant. HR 0.47 for IDFS event (53% risk reduction). 3-year IDFS 92.4% (T-DXd) vs 83.7% (T-DM1). Benefit consistent across HR+ and HR− subsets. Reduced brain metastasis risk. OS trend favorable but immature.
- **T-DXd safety signal: ILD/pneumonitis** — 9.6% (T-DXd) vs 1.6% (T-DM1), including some Grade 5 events. This is the principal trade-off in the supersession decision.
- **Regulatory path for T-DXd in this setting:** FDA breakthrough therapy designation December 2025; sBLA priority review granted, **PDUFA target action date July 7, 2026**. Until then T-DXd in this indication is **investigational/off-label**.
- **Tucatinib has no established adjuvant role.** HER2CLIMB ([[tucatinib]] + trastuzumab + capecitabine) is metastatic-only. [[her2climb-05]] (SABCS 2025) tested tucatinib added to trastuzumab + pertuzumab as 1L *maintenance* in *metastatic* HER2+ — 8.6-month PFS benefit. Adjuvant use in MRD+ residual disease post-TCHP would be **investigational and off-label**, with no dedicated trial.
- **ctDNA MRD-guided therapy escalation is investigational.** [[circulating-tumor-dna]] detection is robustly prognostic for recurrence, but no Phase 3 trial has shown that intervening on MRD-positivity improves outcomes. NCCN, ASCO, and ESMO **do not recommend routine ctDNA MRD testing to guide adjuvant escalation** in HR+/HER2+ disease as of early 2026.
- **The [[zest-trial]] closed early** due to randomization difficulties — too few MRD+ events in the eligible population. Lesson: future MRD-guided adjuvant trials need higher-risk enrichment (which the Q3 case represents — residual disease *and* MRD+).
- **NCT07136493** is an ongoing prospective trial of ctDNA MRD detection in early-stage breast cancer (including HER2+) intended to associate ctDNA detectability with recurrence-free survival.

## Entities mentioned

Drugs: [[trastuzumab-emtansine]], [[trastuzumab-deruxtecan]], [[tucatinib]]
Trials: [[katherine-trial]], [[destiny-breast05]], [[her2climb-05]], [[zest-trial]]
Cancer / biomarkers: [[her2-positive-breast-cancer]], [[circulating-tumor-dna]]

## Relevance

This source establishes the evidence base for the foundational HER2+ early-breast-cancer adjuvant decision node in the wiki. It will be the primary citation for [[adjuvant-her2-positive-breast-cancer]] and [[mrd-guided-therapy-escalation]]. The Q3 case framing (residual disease *and* MRD+) motivates the [[residual-disease-vs-mrd-positivity]] concept page — these are nested risk strata, not synonyms.

## Limitations / caveats

- **Secondary source.** Gemini synthesis of web-grounded sources, not primary literature. Primary citations (KATHERINE, DESTINY-Breast05) should be fetched into `raw/papers/` for definitive provenance. Tag any claim that cannot be traced to a specific primary source as `[search-sourced]`.
- **Guideline lag.** Search assumes NCCN/ASCO/ESMO will incorporate DESTINY-Breast05 imminently but does not confirm this has happened. Re-verify in mid-2026 after expected guideline updates.
- **Mild conflation in the search.** The Gemini response treats "residual disease" and "MRD-positivity" as overlapping rather than nested. This wiki disambiguates them on the [[residual-disease-vs-mrd-positivity]] concept page.
- **Sponsor-press citations.** Several DESTINY-Breast05 claims trace back to AstraZeneca/Daiichi Sankyo press releases (Sept 2025). The published primary readout should be preferred when available.
- **OS data immature** for DESTINY-Breast05 — IDFS benefit is robust, OS benefit is a favorable trend only.
