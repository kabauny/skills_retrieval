"""
Synthesis-quality eval for the manifest "prompt" field.

Isolates ONE variable: does injecting a manifest's procedural prompt into
synthesis produce better answers? Both arms get the SAME question and the SAME
retrieved pages (the manifest's docs) — only the prompt differs:

  BASELINE : answer from the pages, generic instructions (today's behavior)
  PROMPT   : same + the manifest's procedural "## Prompt" as reasoning guidance

Scoring (Gemini Pro as judge):
  1. RUBRIC  : each answer graded PASS/FAIL per concrete criterion (blind —
               judge sees one answer, never which arm). Criteria are derived
               from the manifest prompt, so "quality" = did it do the clinical
               reasoning steps.
  2. PAIRWISE: both answers shown A/B in randomized order (blind), judge picks
               which better satisfies the rubric.

Run:  .venv/bin/python proto/prompt_eval.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core  # noqa: E402
from route_proto import load_manifests  # noqa: E402

random.seed(7)  # reproducible A/B ordering


# Queries tied to a manifest, each with a rubric of concrete reasoning steps
# (lifted from that manifest's procedural prompt).
EVAL = [
    {
        "q": "65-year-old with HER2+ breast cancer and residual invasive disease after neoadjuvant TCHP — how do you choose adjuvant therapy?",
        "manifest": "adjuvant-her2",
        "rubric": [
            "Uses residual-disease status as the driver of escalation",
            "Weighs ILD risk (T-DM1) against CNS activity / IDFS magnitude (T-DXd)",
            "Notes the guideline vs PDUFA-timeline gap for adjuvant T-DXd",
            "Cites a pivotal adjuvant trial (KATHERINE or DESTINY-Breast05) for an efficacy claim",
        ],
    },
    {
        "q": "TNBC, pCR after neoadjuvant KEYNOTE-522, but had grade 3 colitis needing infliximab — continue adjuvant pembrolizumab?",
        "manifest": "tnbc-immunotherapy",
        "rubric": [
            "Anchors on pCR as a strong prognostic marker that reshapes risk/benefit",
            "Weighs re-challenge toxicity against the marginal benefit in pCR patients",
            "Accounts for the severity (grade 3, steroid-refractory) of the prior irAE",
            "Flags that this sits in a guideline-gap area",
        ],
    },
    {
        "q": "Premenopausal woman, node-negative, intermediate Oncotype recurrence score — chemotherapy or OFS+AI?",
        "manifest": "hr-positive-premenopausal-adjuvant",
        "rubric": [
            "Uses TAILORx (node-negative) as the governing trial",
            "Does NOT misattribute the decision to RxPONDER (node-positive)",
            "Distinguishes true chemo benefit from a chemo-induced ovarian-suppression (CIOS) effect",
            "Offers OFS+AI as the endocrine-intensification alternative to chemo",
        ],
    },
    {
        "q": "Premenopausal woman, node-positive, low Oncotype recurrence score — does she benefit from chemotherapy?",
        "manifest": "hr-positive-premenopausal-adjuvant",
        "rubric": [
            "Uses RxPONDER (node-positive) as the governing trial",
            "Notes premenopausal node-positive patients DID benefit from chemo in RxPONDER",
            "Distinguishes this from the node-negative TAILORx population",
            "Raises the CIOS interpretation of the premenopausal benefit",
        ],
    },
    {
        "q": "How does ctDNA / MRD status guide adjuvant escalation decisions in breast cancer?",
        "manifest": "ctdna-mrd-breast",
        "rubric": [
            "Distinguishes radiographic residual disease from molecular (MRD) positivity",
            "States that MRD-guided action differs across subtypes",
            "Cites an MRD-enrichment trial (ZEST or OFSET)",
            "Notes where MRD-guided escalation is investigational vs guideline-endorsed",
        ],
    },
]


def synthesize(query: str, pages_text: str, manifest_prompt: str | None) -> str:
    guidance = ""
    if manifest_prompt:
        guidance = f"\n## Approach (follow this clinical reasoning)\n{manifest_prompt}\n"
    prompt = f"""You are a clinical knowledge assistant. Answer the question using the provided wiki pages. Give a clear, structured answer with [[page]] citations for factual claims.
{guidance}
QUESTION:
{query}

