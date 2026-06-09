"""
Seed the entity backbone (cancers + common systemic drugs) and WIRE the link
contract, so the whole graph hangs off the principle stems.

Phase 1 of "grow the tree": deterministic, no per-node web search. For each
canonical cancer/drug it ensures an entity page exists and that its required
contract edges are present (drug -> efficacy, adverse-events, >=1 cancer; cancer
-> staging-and-resectability, biomarker-testing, its disease-framework). Existing
pages are NEVER overwritten — we only MERGE missing links into their Related
section. Cancers also get a brief disease-framework principle node.

Run:  .venv/bin/python seed_backbone.py            # apply
      .venv/bin/python seed_backbone.py --dry-run  # report only
"""

from __future__ import annotations

import re
import sys

import core

LINK_RE = re.compile(r"\[\[([^\]|#]+)")
ENT = core.WIKI / "entities"
PRIN = core.PRINCIPLES_DIR

# --- Canonical cancers (25): stem -> (title, aliases, overview, biomarkers, approach)
# `approach` is the disease-framework body: the ordered reasoning spine.
CANCERS: dict[str, dict] = {
    "non-small-cell-lung-cancer": dict(
        title="Non-small cell lung cancer (NSCLC)", aliases=["NSCLC"],
        overview="The most common lung cancer; adenocarcinoma and squamous histologies. Outcome and therapy hinge on stage, driver mutations, and PD-L1.",
        biomarkers=["EGFR, ALK, ROS1, BRAF, KRAS G12C, MET, RET, NTRK, HER2", "PD-L1 (IHC)"],
        approach="Stage and resolve resectability first (including invasive mediastinal staging). Then obtain broad NGS + PD-L1 before systemic therapy — a targetable driver mandates a TKI over chemo-IO. Assess fitness/comorbidity, then weigh regimens.",
        framework_stem="nsclc-approach"),
    "small-cell-lung-cancer": dict(
        title="Small cell lung cancer (SCLC)", aliases=["SCLC"],
        overview="Aggressive neuroendocrine lung cancer; classified limited- vs extensive-stage. High initial chemosensitivity but early relapse.",
        biomarkers=["limited vs extensive stage", "rare actionable drivers"],
        approach="Classify limited- vs extensive-stage. Limited-stage: concurrent chemoradiation +/- consolidation; extensive-stage: platinum-etoposide + immunotherapy. Performance status and CNS involvement drive choices; relapse is the dominant problem."),
    "breast-cancer": dict(
        title="Breast cancer", aliases=["breast carcinoma"],
        overview="Umbrella for biologically distinct subtypes defined by ER/PR and HER2. See subtype pages for therapy specifics.",
        biomarkers=["ER / PR (IHC)", "HER2 (IHC/ISH)", "Ki-67, recurrence scores", "germline BRCA, PIK3CA"],
        approach="Stage and define subtype (ER/PR, HER2) — subtype dictates the entire systemic strategy. Decide curative-intent local therapy + (neo)adjuvant systemic per subtype/stage; in advanced disease, sequence by subtype and prior exposure."),
    "colorectal-cancer": dict(
        title="Colorectal cancer (CRC)", aliases=["colorectal carcinoma", "colon cancer", "rectal cancer"],
        overview="Common GI adenocarcinoma. Management diverges sharply by stage, sidedness, and molecular profile.",
        biomarkers=["MSI/MMR", "RAS (KRAS/NRAS)", "BRAF V600E", "HER2", "sidedness"],
        approach="Stage and assess resectability (including resectability of liver/lung oligometastases — potentially curative). Test MMR/MSI, RAS, BRAF, HER2 before systemic therapy; these gate anti-EGFR, IO, and targeted options. Sidedness informs biologic choice."),
    "gastric-cancer": dict(
        title="Gastric cancer", aliases=["gastric adenocarcinoma", "gastroesophageal cancer", "GEJ cancer"],
        overview="Gastric/GEJ adenocarcinoma. Therapy guided by HER2, PD-L1, MSI, and Claudin 18.2.",
        biomarkers=["HER2", "PD-L1 (CPS)", "MSI/MMR", "Claudin 18.2"],
        approach="Stage and assess resectability (perioperative chemo for resectable; palliative systemic for metastatic). Test HER2, PD-L1 CPS, MSI, CLDN18.2 up front — each opens a distinct first-line combination."),
    "esophageal-cancer": dict(
        title="Esophageal cancer", aliases=["esophageal carcinoma"],
        overview="Squamous cell or adenocarcinoma; histology and location shape therapy.",
        biomarkers=["histology (SCC vs adeno)", "HER2 (adeno)", "PD-L1"],
        approach="Stage and assess resectability; trimodality (neoadjuvant chemoradiation + surgery) for locally advanced. Histology and HER2/PD-L1 status guide systemic and adjuvant immunotherapy choices."),
    "pancreatic-cancer": dict(
        title="Pancreatic cancer", aliases=["pancreatic ductal adenocarcinoma", "PDAC"],
        overview="Pancreatic ductal adenocarcinoma — usually diagnosed late; resectability is the key fork.",
        biomarkers=["germline/somatic BRCA, PALB2", "MSI (rare)", "KRAS"],
        approach="Classify resectable / borderline / locally advanced / metastatic — this defines intent. Multi-agent chemo (FOLFIRINOX or gem/nab-paclitaxel) by fitness; test BRCA/PALB2 for maintenance PARP inhibition."),
    "hepatocellular-carcinoma": dict(
        title="Hepatocellular carcinoma (HCC)", aliases=["HCC", "liver cancer"],
        overview="Primary liver cancer arising in cirrhosis; liver function is as decisive as tumor stage.",
        biomarkers=["underlying liver function (Child-Pugh)", "BCLC stage", "AFP"],
        approach="Stage with BCLC integrating tumor burden, liver function, and performance status. Curative options (resection, ablation, transplant) for early disease; systemic IO-based therapy for advanced — gated by adequate liver function."),
    "cholangiocarcinoma": dict(
        title="Cholangiocarcinoma", aliases=["biliary tract cancer", "bile duct cancer"],
        overview="Biliary tract adenocarcinoma; intra- vs extrahepatic. Notably actionable molecularly.",
        biomarkers=["FGFR2 fusions", "IDH1", "HER2", "BRAF", "MSI"],
        approach="Stage and assess resectability. Obtain NGS early — FGFR2 fusions, IDH1, HER2 each unlock targeted therapy. Gemcitabine/cisplatin + immunotherapy is the systemic backbone."),
    "renal-cell-carcinoma": dict(
        title="Renal cell carcinoma (RCC)", aliases=["RCC", "kidney cancer", "clear cell renal cell carcinoma"],
        overview="Kidney cancer, predominantly clear cell. Risk stratification drives systemic combinations.",
        biomarkers=["clear cell vs non-clear cell histology", "IMDC risk group"],
        approach="Stage; localized disease is often cured surgically. For advanced disease, stratify by IMDC risk and histology, then select IO-IO or IO-TKI combinations; weigh toxicity against benefit."),
    "urothelial-carcinoma": dict(
        title="Urothelial carcinoma", aliases=["bladder cancer", "metastatic urothelial carcinoma"],
        overview="Cancer of the bladder/upper tract. Therapy depends on muscle invasion and metastatic status.",
        biomarkers=["FGFR2/3 alterations", "PD-L1", "HER2", "cisplatin eligibility"],
        approach="Distinguish non-muscle-invasive, muscle-invasive (curative-intent: neoadjuvant chemo + cystectomy), and metastatic. Assess cisplatin eligibility; test FGFR and HER2 for later-line targeted/ADC therapy."),
    "prostate-cancer": dict(
        title="Prostate cancer", aliases=["prostate adenocarcinoma", "mCRPC", "metastatic castration-resistant prostate cancer"],
        overview="Common male adenocarcinoma; androgen-driven. Castration sensitivity and metastatic burden define lines.",
        biomarkers=["castration sensitive vs resistant", "germline/somatic HRR (BRCA)", "MSI", "PSMA"],
        approach="Define localized vs metastatic and castration-sensitive vs -resistant — this sets the line of therapy. Backbone is androgen deprivation + intensification; test HRR/BRCA and MSI for PARP and IO, and PSMA for radioligand therapy."),
    "ovarian-cancer": dict(
        title="Ovarian cancer", aliases=["epithelial ovarian cancer", "high-grade serous carcinoma"],
        overview="Usually high-grade serous; presents advanced. Cytoreduction + platinum + maintenance is the spine.",
        biomarkers=["BRCA1/2 (germline/somatic)", "homologous recombination deficiency (HRD)"],
        approach="Assess for primary vs interval cytoreductive surgery; platinum-based chemo is standard. Test BRCA/HRD to select PARP-inhibitor maintenance — the key determinant of progression-free benefit."),
    "endometrial-cancer": dict(
        title="Endometrial cancer", aliases=["uterine cancer", "endometrial carcinoma"],
        overview="Common gynecologic cancer; molecular classification now guides therapy.",
        biomarkers=["MMR/MSI", "p53", "POLE", "HER2", "ER"],
        approach="Stage surgically. Use molecular classification (MMR/MSI, p53, POLE) for prognosis and to select immunotherapy; advanced disease increasingly uses chemo + IO."),
    "cervical-cancer": dict(
        title="Cervical cancer", aliases=["cervical carcinoma"],
        overview="HPV-driven squamous/adeno cancer. Stage and PD-L1 guide chemoradiation and systemic IO.",
        biomarkers=["PD-L1 (CPS)", "HPV status"],
        approach="Stage to choose curative chemoradiation vs surgery for localized disease. For advanced/recurrent disease, chemo + bevacizumab + immunotherapy by PD-L1 status."),
    "head-and-neck-squamous-cell-carcinoma": dict(
        title="Head and neck squamous cell carcinoma (HNSCC)", aliases=["HNSCC", "head and neck cancer"],
        overview="Squamous cancers of the upper aerodigestive tract; HPV status is prognostic and shapes intensity.",
        biomarkers=["HPV/p16 status", "PD-L1 (CPS)"],
        approach="Stage and define HPV status. Curative-intent surgery or chemoradiation for localized disease; recurrent/metastatic disease uses immunotherapy by PD-L1 CPS +/- chemo."),
    "melanoma": dict(
        title="Melanoma", aliases=["cutaneous melanoma", "malignant melanoma"],
        overview="Aggressive skin cancer; BRAF status and immunotherapy define modern care.",
        biomarkers=["BRAF V600", "stage / ulceration", "LDH"],
        approach="Stage; resect localized disease with adjuvant therapy for high risk. For advanced disease, choose immunotherapy vs BRAF/MEK-targeted therapy by BRAF status, weighing toxicity and pace of disease."),
    "glioblastoma": dict(
        title="Glioblastoma", aliases=["GBM", "glioblastoma multiforme"],
        overview="Most aggressive primary brain tumor. Maximal safe resection + chemoradiation; molecular markers refine prognosis.",
        biomarkers=["MGMT promoter methylation", "IDH status"],
        approach="Maximal safe resection, then chemoradiation with temozolomide. MGMT methylation predicts temozolomide benefit; IDH status reclassifies the tumor. Functional status heavily constrains options."),
    "thyroid-cancer": dict(
        title="Thyroid cancer", aliases=["differentiated thyroid cancer", "medullary thyroid cancer"],
        overview="Mostly indolent differentiated cancers; subsets are highly actionable.",
        biomarkers=["BRAF", "RET fusions/mutations", "NTRK", "RAS"],
        approach="Surgery +/- radioactive iodine for differentiated disease. In RAI-refractory or medullary/anaplastic disease, NGS drives RET/BRAF/NTRK-targeted therapy or multikinase inhibitors."),
    "diffuse-large-b-cell-lymphoma": dict(
        title="Diffuse large B-cell lymphoma (DLBCL)", aliases=["DLBCL"],
        overview="Most common aggressive lymphoma; curable in a majority with frontline immunochemotherapy.",
        biomarkers=["cell of origin (GCB vs ABC)", "double-hit (MYC/BCL2)", "CD20"],
        approach="Stage and assess fitness. Frontline anti-CD20 immunochemotherapy with curative intent; relapsed/refractory disease is risk-stratified toward CAR-T and bispecifics. Manage CRS/ICANS toxicity actively."),
    "follicular-lymphoma": dict(
        title="Follicular lymphoma (FL)", aliases=["FL"],
        overview="Indolent B-cell lymphoma; often a chronic, relapsing course. Watchful waiting is frequently appropriate.",
        biomarkers=["grade", "transformation to aggressive lymphoma", "POD24"],
        approach="Confirm grade and rule out transformation. Asymptomatic low-burden disease often warrants observation; treat by symptoms/burden, then sequence anti-CD20 combinations, lenalidomide, and bispecifics on relapse."),
    "hodgkin-lymphoma": dict(
        title="Hodgkin lymphoma", aliases=["classical Hodgkin lymphoma", "HL"],
        overview="Highly curable lymphoma of young adults; minimizing late toxicity is a central goal.",
        biomarkers=["stage / bulk", "interim PET response", "CD30"],
        approach="Stage and risk-stratify; use PET-adapted therapy to balance cure against late toxicity. Brentuximab vedotin and checkpoint inhibitors anchor advanced and relapsed disease."),
    "chronic-lymphocytic-leukemia": dict(
        title="Chronic lymphocytic leukemia (CLL)", aliases=["CLL"],
        overview="Indolent B-cell leukemia; observation until treatment criteria are met, then targeted oral therapy.",
        biomarkers=["del(17p)/TP53", "IGHV mutation status"],
        approach="Confirm diagnosis and test del(17p)/TP53 and IGHV before treating. Observe asymptomatic disease; at indication, choose BTK inhibitors or venetoclax-based therapy guided by TP53 status and patient factors."),
    "acute-myeloid-leukemia": dict(
        title="Acute myeloid leukemia (AML)", aliases=["AML"],
        overview="Aggressive myeloid leukemia requiring rapid risk stratification; fitness determines intensity.",
        biomarkers=["FLT3", "IDH1/IDH2", "NPM1", "TP53", "cytogenetic risk"],
        approach="Stratify by cytogenetics/molecular markers and fitness urgently. Fit patients: intensive induction +/- targeted add-ons (FLT3, IDH); unfit: hypomethylating agent + venetoclax. Plan transplant by risk."),
    "multiple-myeloma": dict(
        title="Multiple myeloma", aliases=["myeloma", "plasma cell myeloma"],
        overview="Plasma cell malignancy; incurable but highly treatable with sequential combinations.",
        biomarkers=["cytogenetic risk (del17p, t(4;14))", "BCMA"],
        approach="Confirm diagnosis and stage (R-ISS). Induction with triplets/quadruplets, transplant by eligibility, then maintenance; relapse is sequenced through anti-CD38, immunomodulators, proteasome inhibitors, and BCMA-directed therapy."),
}

