---
title: "Oncotype DX Recurrence Score"
entity_type: biomarker
aliases: ["Oncotype DX", "21-gene Recurrence Score", "RS", "ODX RS"]
tags: [biomarker/oncotype-dx, "genomics", cancer/breast]
---

# Oncotype DX Recurrence Score

## Overview

A 21-gene RT-PCR-based assay performed on tumor tissue that produces a **Recurrence Score (RS)** ranging from 0 to 100 in HR+/HER2− early breast cancer. The RS estimates 10-year distant recurrence risk on endocrine therapy alone and predicts chemotherapy benefit. Ranges have been operationally defined by the [[tailorx-trial]] (node-negative) and [[rxponder-trial]] (node-positive) thresholds.

## Key facts

- **RS ranges in current operational use** (per [[tailorx-trial]] / [[rxponder-trial]]):
  - **RS 0–10:** very low risk; endocrine therapy alone (no chemo) — confirmed by [[tailorx-trial]].
  - **RS 11–25 ("intermediate"):** the Q4 zone. In **node-negative** ([[tailorx-trial]]), most can skip chemo *except* premenopausal ≤50yr with high-risk clinical features. In **node-positive** ([[rxponder-trial]]), premenopausal women benefit from chemo, postmenopausal do not.
  - **RS ≥26:** chemo recommended.
- **Predictive vs prognostic:** RS is **both** prognostic (recurrence risk on endocrine therapy alone) and predictive (chemotherapy benefit) — the predictive component is what makes it more than a risk score [[premenopausal-intermediate-oncotype-2026]].
- **Q4 patient RS = 22** — sits in the upper end of the intermediate range. Per the April 2024 NCDB retrospective, **RS 21–25 in <50yo node-negative women shows a particular OS benefit signal** for chemotherapy [[premenopausal-intermediate-oncotype-2026]].
- **Limitations:**
  - The RS was developed and primarily validated in postmenopausal women; premenopausal extrapolation is the central tension addressed by [[tailorx-trial]] and [[rxponder-trial]].
  - The intermediate range has the most clinical equipoise — high-risk clinical features (Grade 3, larger tumor, younger age) can shift the decision.

## Related entities

- [[tailorx-trial]] — node-negative validation
- [[rxponder-trial]] — node-positive validation
- [[ofset-trial]] — using RS for OFSET eligibility
- [[hr-positive-her2-negative-breast-cancer]] — disease setting

## Related concepts

- [[intermediate-rs-premenopausal-hr-positive-management]]
- [[node-negative-vs-node-positive-genomic-trial-scoping]]

## Sources

- [[premenopausal-intermediate-oncotype-2026]]
