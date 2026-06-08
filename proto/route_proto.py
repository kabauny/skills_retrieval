"""
Two-tier (skills-style) router prototype + A/B harness vs the flat index.

Isolated experiment — reads manifests from proto/routes/, does NOT touch the
live wiki retrieval. Compares, on a hand-labeled query set:

  FLAT      : core.select_relevant_pages (router reads the whole index.md)
  TWO-TIER  : tier1 routes over manifest DESCRIPTIONS -> union of the matched
              manifests' doc refs (overlapping allowed); falls back to FLAT
              when no manifest matches.

Run:  .venv/bin/python proto/route_proto.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core  # noqa: E402

ROUTES_DIR = Path(__file__).resolve().parent / "routes"


# ---------------------------------------------------------------------------
# Manifests
# ---------------------------------------------------------------------------


def load_manifests() -> list[dict]:
    out = []
    for p in sorted(ROUTES_DIR.glob("*.md")):
        text = p.read_text(encoding="utf-8")
        fm, body = core.parse_frontmatter(text)
        docs = re.findall(r"-\s*\[\[([^\]]+)\]\]", body)
        prompt = ""
        m = re.search(r"##\s*Prompt\s*\n(.*?)(?=\n##\s|\Z)", body, re.DOTALL)
        if m:
            prompt = m.group(1).strip()
        out.append({
            "name": fm.get("name", p.stem),
            "description": fm.get("description", ""),
            "when_to_use": fm.get("when_to_use", ""),
            "do_not_use": fm.get("do_not_use", ""),
            "prompt": prompt,
            "docs": docs,
        })
    return out


def tier1_route(query: str, manifests: list[dict]) -> tuple[list[str], int]:
    """Pick relevant manifest names from descriptions only (the cheap tier)."""
    catalog = "\n".join(
        f"- {m['name']}: {m['description']}\n    USE WHEN: {m['when_to_use']}\n    DO NOT USE: {m['do_not_use']}"
        for m in manifests
    )
    prompt = f"""You are a routing layer. Given a clinical question and a list of knowledge "routes" (each with a description, when-to-use, and do-not-use), return the route name(s) whose scope the question falls in.

Return STRICTLY a JSON array of route names. Return [] if NONE clearly apply (the question is outside all routes).

QUESTION:
{query}