# --- Common systemic drugs (~100): stem -> (title, drug_class, [cancer stems])
def D(title, cls, cancers):
    return dict(title=title, cls=cls, cancers=cancers)

DRUGS: dict[str, dict] = {
    # Cytotoxic chemotherapy
    "cisplatin": D("Cisplatin", "chemotherapy/platinum", ["non-small-cell-lung-cancer", "urothelial-carcinoma", "head-and-neck-squamous-cell-carcinoma"]),
    "carboplatin": D("Carboplatin", "chemotherapy/platinum", ["non-small-cell-lung-cancer", "ovarian-cancer", "breast-cancer"]),
    "oxaliplatin": D("Oxaliplatin", "chemotherapy/platinum", ["colorectal-cancer", "gastric-cancer", "pancreatic-cancer"]),
    "fluorouracil": D("Fluorouracil (5-FU)", "chemotherapy/antimetabolite", ["colorectal-cancer", "gastric-cancer", "pancreatic-cancer"]),
    "capecitabine": D("Capecitabine", "chemotherapy/antimetabolite", ["colorectal-cancer", "breast-cancer", "gastric-cancer"]),
    "gemcitabine": D("Gemcitabine", "chemotherapy/antimetabolite", ["pancreatic-cancer", "urothelial-carcinoma", "cholangiocarcinoma"]),
    "pemetrexed": D("Pemetrexed", "chemotherapy/antimetabolite", ["non-small-cell-lung-cancer"]),
    "methotrexate": D("Methotrexate", "chemotherapy/antimetabolite", ["diffuse-large-b-cell-lymphoma", "breast-cancer"]),
    "cytarabine": D("Cytarabine", "chemotherapy/antimetabolite", ["acute-myeloid-leukemia"]),
    "paclitaxel": D("Paclitaxel", "chemotherapy/taxane", ["breast-cancer", "ovarian-cancer", "non-small-cell-lung-cancer"]),
    "nab-paclitaxel": D("Nab-paclitaxel", "chemotherapy/taxane", ["pancreatic-cancer", "breast-cancer"]),
    "docetaxel": D("Docetaxel", "chemotherapy/taxane", ["non-small-cell-lung-cancer", "prostate-cancer", "breast-cancer"]),
    "doxorubicin": D("Doxorubicin", "chemotherapy/anthracycline", ["breast-cancer", "diffuse-large-b-cell-lymphoma"]),
    "epirubicin": D("Epirubicin", "chemotherapy/anthracycline", ["breast-cancer", "gastric-cancer"]),
    "cyclophosphamide": D("Cyclophosphamide", "chemotherapy/alkylating", ["breast-cancer", "diffuse-large-b-cell-lymphoma"]),
    "ifosfamide": D("Ifosfamide", "chemotherapy/alkylating", ["cervical-cancer"]),
    "temozolomide": D("Temozolomide", "chemotherapy/alkylating", ["glioblastoma", "melanoma"]),
    "bendamustine": D("Bendamustine", "chemotherapy/alkylating", ["follicular-lymphoma", "chronic-lymphocytic-leukemia"]),
    "irinotecan": D("Irinotecan", "chemotherapy/topoisomerase", ["colorectal-cancer", "pancreatic-cancer"]),
    "etoposide": D("Etoposide", "chemotherapy/topoisomerase", ["small-cell-lung-cancer"]),
    "topotecan": D("Topotecan", "chemotherapy/topoisomerase", ["small-cell-lung-cancer", "ovarian-cancer"]),
    "vinorelbine": D("Vinorelbine", "chemotherapy/vinca", ["non-small-cell-lung-cancer", "breast-cancer"]),
    "vincristine": D("Vincristine", "chemotherapy/vinca", ["diffuse-large-b-cell-lymphoma", "hodgkin-lymphoma"]),
    "eribulin": D("Eribulin", "chemotherapy/microtubule", ["breast-cancer"]),
    "mitomycin": D("Mitomycin C", "chemotherapy/alkylating", ["urothelial-carcinoma"]),
    # EGFR / ALK / lung-driver TKIs
    "osimertinib": D("Osimertinib", "targeted/EGFR-TKI", ["non-small-cell-lung-cancer"]),
    "erlotinib": D("Erlotinib", "targeted/EGFR-TKI", ["non-small-cell-lung-cancer", "pancreatic-cancer"]),
    "gefitinib": D("Gefitinib", "targeted/EGFR-TKI", ["non-small-cell-lung-cancer"]),
    "afatinib": D("Afatinib", "targeted/EGFR-TKI", ["non-small-cell-lung-cancer"]),
    "alectinib": D("Alectinib", "targeted/ALK-TKI", ["non-small-cell-lung-cancer"]),
    "brigatinib": D("Brigatinib", "targeted/ALK-TKI", ["non-small-cell-lung-cancer"]),
    "lorlatinib": D("Lorlatinib", "targeted/ALK-TKI", ["non-small-cell-lung-cancer"]),
    "crizotinib": D("Crizotinib", "targeted/ALK-ROS1-TKI", ["non-small-cell-lung-cancer"]),
    "sotorasib": D("Sotorasib", "targeted/KRAS-G12C", ["non-small-cell-lung-cancer", "colorectal-cancer"]),
    "adagrasib": D("Adagrasib", "targeted/KRAS-G12C", ["non-small-cell-lung-cancer", "colorectal-cancer"]),
    "capmatinib": D("Capmatinib", "targeted/MET", ["non-small-cell-lung-cancer"]),
    "selpercatinib": D("Selpercatinib", "targeted/RET", ["non-small-cell-lung-cancer", "thyroid-cancer"]),
    "larotrectinib": D("Larotrectinib", "targeted/NTRK", ["thyroid-cancer", "non-small-cell-lung-cancer"]),
    "entrectinib": D("Entrectinib", "targeted/NTRK-ROS1", ["non-small-cell-lung-cancer"]),
    # BRAF/MEK
    "dabrafenib": D("Dabrafenib", "targeted/BRAF", ["melanoma", "non-small-cell-lung-cancer", "thyroid-cancer"]),
    "trametinib": D("Trametinib", "targeted/MEK", ["melanoma", "non-small-cell-lung-cancer"]),
    "vemurafenib": D("Vemurafenib", "targeted/BRAF", ["melanoma"]),
    "encorafenib": D("Encorafenib", "targeted/BRAF", ["melanoma", "colorectal-cancer"]),
    "binimetinib": D("Binimetinib", "targeted/MEK", ["melanoma"]),
    # Antiangiogenic / multikinase
    "bevacizumab": D("Bevacizumab", "targeted/anti-VEGF", ["colorectal-cancer", "non-small-cell-lung-cancer", "ovarian-cancer"]),
    "ramucirumab": D("Ramucirumab", "targeted/anti-VEGFR2", ["gastric-cancer", "non-small-cell-lung-cancer", "hepatocellular-carcinoma"]),
    "cabozantinib": D("Cabozantinib", "targeted/multikinase", ["renal-cell-carcinoma", "hepatocellular-carcinoma", "thyroid-cancer"]),
    "lenvatinib": D("Lenvatinib", "targeted/multikinase", ["thyroid-cancer", "hepatocellular-carcinoma", "endometrial-cancer"]),
    "sunitinib": D("Sunitinib", "targeted/multikinase", ["renal-cell-carcinoma"]),
    "pazopanib": D("Pazopanib", "targeted/multikinase", ["renal-cell-carcinoma"]),
    "axitinib": D("Axitinib", "targeted/multikinase", ["renal-cell-carcinoma"]),
    "regorafenib": D("Regorafenib", "targeted/multikinase", ["colorectal-cancer", "hepatocellular-carcinoma"]),
    "sorafenib": D("Sorafenib", "targeted/multikinase", ["hepatocellular-carcinoma", "thyroid-cancer"]),
    "belzutifan": D("Belzutifan", "targeted/HIF-2alpha", ["renal-cell-carcinoma"]),
    # Heme small molecules
    "imatinib": D("Imatinib", "targeted/BCR-ABL", ["acute-myeloid-leukemia"]),
    "ibrutinib": D("Ibrutinib", "targeted/BTK", ["chronic-lymphocytic-leukemia"]),
    "acalabrutinib": D("Acalabrutinib", "targeted/BTK", ["chronic-lymphocytic-leukemia"]),
    "zanubrutinib": D("Zanubrutinib", "targeted/BTK", ["chronic-lymphocytic-leukemia", "follicular-lymphoma"]),
    "venetoclax": D("Venetoclax", "targeted/BCL2", ["chronic-lymphocytic-leukemia", "acute-myeloid-leukemia"]),
    "midostaurin": D("Midostaurin", "targeted/FLT3", ["acute-myeloid-leukemia"]),
    "gilteritinib": D("Gilteritinib", "targeted/FLT3", ["acute-myeloid-leukemia"]),
    "ivosidenib": D("Ivosidenib", "targeted/IDH1", ["acute-myeloid-leukemia", "cholangiocarcinoma"]),
    "enasidenib": D("Enasidenib", "targeted/IDH2", ["acute-myeloid-leukemia"]),
    "azacitidine": D("Azacitidine", "targeted/hypomethylating", ["acute-myeloid-leukemia"]),
    # PARP / CDK4-6 / endocrine pathway
    "olaparib": D("Olaparib", "targeted/PARP", ["ovarian-cancer", "breast-cancer", "prostate-cancer", "pancreatic-cancer"]),
    "niraparib": D("Niraparib", "targeted/PARP", ["ovarian-cancer"]),
    "rucaparib": D("Rucaparib", "targeted/PARP", ["ovarian-cancer", "prostate-cancer"]),
    "palbociclib": D("Palbociclib", "targeted/CDK4-6", ["breast-cancer"]),
    "ribociclib": D("Ribociclib", "targeted/CDK4-6", ["breast-cancer"]),
    "abemaciclib": D("Abemaciclib", "targeted/CDK4-6", ["breast-cancer"]),
    "everolimus": D("Everolimus", "targeted/mTOR", ["breast-cancer", "renal-cell-carcinoma"]),
    "capivasertib": D("Capivasertib", "targeted/AKT", ["breast-cancer"]),
    # FGFR / HER2 small molecule
    "pemigatinib": D("Pemigatinib", "targeted/FGFR", ["cholangiocarcinoma"]),
    "erdafitinib": D("Erdafitinib", "targeted/FGFR", ["urothelial-carcinoma"]),
    "tucatinib": D("Tucatinib", "targeted/HER2-TKI", ["breast-cancer", "colorectal-cancer"]),
    # Monoclonal antibodies (non-IO)
    "rituximab": D("Rituximab", "antibody/anti-CD20", ["diffuse-large-b-cell-lymphoma", "follicular-lymphoma", "chronic-lymphocytic-leukemia"]),
    "obinutuzumab": D("Obinutuzumab", "antibody/anti-CD20", ["follicular-lymphoma", "chronic-lymphocytic-leukemia"]),
    "trastuzumab": D("Trastuzumab", "antibody/anti-HER2", ["breast-cancer", "gastric-cancer"]),
    "pertuzumab": D("Pertuzumab", "antibody/anti-HER2", ["breast-cancer"]),
    "cetuximab": D("Cetuximab", "antibody/anti-EGFR", ["colorectal-cancer", "head-and-neck-squamous-cell-carcinoma"]),
    "panitumumab": D("Panitumumab", "antibody/anti-EGFR", ["colorectal-cancer"]),
    "daratumumab": D("Daratumumab", "antibody/anti-CD38", ["multiple-myeloma"]),
    "isatuximab": D("Isatuximab", "antibody/anti-CD38", ["multiple-myeloma"]),
    # Checkpoint inhibitors (IO)
    "pembrolizumab": D("Pembrolizumab", "IO/anti-PD-1", ["non-small-cell-lung-cancer", "melanoma", "head-and-neck-squamous-cell-carcinoma", "urothelial-carcinoma"]),
    "nivolumab": D("Nivolumab", "IO/anti-PD-1", ["melanoma", "non-small-cell-lung-cancer", "renal-cell-carcinoma"]),
    "cemiplimab": D("Cemiplimab", "IO/anti-PD-1", ["non-small-cell-lung-cancer"]),
    "dostarlimab": D("Dostarlimab", "IO/anti-PD-1", ["endometrial-cancer"]),
    "atezolizumab": D("Atezolizumab", "IO/anti-PD-L1", ["non-small-cell-lung-cancer", "small-cell-lung-cancer", "hepatocellular-carcinoma"]),
    "durvalumab": D("Durvalumab", "IO/anti-PD-L1", ["non-small-cell-lung-cancer", "small-cell-lung-cancer", "cholangiocarcinoma"]),
    "avelumab": D("Avelumab", "IO/anti-PD-L1", ["urothelial-carcinoma"]),
    "ipilimumab": D("Ipilimumab", "IO/anti-CTLA-4", ["melanoma", "renal-cell-carcinoma"]),
    "tremelimumab": D("Tremelimumab", "IO/anti-CTLA-4", ["hepatocellular-carcinoma"]),
    # Antibody-drug conjugates
    "trastuzumab-deruxtecan": D("Trastuzumab deruxtecan", "ADC/anti-HER2", ["breast-cancer", "gastric-cancer", "non-small-cell-lung-cancer"]),
    "trastuzumab-emtansine": D("Trastuzumab emtansine (T-DM1)", "ADC/anti-HER2", ["breast-cancer"]),
    "sacituzumab-govitecan": D("Sacituzumab govitecan", "ADC/anti-Trop-2", ["breast-cancer", "urothelial-carcinoma"]),
    "enfortumab-vedotin": D("Enfortumab vedotin", "ADC/anti-Nectin-4", ["urothelial-carcinoma"]),
    "brentuximab-vedotin": D("Brentuximab vedotin", "ADC/anti-CD30", ["hodgkin-lymphoma", "diffuse-large-b-cell-lymphoma"]),
    "polatuzumab-vedotin": D("Polatuzumab vedotin", "ADC/anti-CD79b", ["diffuse-large-b-cell-lymphoma"]),
    # Bispecifics / cellular
    "blinatumomab": D("Blinatumomab", "bispecific/CD19-CD3", ["diffuse-large-b-cell-lymphoma"]),
    "mosunetuzumab": D("Mosunetuzumab", "bispecific/CD20-CD3", ["follicular-lymphoma"]),
    "epcoritamab": D("Epcoritamab", "bispecific/CD20-CD3", ["diffuse-large-b-cell-lymphoma", "follicular-lymphoma"]),
    "teclistamab": D("Teclistamab", "bispecific/BCMA-CD3", ["multiple-myeloma"]),
    # Endocrine therapy
    "tamoxifen": D("Tamoxifen", "endocrine/SERM", ["breast-cancer"]),
    "letrozole": D("Letrozole", "endocrine/aromatase-inhibitor", ["breast-cancer"]),
    "anastrozole": D("Anastrozole", "endocrine/aromatase-inhibitor", ["breast-cancer"]),
    "exemestane": D("Exemestane", "endocrine/aromatase-inhibitor", ["breast-cancer"]),
    "fulvestrant": D("Fulvestrant", "endocrine/SERD", ["breast-cancer"]),
    "abiraterone": D("Abiraterone", "endocrine/CYP17", ["prostate-cancer"]),
    "enzalutamide": D("Enzalutamide", "endocrine/AR-antagonist", ["prostate-cancer"]),
    "apalutamide": D("Apalutamide", "endocrine/AR-antagonist", ["prostate-cancer"]),
    "darolutamide": D("Darolutamide", "endocrine/AR-antagonist", ["prostate-cancer"]),
    "leuprolide": D("Leuprolide", "endocrine/GnRH-agonist", ["prostate-cancer"]),
}


