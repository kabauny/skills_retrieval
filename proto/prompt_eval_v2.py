"""
Hardened synthesis-quality eval for the manifest "prompt" field.

Fixes the three weaknesses of v1:
  (i)   INDEPENDENT rubrics — clinically grounded, written fresh (not lifted
        from the prompts), and each tagged scope="in" (something the manifest
        prompt steers toward) or scope="out" (general answer quality the prompt
        does NOT mention). The out-of-scope criteria test for tunnel vision:
        does the prompt improve its focus at the expense of everything else?
  (ii)  DIFFERENT judge model — generator = Pro (production), judge = Flash —
        removes same-model self-preference. Pairwise is run in BOTH orders and
        only counts a win if consistent (kills position bias).
  (iii) MORE + VARIED queries, including off-focus informational and QoL ones
        where the prompt should NOT help (collateral-damage check).

Run:  .venv/bin/python proto/prompt_eval_v2.py
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core  # noqa: E402
from route_proto import load_manifests  # noqa: E402

random.seed(11)

GEN_MODEL = core.MODEL_PRO     # generator = production model
JUDGE_MODEL = core.MODEL_FLASH  # judge = different model (independence)


def C(text, scope):
    return {"text": text, "scope": scope}


EVAL = [
    {
        "q": "65-year-old with HER2+ breast cancer and residual invasive disease after neoadjuvant TCHP — how do you choose adjuvant therapy?",
        "manifest": "adjuvant-her2",
        "rubric": [
            C("Identifies residual invasive disease as the trigger for treatment intensification", "in"),
            C("Compares T-DM1 vs T-DXd including the ILD/pneumonitis trade-off", "in"),
            C("Reaches a clear primary recommendation rather than only listing options", "out"),
            C("Mentions a concrete monitoring/toxicity safeguard relevant to the choice", "out"),
        ],
    },
    {
        "q": "TNBC, pCR after neoadjuvant KEYNOTE-522, but had grade 3 colitis needing infliximab — continue adjuvant pembrolizumab?",
        "manifest": "tnbc-immunotherapy",
        "rubric": [
            C("Treats pCR as a favorable prognostic factor weighing on the decision", "in"),
            C("Weighs irAE recurrence risk on re-challenge given the grade 3 severity", "in"),
            C("Reaches an explicit recommendation (continue vs omit)", "out"),
            C("Invokes shared decision-making / patient values", "out"),
        ],
    },
    {
        "q": "Premenopausal woman, node-negative, intermediate Oncotype recurrence score — chemotherapy or OFS+AI?",
        "manifest": "hr-positive-premenopausal-adjuvant",
        "rubric": [
            C("Anchors to the node-negative genomic trial (TAILORx) population", "in"),
            C("Distinguishes chemo benefit from a chemo-induced ovarian-suppression effect", "in"),
            C("Presents OFS+AI vs chemotherapy as the actual decision for this patient", "out"),
            C("Notes patient age as a modifier of how to read the recurrence score", "out"),
        ],
    },
    {
        "q": "Premenopausal woman, node-positive, low Oncotype recurrence score — does she benefit from chemotherapy?",
        "manifest": "hr-positive-premenopausal-adjuvant",
        "rubric": [
            C("Anchors to the node-positive trial (RxPONDER) rather than TAILORx", "in"),
            C("States premenopausal node-positive patients derived a chemo benefit", "in"),
            C("Gives an actionable recommendation for this specific patient", "out"),
            C("Does not fabricate statistics absent from the provided pages", "out"),
        ],
    },
    {
        "q": "How does ctDNA / MRD status guide adjuvant escalation decisions in breast cancer?",
        "manifest": "ctdna-mrd-breast",
        "rubric": [
            C("Separates molecular (ctDNA) MRD from radiographic residual disease", "in"),
            C("Conveys that MRD utility differs by subtype / clinical context", "in"),
            C("States the current evidence maturity (routine vs investigational)", "out"),
            C("Notes the absence of proven OS benefit from acting on MRD", "out"),
        ],
    },
    # --- off-focus / collateral-damage checks (prompt should NOT help here) ---
    {
        "q": "What is the KEYNOTE-522 regimen and what benefit did it show?",
        "manifest": "tnbc-immunotherapy",  # prompt focus (re-challenge) is irrelevant here
        "rubric": [
            C("Lists the neoadjuvant chemo + pembrolizumab components", "out"),
            C("States the pCR (and/or EFS) benefit observed", "out"),
            C("Notes the adjuvant pembrolizumab continuation phase", "out"),
            C("Stays faithful to the pages without fabricating specifics", "out"),
        ],
    },
    {
        "q": "Counsel a premenopausal patient on fertility and quality-of-life when weighing chemotherapy vs endocrine therapy.",
        "manifest": "hr-positive-premenopausal-adjuvant",  # prompt is trial-focused, not QoL
        "rubric": [
            C("Addresses fertility preservation / ovarian toxicity of chemotherapy", "out"),
            C("Addresses OFS/AI menopausal-symptom and QoL burden", "out"),
            C("Frames it as a shared decision aligned to patient priorities", "out"),
            C("Does not tunnel onto trial data at the expense of the QoL question", "out"),
        ],
    },
    {
        "q": "Is ctDNA testing ready for routine clinical use to guide breast adjuvant therapy?",
        "manifest": "ctdna-mrd-breast",
        "rubric": [
            C("Conveys it is largely investigational / not yet standard of care", "in"),
            C("Balances the promise against current limitations", "out"),
            C("Mentions the lack of proven outcome benefit from MRD-guided action", "out"),
            C("Avoids overstating clinical readiness", "out"),
        ],
    },
]


def synthesize(query: str, pages_text: str, manifest_prompt: str | None) -> str:
    guidance = f"\n## Approach (follow this clinical reasoning)\n{manifest_prompt}\n" if manifest_prompt else ""
    prompt = f"""You are a clinical knowledge assistant. Answer the question using the provided wiki pages. Give a clear, structured answer with [[page]] citations for factual claims.
{guidance}
QUESTION:
{query}

