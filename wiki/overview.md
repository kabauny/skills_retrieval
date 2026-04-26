---
title: Overview
---

# Overview

High-level synthesis of the wiki, updated after every ingest.

## Current scope

The wiki covers **three adjuvant breast cancer decision clusters**:

1. **HER2+ residual disease post-neoadjuvant TCHP** (Q3 ingest)
2. **Premenopausal HR+/HER2− intermediate Oncotype DX RS, node-negative** (Q4 ingest)
3. **TNBC pCR after KEYNOTE-522 with severe irAE — adjuvant pembrolizumab continuation vs omission** (Q5 ingest)

Cross-cluster: [[circulating-tumor-dna]] now spans **all three** subtypes, with a unified concept page [[mrd-guided-therapy-escalation]] capturing the shared (still-investigational) status. Same prognostic-not-predictive conclusion across HER2+, HR+/HER2−, and TNBC.

## Synthesis (as of 2026-04-25)

### HER2+ residual disease (Q3 cluster)

[[trastuzumab-emtansine]] is the established adjuvant standard for HER2+ residual invasive disease per [[katherine-trial]] (50% IDFS reduction, sustained at 8.4 years). [[destiny-breast05]] (presented late 2025) demonstrated [[trastuzumab-deruxtecan]] superiority over T-DM1 in the same setting (HR 0.47 for IDFS event; 3-year IDFS 92.4% vs 83.7%; brain-met risk reduction; consistent across HR+ and HR− subsets). FDA breakthrough designation December 2025; **PDUFA July 7, 2026**. The principal trade-off is interstitial lung disease (ILD 9.6% vs 1.6%, including some Grade 5 events).

[[tucatinib]] has no established adjuvant role. [[her2climb-05]] (SABCS 2025, 8.6-month PFS gain) is in **metastatic 1L maintenance** — extending those data to adjuvant residual disease is investigational extrapolation.

The Q3 case (residual disease + MRD+ post-TCHP) sits at the intersection of strong evidence (use a HER2-directed ADC) and absent evidence (whether to escalate further on MRD-positivity alone). See [[adjuvant-her2-positive-breast-cancer]] for the decision skeleton, [[mrd-guided-therapy-escalation]] for why escalation is investigational, and [[residual-disease-vs-mrd-positivity]] for the nested-stratum disambiguation.

### Premenopausal HR+/HER2− intermediate-RS, node-negative (Q4 cluster)

For premenopausal HR+/HER2− node-negative disease with intermediate [[oncotype-dx-recurrence-score]] (RS 16–25) and high-risk clinical features, the decision sits between **adjuvant chemotherapy + endocrine therapy** and **OFS + AI alone**. [[tailorx-trial]] is the directly governing trial — its premenopausal high-risk subgroup showed a small but persistent chemo benefit at 12-year follow-up, especially RS 21–25 (April 2024 NCDB retrospective).

[[rxponder-trial]] addressed a **different population (node-positive, 1–3 nodes)** but spawned the central mechanistic debate: is the premenopausal chemo benefit direct cytotoxicity, or [[chemotherapy-induced-ovarian-suppression]]? The June 2024 [[anti-mullerian-hormone]] post-hoc supports the CIOS hypothesis (low AMH → less chemo benefit). [[ofset-trial]] (NCT05879926) is designed to definitively answer this by giving OFS in both arms — pending readout.

The Q4 patient (39yo, RS 22, Grade 3, 2.5 cm, N0) has three defensible options (chemo+endocrine; OFS+AI; OFS+tamoxifen — the last less appropriate given high-risk features). [[soft-text-trials|SOFT/TEXT]] establish OFS+AI as the strongest non-chemo regimen. NCCN 2025–2026 guidance is permissive ("chemotherapy could be offered"), reflecting genuine equipoise. See [[intermediate-rs-premenopausal-hr-positive-management]] for the decision skeleton and [[node-negative-vs-node-positive-genomic-trial-scoping]] for why TAILORx (not RxPONDER) governs.

### TNBC — pCR with severe irAE during KEYNOTE-522 (Q5 cluster)

For high-risk early [[triple-negative-breast-cancer]], the [[keynote-522]] regimen (neoadjuvant + adjuvant [[pembrolizumab]] + chemotherapy) is current standard. 5-year OS gain HR 0.66 (86.6% vs 81.7% overall, ESMO 2024). But the **pCR-subgroup** OS gap is small (95.1% vs 94.4%, ~0.7% absolute) — most of the regimen's benefit is in non-pCR patients. **The trial wasn't designed to isolate adjuvant benefit after pCR.**

The Q5 case: pCR achieved, but Grade 3 immune-mediated colitis required steroids and [[infliximab]]. Re-challenge real-world data show 28.8% irAE recurrence overall (~23% specifically for colitis/pneumonitis). Adjuvant-phase irAE rate is 18.1% in real-world data. For a patient with small marginal OS benefit and meaningful recurrence risk, the calculus tilts toward omission — but no Phase 3 evidence directly supports that decision. NCCN/ASCO/ESMO recommend the full regimen including 1 year adjuvant pembrolizumab regardless of pCR. See [[adjuvant-pembrolizumab-after-pcr-tnbc]] for the decision skeleton, [[pembrolizumab-rechallenge-after-severe-irae]] for the re-challenge calculus, and [[immune-related-adverse-events]] for general irAE management.

### What spans all three clusters

- [[circulating-tumor-dna]] — prognostic across HER2+, HR+/HER2−, and TNBC; not yet adjuvant-decisional in any. Active prospective work: NCT07136493 (HER2+), DARE/TRACKER/SURVIVE/OFSET (HR+/HER2−), NCT07327021 (TNBC), [[zest-trial]] (closed early — design lesson).
- [[mrd-guided-therapy-escalation]] — the universal framing: ctDNA detection is robustly prognostic, but no Phase 3 has shown that intervening on MRD+ improves outcomes. Same conclusion across all three breast subtypes.
- [[immune-related-adverse-events]] — IO toxicity framework relevant across all checkpoint-inhibitor uses (currently only TNBC in this wiki, but pattern is general).

## What's not yet in the wiki

- **GI cancers** (Q1 MSI-H Stage IIB, Q2 borderline resectable pancreas)
- **Thoracic** (Q6 early-stage EGFR, Q7 PCI in IO-era ES-SCLC)
- **GU/melanoma** (Q8 favorable-risk ccRCC, Q9 adjuvant melanoma IO vs targeted)
- **Heme** (Q10 high-risk smoldering myeloma)
- **Primary literature in `raw/papers/`** — the corpus is still Gemini-synthesized search results only. KATHERINE (NEJM 2019), DESTINY-Breast05 (when published), TAILORx (NEJM 2018/2019, JCO 2022), RxPONDER (NEJM 2021), SOFT/TEXT (NEJM 2014/2018), KEYNOTE-522 (NEJM 2020 + ESMO 2024 OS update) are the highest-priority primary papers to fetch.