def _existing_links(text: str) -> set[str]:
    return {m.strip() for m in LINK_RE.findall(text)}


def _merge_related(text: str, needed: list[str]) -> tuple[str, list[str]]:
    """Add any missing [[stems]] to the page's ## Related section, preserving all
    existing content. Returns (new_text, added)."""
    have = _existing_links(text)
    missing = [s for s in needed if s not in have]
    if not missing:
        return text, []
    bullets = "".join(f"- [[{s}]]\n" for s in missing)
    m = re.search(r"^## Related[ \t]*\n", text, flags=re.M)
    if m:
        # skip a single blank line after the heading for tidy insertion
        at = m.end()
        if text[at:at + 1] == "\n":
            at += 1
        new = text[:at] + bullets + text[at:]
    else:
        new = text.rstrip() + "\n\n## Related\n\n" + bullets
    return new, missing


def _aliases_yaml(aliases: list[str]) -> str:
    return "[" + ", ".join(f'"{a}"' for a in aliases) + "]" if aliases else "[]"


def ensure_cancer(stem: str, d: dict, dry: bool) -> dict:
    framework = d.get("framework_stem", f"{stem}-approach")
    needed = ["staging-and-resectability", "biomarker-testing", framework]
    path = ENT / f"{stem}.md"
    action = {}
    if path.exists():
        text = path.read_text(encoding="utf-8")
        new, added = _merge_related(text, needed)
        if added and not dry:
            path.write_text(new, encoding="utf-8")
        action["entity"] = f"merged:{','.join(added)}" if added else "ok"
    else:
        bio = "\n".join(f"- {b}" for b in d["biomarkers"])
        body = (
            f"---\ntitle: \"{d['title']}\"\nentity_type: cancer\n"
            f"aliases: {_aliases_yaml(d['aliases'])}\ntags: [cancer]\n---\n\n"
            f"# {d['title']}\n\n## Overview\n{d['overview']}\n\n"
            f"## Key biomarkers\n{bio}\n\n## Related\n"
            + "".join(f"- [[{s}]]\n" for s in needed)
        )
        if not dry:
            path.write_text(body, encoding="utf-8")
        action["entity"] = "created"
    # disease-framework principle node
    fpath = PRIN / f"{framework}.md"
    if fpath.exists():
        action["framework"] = "ok"
    else:
        fbody = (
            f"---\ntitle: \"Approach to {d['title']} — how to think about it\"\n"
            f"page_type: principle\nprinciple_kind: disease-framework\n"
            f"applies_to: [cancer]\ntags: [principle, disease-framework]\n---\n\n"
            f"# Approach to {d['title']}\n\n"
            f"> **Principle node (disease framework).** How to approach this disease "
            f"before choosing therapy — the order of operations, pointing to the lenses.\n\n"
            f"## How to approach {d['title']}\n{d['approach']}\n\n"
            f"## Related\n- [[staging-and-resectability]]\n- [[biomarker-testing]]\n"
            f"- [[tolerability-and-comorbidity]]\n- [[efficacy]]\n- [[adverse-events]]\n"
        )
        if not dry:
            fpath.write_text(fbody, encoding="utf-8")
        action["framework"] = "created"
    return action


