---
title: "Search: DESTINY-Breast05 + KATHERINE adjuvant HER2+ status — April 2026 update"
authors: ["Gemini grounded search"]
year: 2026
source_type: search
journal: "n/a — Gemini synthesis of 18 grounded sources, including FDA/sponsor announcements + Jan 2025 KATHERINE long-term update"
tags: [cancer/breast, biomarker/HER2, therapy/ADC, "guideline/NCCN", search-sourced]
date_ingested: 2026-04-26
raw_file: "raw/searches/current-fda-approval-status-and-nccn-asco-esmo-2026-guideline-incorporation-of-t.md"
gemini_tokens_total: 4546
supersession_role: true
---

# Source summary: DESTINY-Breast05 + KATHERINE adjuvant HER2+ status (April 2026 update)

## Summary

A targeted Gemini grounded search run to test the **supersede operation** in the wiki. Confirms several existing claims (FDA status, NCCN/ASCO/ESMO not-yet-updated) and **supersedes specific claims** with newer or more precise data: DESTINY-Breast05 brain metastasis quantification (HR 0.64), DESTINY-Breast05 ILD Grade 5 asymmetry (2 vs 0), DESTINY-Breast05 NEJM primary publication reference, and KATHERINE 7-year IDFS/OS quantification from the January 2025 long-term update.

## Confirmed (no supersession)

- **FDA status:** T-DXd in adjuvant HER2+ residual disease remains investigational. sBLA priority review March 9, 2026. **PDUFA target action date July 7, 2026** — unchanged.
- **NCCN, ASCO, ESMO formal guideline incorporation:** **not yet updated** to include T-DXd as preferred adjuvant for HER2+ residual disease as of April 2026. NCCN Breast Cancer Guidelines v1.2026 do not yet show this. ASCO has flagged "Medical Therapy for Stage I–III HER2-Positive Breast Cancer" as a 2025–2026 update priority. ESMO living guidelines still reference T-DXd for metastatic / HER2-low only.
- **DESTINY-Breast05 IDFS:** HR 0.47 (53% reduction); 3-year IDFS 92.4% (T-DXd) vs 83.7% (T-DM1). Subgroup consistency. Unchanged.
- **OS data for DESTINY-Breast05:** still immature; secondary endpoint, not yet specifically reported beyond the favorable trend noted in late 2025.

## Supersedes (claims rewritten elsewhere in the wiki)

1. **DESTINY-Breast05 CNS endpoint, quantified.** Brain metastasis-free interval **HR 0.64 (95% CI 0.35–1.17), 36% reduction** with T-DXd vs T-DM1. Reported in March 2026 sBLA-priority-review press releases. Supersedes the prior qualitative phrasing "clinically meaningful reduction in brain metastasis risk" on [[trastuzumab-deruxtecan]] and [[destiny-breast05]].

2. **DESTINY-Breast05 ILD specifics.** ILD 9.6% in T-DXd arm **including 2 Grade 5 events**; 1.6% in T-DM1 arm with **0 Grade 5 events**. Trial protocol incorporated **proactive serial low-dose chest CT monitoring** for ILD detection. **No increased ILD risk with concurrent radiotherapy.** Supersedes prior phrasing "some Grade 5 events" and adds protocol/monitoring detail.

3. **DESTINY-Breast05 primary publication reference.** Trial results published in The New England Journal of Medicine following the ESMO 2025 oral presentation. Supersedes the prior wiki citation chain that depended on press releases and ESMO oral references.

4. **KATHERINE long-term follow-up quantification.** January 2025 published update at 8.4-year median follow-up: **7-year IDFS 80.8% (T-DM1) vs 67.1% (trastuzumab); 7-year OS 89.1% vs 84.4%**. Supersedes the prior qualitative claim "sustained IDFS benefit and improved OS" on [[katherine-trial]].

## Entities mentioned

- [[trastuzumab-deruxtecan]], [[trastuzumab-emtansine]] — drugs subject to supersession
- [[destiny-breast05]], [[katherine-trial]] — trials subject to supersession
- [[her2-positive-breast-cancer]] — disease setting

## Relevance

This source exists primarily to **test the supersede operation**. It confirms the time-sensitive claims that have not changed and identifies four specific claims that have been quantified or updated since our original Q3 ingest. Future ingests with similar role would naturally retire to a "previously authoritative" status once their specific superseded claims have been overtaken by yet-newer sources.

## Limitations / caveats

- **Secondary source (Gemini synthesis).** Primary references should be fetched into `raw/papers/` — particularly the DESTINY-Breast05 NEJM publication and the KATHERINE January 2025 long-term update.
- **Brain metastasis HR 95% CI 0.35–1.17 crosses 1.0** — directional finding consistent with T-DXd CNS activity but not statistically definitive at the conventional threshold. The "36% reduction" framing should be presented with this caveat.
- **Sponsor press citations** (Daiichi Sankyo, AstraZeneca) for several supersession items — primary publication preferred when available.
- **NEJM publication referenced but not directly cited with DOI/issue** — the search did not retrieve the specific publication metadata. Should be confirmed by fetching the actual NEJM paper.