WIKI PAGES:
{pages_text}
"""
    resp = core.get_client().models.generate_content(model=GEN_MODEL, contents=prompt)
    return (resp.text or "").strip()


def grade_rubric(query: str, answer: str, rubric: list[dict]) -> list[bool]:
    crit = "\n".join(f"{i+1}. {c['text']}" for i, c in enumerate(rubric))
    prompt = f"""Grade the ANSWER against each rubric criterion. Be strict: PASS only if the answer clearly does it. Output STRICTLY a JSON array, one object per criterion in order: [{{"n":1,"verdict":"PASS"|"FAIL"}}].

QUESTION:
{query}

ANSWER:
{answer}

RUBRIC:
{crit}
"""
    resp = core.get_client().models.generate_content(model=JUDGE_MODEL, contents=prompt)
    parsed = core._extract_json(resp.text or "")
    out = [False] * len(rubric)
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict) and isinstance(item.get("n"), int):
                i = item["n"] - 1
                if 0 <= i < len(rubric):
                    out[i] = str(item.get("verdict", "")).upper() == "PASS"
    return out


def _pairwise_once(query, ans_a, ans_b, rubric) -> str:
    crit = "\n".join(f"- {c['text']}" for c in rubric)
    prompt = f"""Two answers (A and B) to the same clinical question. Which better satisfies the rubric? Output STRICTLY JSON: {{"winner":"A"|"B"|"tie"}}.

QUESTION:
{query}

RUBRIC:
{crit}

ANSWER A:
{ans_a}

ANSWER B:
{ans_b}
"""
    resp = core.get_client().models.generate_content(model=JUDGE_MODEL, contents=prompt)
    parsed = core._extract_json(resp.text or "")
    w = (parsed or {}).get("winner", "tie") if isinstance(parsed, dict) else "tie"
    return w if w in ("A", "B", "tie") else "tie"


def pairwise_dual(query, base, prom, rubric) -> str:
    """Run both orders; a win counts only if consistent across orders."""
    w1 = _pairwise_once(query, base, prom, rubric)  # A=base, B=prom
    w2 = _pairwise_once(query, prom, base, rubric)  # A=prom, B=base
    r1 = {"A": "base", "B": "prom", "tie": "tie"}[w1]
    r2 = {"A": "prom", "B": "base", "tie": "tie"}[w2]
    return r1 if r1 == r2 else "tie"


def main() -> None:
    manifests = {m["name"]: m for m in load_manifests()}
    agg = {("base", "in"): [0, 0], ("base", "out"): [0, 0],
           ("prom", "in"): [0, 0], ("prom", "out"): [0, 0]}
    wins = {"base": 0, "prom": 0, "tie": 0}

    for item in EVAL:
        q, m, rubric = item["q"], manifests[item["manifest"]], item["rubric"]
        pages = core._load_pages(m["docs"])
        pages_text = "\n\n---\n\n".join(f"## {k}\n{v}" for k, v in pages.items())

        base = synthesize(q, pages_text, None)
        prom = synthesize(q, pages_text, m["prompt"])
        gb = grade_rubric(q, base, rubric)
        gp = grade_rubric(q, prom, rubric)
        w = pairwise_dual(q, base, prom, rubric)
        wins[w] += 1

        print("=" * 96)
        print(f"[{item['manifest']}] {q}")
        for i, c in enumerate(rubric):
            print(f"   {'B+' if gb[i] else 'B-'} {'P+' if gp[i] else 'P-'} [{c['scope']:>3}] {c['text']}")
        bi = sum(gb[i] for i, c in enumerate(rubric) if c["scope"] == "in")
        pi = sum(gp[i] for i, c in enumerate(rubric) if c["scope"] == "in")
        bo = sum(gb[i] for i, c in enumerate(rubric) if c["scope"] == "out")
        po = sum(gp[i] for i, c in enumerate(rubric) if c["scope"] == "out")
        print(f"   in-scope: B {bi} P {pi}  | out-scope: B {bo} P {po}  | dual-order pairwise: {w}")

        for i, c in enumerate(rubric):
            agg[("base", c["scope"])][1] += 1
            agg[("prom", c["scope"])][1] += 1
            agg[("base", c["scope"])][0] += int(gb[i])
            agg[("prom", c["scope"])][0] += int(gp[i])

    def pct(arm, scope):
        h, n = agg[(arm, scope)]
        return f"{h}/{n} ({100*h/n:.0f}%)" if n else "-"

    print("\n" + "=" * 96)
    print(f"AGGREGATE  (generator={GEN_MODEL}, judge={JUDGE_MODEL})")
    print(f"  IN-SCOPE  (prompt's focus):   BASELINE {pct('base','in')}   PROMPT {pct('prom','in')}")
    print(f"  OUT-SCOPE (collateral check): BASELINE {pct('base','out')}   PROMPT {pct('prom','out')}")
    print(f"  Dual-order pairwise wins:  BASELINE {wins['base']}   PROMPT {wins['prom']}   TIE {wins['tie']}")


if __name__ == "__main__":
    main()
