"""
Retrieval A/B — graph on vs off, and "smaller shortlist + graph recall".

For each query x config, measure (no Pro synthesis — we estimate its input):
  - routing tokens : the Flash rerank call (smaller shortlist -> fewer tokens)
  - pages          : how many pages reach synthesis
  - synth-input    : sum of those pages' sizes / 4 (the dominant synthesis cost)
  - total est      : routing + synth-input (+ ~constant output)
  - the pages, so you can eyeball whether C recovers B's relational recall

Configs:
  A  graph OFF      shortlist 12, no expansion        (semantic only)
  B  graph ON       shortlist 12, expand<=3           (current production)
  C  small+graph    shortlist 6,  expand<=4           (cheaper rerank, graph recall)

Run:  .venv/bin/python proto/retrieval_ab.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core  # noqa: E402

QUERIES = [
    ("second-line options for EGFR NSCLC after progression on osimertinib", "relational"),
    ("managing acquired resistance in EGFR-mutant NSCLC", "relational"),
    ("How does ctDNA MRD guide adjuvant decisions across breast cancer subtypes?", "cross-cut"),
    ("first-line treatment for metastatic clear cell renal cell carcinoma", "factual"),
    ("BRAF V600E metastatic colorectal cancer treatment", "factual"),
    ("first-line treatment for diffuse large B-cell lymphoma", "factual"),
]

CONFIGS = [
    ("A graph-OFF  ", dict(shortlist=12, graph=False)),
    ("B graph-ON   ", dict(shortlist=12, graph=True, graph_max_add=3)),
    ("C small+graph", dict(shortlist=6, graph=True, graph_max_add=4)),
]


def synth_input_tokens(stems: list[str]) -> int:
    pages = core._load_pages(stems)
    chars = sum(len(v) for v in pages.values())
    return chars // 4 + 80  # + instructions/question overhead


def main() -> None:
    core.build_page_embeddings()
    agg: dict[str, list[int]] = {name: [0, 0, 0] for name, _ in CONFIGS}  # route, synth, pages
    for q, kind in QUERIES:
        print("=" * 100)
        print(f"[{kind}] {q}")
        base_pages = None
        for name, kw in CONFIGS:
            pages, tok = core.select_relevant_pages_embed(q, **kw)
            si = synth_input_tokens(pages)
            total = tok.total + si
            agg[name][0] += tok.total
            agg[name][1] += si
            agg[name][2] += len(pages)
            extra = ""
            if base_pages is not None:
                missing = [p for p in base_pages if p not in pages]
                gained = [p for p in pages if p not in base_pages]
                if missing:
                    extra += f"  miss-vs-B:{len(missing)}"
                if gained:
                    extra += f"  new-vs-B:{len(gained)}"
            print(f"  {name}  route={tok.total:>5}  synth~={si:>5}  total~={total:>6}  pages={len(pages)}{extra}")
            print(f"               -> {pages}")
            if name.startswith("B"):
                base_pages = pages
        print()

    n = len(QUERIES)
    print("=" * 100)
    print("AGGREGATE (avg per query)")
    for name, _ in CONFIGS:
        r, s, p = agg[name]
        print(f"  {name}  route~={r//n:>5}  synth~={s//n:>5}  total~={(r+s)//n:>6}  pages~={p/n:.1f}")
    print("\n(synth-input is a char/4 estimate of what Pro would read; routing is the real Flash count)")


if __name__ == "__main__":
    main()