WIKI PAGES:
{pages_text}
"""
    resp = core.get_client().models.generate_content(model=core.MODEL_PRO, contents=prompt)
    return (resp.text or "").strip()


def grade_rubric(query: str, answer: str, rubric: list[str]) -> list[bool]:
    crit = "\n".join(f"{i+1}. {c}" for i, c in enumerate(rubric))
    prompt = f"""Grade the ANSWER against each rubric criterion. Be strict: PASS only if the answer clearly does it. Output STRICTLY a JSON array of objects, one per criterion, in order: [{{"n": 1, "verdict": "PASS"|"FAIL"}}].

QUESTION:
{query}

ANSWER:
{answer}

RUBRIC:
{crit}
"""
    resp = core.get_client().models.generate_content(model=core.MODEL_PRO, contents=prompt)
    parsed = core._extract_json(resp.text or "")
    out = [False] * len(rubric)
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict) and isinstance(item.get("n"), int):
                i = item["n"] - 1
                if 0 <= i < len(rubric):
                    out[i] = str(item.get("verdict", "")).upper() == "PASS"
    return out


def pairwise(query: str, ans_a: str, ans_b: str, rubric: list[str]) -> str:
    crit = "\n".join(f"- {c}" for c in rubric)
    prompt = f"""Two answers (A and B) to the same clinical question. Which one better satisfies the rubric of reasoning steps? Output STRICTLY JSON: {{"winner": "A"|"B"|"tie"}}.

QUESTION:
{query}

RUBRIC:
{crit}

ANSWER A:
{ans_a}

ANSWER B:
{ans_b}
"""
    resp = core.get_client().models.generate_content(model=core.MODEL_PRO, contents=prompt)
    parsed = core._extract_json(resp.text or "")
    w = (parsed or {}).get("winner", "tie") if isinstance(parsed, dict) else "tie"
    return w if w in ("A", "B", "tie") else "tie"


def main() -> None:
    manifests = {m["name"]: m for m in load_manifests()}
    totals = {"base": 0, "prompt": 0, "n": 0}
    wins = {"base": 0, "prompt": 0, "tie": 0}

    for item in EVAL:
        q = item["q"]
        m = manifests[item["manifest"]]
        rubric = item["rubric"]
        pages = core._load_pages(m["docs"])
        pages_text = "\n\n---\n\n".join(f"## {k}\n{v}" for k, v in pages.items())

        base = synthesize(q, pages_text, None)
        prom = synthesize(q, pages_text, m["prompt"])

        gb = grade_rubric(q, base, rubric)
        gp = grade_rubric(q, prom, rubric)

        # blind pairwise with randomized order
        flip = random.random() < 0.5
        a, b = (base, prom) if not flip else (prom, base)
        w = pairwise(q, a, b, rubric)
        winner = {"A": ("base" if not flip else "prompt"),
                  "B": ("prompt" if not flip else "base"),
                  "tie": "tie"}[w]
        wins[winner] += 1

        totals["base"] += sum(gb)
        totals["prompt"] += sum(gp)
        totals["n"] += len(rubric)

        print("=" * 96)
        print(f"[{item['manifest']}] {q}")
        for i, c in enumerate(rubric):
            print(f"   {'B:PASS' if gb[i] else 'B:fail'}  {'P:PASS' if gp[i] else 'P:fail'}  | {c}")
        print(f"   rubric: BASELINE {sum(gb)}/{len(rubric)}   PROMPT {sum(gp)}/{len(rubric)}   pairwise winner: {winner}")

    print("\n" + "=" * 96)
    n = totals["n"]
    print("AGGREGATE")
    print(f"  Rubric criteria satisfied:  BASELINE {totals['base']}/{n} ({100*totals['base']/n:.0f}%)   "
          f"PROMPT {totals['prompt']}/{n} ({100*totals['prompt']/n:.0f}%)")
    print(f"  Pairwise wins:  BASELINE {wins['base']}   PROMPT {wins['prompt']}   TIE {wins['tie']}")


if __name__ == "__main__":
    main()