ROUTES:
{catalog}
"""
    resp = core.get_client().models.generate_content(model=core.MODEL_FLASH, contents=prompt)
    parsed = core._extract_json(resp.text or "")
    names = [n for n in parsed if isinstance(n, str)] if isinstance(parsed, list) else []
    valid = {m["name"] for m in manifests}
    return [n for n in names if n in valid], len(prompt)


def two_tier_route(query: str, manifests: list[dict]) -> dict:
    fired, tier1_prompt_chars = tier1_route(query, manifests)
    by_name = {m["name"]: m for m in manifests}
    docs: list[str] = []
    for name in fired:
        for d in by_name[name]["docs"]:
            if d not in docs and core._synthesis_page_path(d) is not None:
                docs.append(d)
    used_fallback = False
    if not fired:
        # No manifest matched -> fall back to the flat router (long-tail safety net).
        docs, _ = core.select_relevant_pages(query)
        used_fallback = True
    return {
        "manifests": fired,
        "docs": docs,
        "fallback": used_fallback,
        "tier1_prompt_chars": tier1_prompt_chars,
    }


# ---------------------------------------------------------------------------
# Labeled query set  (gold = pages a good answer should draw on)
# ---------------------------------------------------------------------------

QUERIES = [
    {
        "q": "T-DM1 vs T-DXd for HER2+ residual disease after neoadjuvant therapy",
        "kind": "in-cluster",
        "gold": ["trastuzumab-emtansine", "trastuzumab-deruxtecan", "destiny-breast05",
                 "katherine-trial", "adjuvant-her2-positive-breast-cancer"],
    },
    {
        "q": "Continue adjuvant pembrolizumab after pCR in TNBC if there was grade 3 colitis?",
        "kind": "in-cluster",
        "gold": ["adjuvant-pembrolizumab-after-pcr-tnbc", "keynote-522",
                 "pembrolizumab-rechallenge-after-severe-irae", "immune-related-adverse-events",
                 "triple-negative-breast-cancer"],
    },
    {
        "q": "Premenopausal woman, intermediate Oncotype recurrence score, node-negative — chemo or OFS+AI?",
        "kind": "in-cluster",
        "gold": ["intermediate-rs-premenopausal-hr-positive-management", "oncotype-dx-recurrence-score",
                 "tailorx-trial", "rxponder-trial", "ovarian-function-suppression"],
    },
    {
        "q": "How does ctDNA MRD status inform adjuvant decisions across breast cancer subtypes?",
        "kind": "cross-cutting",
        "gold": ["circulating-tumor-dna", "mrd-guided-therapy-escalation",
                 "residual-disease-vs-mrd-positivity", "zest-trial", "ofset-trial"],
    },
    {
        "q": "What is the role of ctDNA in managing HER2+ residual disease?",
        "kind": "cross-cutting",
        "gold": ["circulating-tumor-dna", "mrd-guided-therapy-escalation",
                 "destiny-breast05", "adjuvant-her2-positive-breast-cancer"],
    },
    {
        "q": "What did the OFSET trial show?",
        "kind": "boundary-overlap",
        "gold": ["ofset-trial", "ovarian-function-suppression", "mrd-guided-therapy-escalation"],
    },
    {
        "q": "Mechanism and ILD risk of trastuzumab deruxtecan",
        "kind": "in-cluster",
        "gold": ["trastuzumab-deruxtecan", "destiny-breast05"],
    },
    {
        "q": "Neoadjuvant therapy and pathologic complete response in breast cancer",
        "kind": "cross-cutting",
        "gold": ["neoadjuvant-treatment", "pathologic-complete-response",
                 "keynote-522", "triple-negative-breast-cancer"],
    },
    {
        "q": "Treatment options for second-line multiple myeloma after progression",
        "kind": "negative-nonbreast",
        "gold": ["belantamab-mafodotin", "dreamm-7-trial", "majestec-3-trial",
                 "ciltacabtagene-autoleucel", "b-cell-maturation-antigen"],
    },
    {
        "q": "Glioblastoma workup, biomarkers, and staging",
        "kind": "negative-nonbreast",
        "gold": ["glioblastoma", "temozolomide"],
    },
]


def pr(retrieved: list[str], gold: list[str]) -> tuple[float, float]:
    R, G = set(retrieved), set(gold)
    hit = len(R & G)
    precision = hit / len(R) if R else 0.0
    recall = hit / len(G) if G else 1.0
    return precision, recall


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------


def main() -> None:
    manifests = load_manifests()
    index_chars = len(core._read_index())
    tier1_chars_est = None

    print(f"Loaded {len(manifests)} manifests; flat index.md = {index_chars} chars\n")
    print("Overlap (pages in >1 manifest):")
    from collections import Counter
    c = Counter(d for m in manifests for d in m["docs"])
    for doc, n in sorted(c.items(), key=lambda x: -x[1]):
        if n > 1:
            print(f"  {doc}: in {n} manifests")
    print()

    agg = {"flat": [0.0, 0.0], "two": [0.0, 0.0]}
    rows = []
    for item in QUERIES:
        q, gold, kind = item["q"], item["gold"], item["kind"]

        flat_pages, _ = core.select_relevant_pages(q)
        fp, fr = pr(flat_pages, gold)

        tt = two_tier_route(q, manifests)
        tp, tr = pr(tt["docs"], gold)
        tier1_chars_est = tt["tier1_prompt_chars"]

        agg["flat"][0] += fp; agg["flat"][1] += fr
        agg["two"][0] += tp; agg["two"][1] += tr

        rows.append({
            "q": q, "kind": kind,
            "flat": flat_pages, "fp": fp, "fr": fr,
            "manifests": tt["manifests"], "fallback": tt["fallback"],
            "two": tt["docs"], "tp": tp, "tr": tr,
        })

    for r in rows:
        print("=" * 100)
        print(f"[{r['kind']}] {r['q']}")
        print(f"  FLAT     P={r['fp']:.2f} R={r['fr']:.2f}  -> {r['flat']}")
        tag = "FALLBACK->flat" if r["fallback"] else f"manifests={r['manifests']}"
        print(f"  TWO-TIER P={r['tp']:.2f} R={r['tr']:.2f}  [{tag}]")
        print(f"           -> {r['two']}")

    n = len(QUERIES)
    print("\n" + "=" * 100)
    print("AGGREGATE (macro-avg over queries)")
    print(f"  FLAT     precision={agg['flat'][0]/n:.2f}  recall={agg['flat'][1]/n:.2f}")
    print(f"  TWO-TIER precision={agg['two'][0]/n:.2f}  recall={agg['two'][1]/n:.2f}")
    print("\nCOST PROXY (router prompt size)")
    print(f"  FLAT tier reads whole index.md : {index_chars} chars  (grows with EVERY page)")
    print(f"  TWO-TIER tier-1 reads manifests: {tier1_chars_est} chars (grows with # of routes, not pages)")


if __name__ == "__main__":
    main()