def ensure_drug(stem: str, d: dict, dry: bool) -> str:
    cancers = [c for c in d["cancers"] if c in CANCERS]
    needed = ["efficacy", "adverse-events"] + cancers
    path = ENT / f"{stem}.md"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        new, added = _merge_related(text, needed)
        if added and not dry:
            path.write_text(new, encoding="utf-8")
        return f"merged:{','.join(added)}" if added else "ok"
    cancer_titles = ", ".join(CANCERS[c]["title"] for c in cancers)
    body = (
        f"---\ntitle: \"{d['title']}\"\nentity_type: drug\naliases: []\n"
        f"tags: [{d['cls']}]\n---\n\n# {d['title']}\n\n## Overview\n"
        f"{d['title']} is a {d['cls'].split('/')[-1].replace('-', ' ')} agent "
        f"({d['cls']}). Used in: {cancer_titles}.\n\n## Related\n"
        + "".join(f"- [[{s}]]\n" for s in needed)
    )
    if not dry:
        path.write_text(body, encoding="utf-8")
    return "created"


def main() -> None:
    dry = "--dry-run" in sys.argv
    ENT.mkdir(parents=True, exist_ok=True)
    PRIN.mkdir(parents=True, exist_ok=True)
    c_created = c_merged = f_created = d_created = d_merged = 0
    for stem, d in CANCERS.items():
        a = ensure_cancer(stem, d, dry)
        if a["entity"] == "created":
            c_created += 1
        elif a["entity"].startswith("merged"):
            c_merged += 1
        if a["framework"] == "created":
            f_created += 1
    for stem, d in DRUGS.items():
        r = ensure_drug(stem, d, dry)
        if r == "created":
            d_created += 1
        elif r.startswith("merged"):
            d_merged += 1
    tag = "[dry-run] " if dry else ""
    print(f"{tag}cancers: {c_created} created, {c_merged} merged-links ({len(CANCERS)} total)")
    print(f"{tag}frameworks: {f_created} created")
    print(f"{tag}drugs: {d_created} created, {d_merged} merged-links ({len(DRUGS)} total)")


if __name__ == "__main__":
    main()
