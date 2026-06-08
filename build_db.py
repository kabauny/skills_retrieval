"""
Batch DB builder — ask a list of questions, auto-ingesting each grounded answer
as a searchable, indexed wiki/notes/ page. Runs core directly (no server).

Usage:  .venv/bin/python build_db.py
"""

from __future__ import annotations

import core

USER = "jim.chen"

QUESTIONS = [
    # --- Thoracic / lung ---
    "What is the first-line treatment for EGFR exon 19 deletion metastatic NSCLC?",
    "How do you treat ALK-positive metastatic NSCLC in the first line?",
    "What is the role of adjuvant osimertinib in resected EGFR-mutant NSCLC (ADAURA trial)?",
    "What are the treatment options for KRAS G12C-mutated NSCLC after progression on first-line therapy?",
    "How is PD-L1 expression used to guide first-line immunotherapy in metastatic NSCLC?",
    "What is the standard treatment for limited-stage small cell lung cancer?",
    "What is the role of consolidation durvalumab after chemoradiation in unresectable stage III NSCLC (PACIFIC)?",
    "How do you treat ROS1-rearranged metastatic NSCLC?",
    # --- GI ---
    "What is the first-line treatment for metastatic MSI-high colorectal cancer?",
    "How do you treat HER2-positive metastatic gastric or gastroesophageal cancer?",
    "What is the FOLFIRINOX regimen and its role in pancreatic cancer?",
    "What is the role of adjuvant therapy in resected pancreatic adenocarcinoma?",
    "What is the first-line treatment for advanced hepatocellular carcinoma (atezolizumab plus bevacizumab)?",
    "Which biomarkers should be tested in metastatic colorectal cancer to guide therapy?",
    "What is the first-line treatment for advanced biliary tract cancer / cholangiocarcinoma?",
    "How do you treat BRAF V600E-mutated metastatic colorectal cancer?",
    # --- GU ---
    "What is the first-line treatment for metastatic castration-resistant prostate cancer?",
    "How do you treat metastatic hormone-sensitive prostate cancer with triplet therapy?",
    "What is the role of PARP inhibitors in metastatic prostate cancer with HRR mutations?",
    "What is the first-line treatment for metastatic clear cell renal cell carcinoma?",
    "How do you treat metastatic urothelial carcinoma with enfortumab vedotin plus pembrolizumab?",
    "What is the role of lutetium-177 PSMA-617 (Pluvicto) in metastatic prostate cancer?",
    "What are the preferred first-line IO/TKI combinations for advanced renal cell carcinoma?",
    "How is non-clear-cell renal cell carcinoma treated?",
    # --- Heme ---
    "What is the first-line treatment for diffuse large B-cell lymphoma?",
    "How do you treat relapsed or refractory DLBCL with CAR-T cell therapy?",
    "What is the frontline treatment for chronic lymphocytic leukemia (CLL)?",
    "How do you treat newly diagnosed multiple myeloma in transplant-eligible patients?",
    "What is the role of bispecific antibodies in relapsed/refractory multiple myeloma?",
    "What is the first-line treatment for advanced Hodgkin lymphoma?",
    "How do you treat acute myeloid leukemia with FLT3 mutations?",
    "What is the standard first-line management of follicular lymphoma?",
]


def main() -> None:
    created, covered, failed = 0, 0, 0
    for i, q in enumerate(QUESTIONS):
        try:
            turn, grounded = core.run_query_phase1(q, USER, i)
            if grounded is not None:
                turn, warnings = core.run_query_phase2(
                    turn, grounded, q, USER, auto_ingest_enabled=True
                )
                tag = "NOTE" if turn.note_created else "no-note"
                created += 1 if turn.note_created else 0
                print(f"[{i+1:>2}/{len(QUESTIONS)}] {turn.origin:8} {tag:7} | {q[:60]}")
                for w in warnings:
                    print(f"        warn: {w}")
            else:
                covered += 1
                print(f"[{i+1:>2}/{len(QUESTIONS)}] wiki     covered | {q[:60]}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"[{i+1:>2}/{len(QUESTIONS)}] FAILED  {type(exc).__name__}: {exc} | {q[:50]}")

    print(f"\nDone. notes created: {created}  already-covered: {covered}  failed: {failed}")
    print(f"Remaining index gaps: {len(core.index_gaps())}")


if __name__ == "__main__":
    main()
