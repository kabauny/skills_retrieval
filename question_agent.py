"""
Question agent (proposer) — completes the Ingest/Query/EXPAND triad.

Reads what the wiki has generated and proposes NEW questions to grow it, via
three strategies, then DEDUPS each candidate against existing pages using the
embedding index (so it never re-asks what's already covered) and ranks by how
big the gap is. Propose-only: prints a reviewed list; nothing is ingested.

  1. referential — named trials/drugs mentioned in notes but lacking a page
  2. depth       — per-note LLM follow-ups (next-line, resistance, toxicity…)
  3. coverage    — cancer × line/biomarker grid cells with no page

Usage:  .venv/bin/python question_agent.py
        .venv/bin/python question_agent.py --depth-sample 8 --top 25
"""

from __future__ import annotations

import json
import re
import sys

import core

# A candidate is "already covered" only if it embeds VERY close to a page. Set
# high on purpose: same-domain sub-topics (first- vs second-line) embed ~0.7, so
# a low bar wrongly drops real gaps. A human reviews the list — err toward
# proposing. Override with --covered.
COVERED = 0.82
DEPTH_SAMPLE = 10
TOP = 30

AXES = [
    "first-line treatment",
    "second-line treatment after progression",
    "biomarker testing to guide therapy",
    "managing acquired resistance",
]
CANCERS = [
    "metastatic NSCLC", "small cell lung cancer", "metastatic colorectal cancer",
    "advanced gastric cancer", "metastatic pancreatic cancer", "hepatocellular carcinoma",
    "biliary tract cancer", "metastatic castration-resistant prostate cancer",
    "advanced renal cell carcinoma", "metastatic urothelial carcinoma",
    "diffuse large B-cell lymphoma", "chronic lymphocytic leukemia",
    "multiple myeloma", "Hodgkin lymphoma", "follicular lymphoma",
    "acute myeloid leukemia", "triple-negative breast cancer",
    "HER2-positive breast cancer", "HR-positive breast cancer",
]

# trial-name shapes: hyphenated (KEYNOTE-522, DESTINY-Breast05, CheckMate-9ER) or
# all-caps tokens (PACIFIC, ADAURA, MARIPOSA) — minus common non-trial acronyms.
_TRIAL_RE = re.compile(r"\b([A-Za-z][A-Za-z]{2,}-[A-Za-z0-9]+|[A-Z]{4,}\d*)\b")
_STOP = {
    "NCCN", "ASCO", "ESMO", "NSCLC", "SCLC", "TNBC", "DLBCL", "CLL", "AML", "ALL",
    "MZL", "PD-L1", "PD-1", "CTLA-4", "HER2", "EGFR", "ALK", "ROS1", "KRAS", "BRAF",
    "MSI", "MMR", "DMMR", "CTDNA", "MRD", "BCMA", "HRR", "PARP", "IMDC", "FOLFIRINOX",
    "FOLFOX", "FOLFIRI", "CAPOX", "FDA", "PFS", "OS", "IDFS", "EFS", "DFS", "ORR",
    "CNS", "ILD", "QOL", "OFS", "TKI", "ADC", "CAR", "RCC", "GEJ", "PSMA", "AKT",
    "PI3K", "MTOR", "VEGF", "TROP2", "FLT3", "IDH1", "IDH2", "NPM1",
}


def _existing_keys() -> set[str]:
    keys: set[str] = set()
    for p in core.list_wiki_pages():
        keys.add(p.stem.replace("-", " ").lower())
        try:
            fm, _ = core.parse_frontmatter(p.read_text(encoding="utf-8"))
        except OSError:
            continue
        t = (fm.get("title", "") or "").strip().strip('"').strip("'").lower()
        if t:
            keys.add(t)
        for a in re.findall(r'"([^"]+)"', fm.get("aliases", "") or ""):
            keys.add(a.lower())
    return keys


def harvest_referential(existing: set[str]) -> list[dict]:
    notes = list(core.NOTES_DIR.glob("*.md"))
    freq: dict[str, int] = {}
    for p in notes:
        body = p.read_text(encoding="utf-8")
        for tok in _TRIAL_RE.findall(body):
            if tok.upper() in _STOP or tok.lower() in existing:
                continue
            if tok.replace("-", " ").lower() in existing:
                continue
            freq[tok] = freq.get(tok, 0) + 1
    # one LLM pass to keep only real named trials/drugs (drops regex noise)
    cands = sorted(freq, key=lambda t: -freq[t])[:40]
    if not cands:
        return []
    prompt = (
        "From this list of tokens pulled from oncology notes, return STRICTLY a JSON "
        "array of the ones that are genuine named clinical trials or drugs worth their "
        "own wiki page. Drop abbreviations, lab terms, and noise.\n\n" + ", ".join(cands)
    )
    resp = core.get_client().models.generate_content(model=core.MODEL_FLASH, contents=prompt)
    keep = core._extract_json(resp.text or "")
    keep = [k for k in keep if isinstance(k, str)] if isinstance(keep, list) else cands
    out = []
    for name in keep:
        out.append({
            "q": f"What is {name}? Summarize its design and key results.",
            "strategy": "referential",
            "reason": f"'{name}' is referenced in {freq.get(name, 1)} note(s) but has no page",
        })
    return out


def harvest_depth(sample: int) -> list[dict]:
    notes = sorted(core.NOTES_DIR.glob("*.md"), key=lambda x: -x.stat().st_mtime)[:sample]
    out = []
    for p in notes:
        fm, body = core.parse_frontmatter(p.read_text(encoding="utf-8"))
        title = (fm.get("title", p.stem) or p.stem).strip().strip('"')
        prompt = (
            "Given this clinical note, list up to 3 SPECIFIC follow-up questions a "
            "clinician would ask that the note does NOT already answer (e.g. next-line "
            "therapy, resistance, toxicity management, sequencing, special populations). "
            'Return STRICTLY a JSON array of question strings.\n\nNOTE: ' + title + "\n\n" + body[:1500]
        )
        resp = core.get_client().models.generate_content(model=core.MODEL_FLASH, contents=prompt)
        qs = core._extract_json(resp.text or "")
        if isinstance(qs, list):
            for q in qs[:3]:
                if isinstance(q, str) and len(q) > 12:
                    out.append({"q": q.strip(), "strategy": "depth", "reason": f"follow-up from [[{p.stem}]]"})
    return out


def harvest_coverage() -> list[dict]:
    out = []
    for c in CANCERS:
        for ax in AXES:
            out.append({
                "q": f"What is the {ax} for {c}?",
                "strategy": "coverage",
                "reason": f"grid cell: {c} × {ax}",
            })
    return out


def dedup_and_rank(cands: list[dict], top: int, covered: float = COVERED) -> tuple[list[dict], int]:
    core.build_page_embeddings()
    cache = core._embed_cache_load()
    page_vecs = list(cache.items())
    # de-dupe identical questions first
    seen, uniq = set(), []
    for c in cands:
        k = c["q"].lower()
        if k not in seen:
            seen.add(k)
            uniq.append(c)
    # embed candidates in batches, score max-cosine vs existing pages
    qtexts = [c["q"] for c in uniq]
    vecs = []
    for i in range(0, len(qtexts), 100):
        vecs.extend(core._embed(qtexts[i:i + 100], "RETRIEVAL_QUERY"))
    kept, dropped = [], 0
    for c, v in zip(uniq, vecs):
        best, best_stem = 0.0, None
        for stem, d in page_vecs:
            s = core._cosine(v, d["vec"])
            if s > best:
                best, best_stem = s, stem
        if best >= covered:
            dropped += 1
            continue  # already covered — drop
        c["coverage"] = round(best, 3)
        c["nearest"] = best_stem
        kept.append(c)
    kept.sort(key=lambda c: c["coverage"])  # biggest gaps (lowest similarity) first
    return kept[:top], dropped


_REF_COUNT_RE = re.compile(r"referenced in (\d+) note")


def _cohesion(node: str, adj: dict[str, set]) -> float:
    """How tightly a node's neighbor-pages cluster: fraction of neighbor pairs
    that share at least one OTHER hub. ~1.0 for a focused hub (osimertinib — all
    EGFR notes), low for a diffuse bridge whose neighbors share nothing else."""
    nbrs = list(adj.get(node, ()))
    if len(nbrs) < 2:
        return 1.0
    others = {n: (adj.get(n, set()) - {node}) for n in nbrs}
    pairs = shared = 0
    for i in range(len(nbrs)):
        for j in range(i + 1, len(nbrs)):
            pairs += 1
            if others[nbrs[i]] & others[nbrs[j]]:
                shared += 1
    return shared / pairs if pairs else 1.0


def _payoff(node: str, adj: dict[str, set]) -> int:
    """Graph-growth payoff = reach x focus = degree x cohesion^2. The squared
    cohesion strongly down-weights diffuse generic hubs (pembrolizumab spanning
    cancers) vs focused ones (osimertinib), per the retrieval A/B lesson."""
    deg = len(adj.get(node, ()))
    return round(deg * _cohesion(node, adj) ** 2)


def _connectivity(question: str, reason: str, adj: dict[str, set]) -> int:
    """How much answering this question would strengthen the graph — reach x
    focus of the entity it documents. Falls back to the referential note-count
    if the entity isn't a graph node yet."""
    cands: set[str] = set()
    m = re.search(r"'([^']+)'", reason)  # referential names its entity in quotes
    if m:
        cands.add(core.kebab(m.group(1)))
    text = f"{question} {reason}".lower()
    for node in adj:
        name = node.replace("-", " ")
        if len(name) >= 5 and name in text:
            cands.add(node)
    in_graph = [c for c in cands if c in adj]
    if in_graph:
        return max(_payoff(c, adj) for c in in_graph)
    rm = _REF_COUNT_RE.search(reason)  # entity not a node yet — best available
    return int(rm.group(1)) if rm else 0


def propose(depth_sample: int = DEPTH_SAMPLE, top: int = TOP, covered: float = COVERED) -> list[dict]:
    """Harvest candidates (all 3 strategies), dedup vs existing pages via
    embeddings, rank by gap size, and score connectivity payoff. Returns the
    ranked list of {q, strategy, reason, coverage, nearest, connectivity}."""
    existing = _existing_keys()
    cands = harvest_referential(existing) + harvest_depth(depth_sample) + harvest_coverage()
    ranked, _ = dedup_and_rank(cands, top, covered)
    adj = core.build_link_graph()
    for item in ranked:
        item["connectivity"] = _connectivity(item["q"], item.get("reason", ""), adj)
    return ranked


def main() -> None:
    args = sys.argv
    sample = int(args[args.index("--depth-sample") + 1]) if "--depth-sample" in args else DEPTH_SAMPLE
    top = int(args[args.index("--top") + 1]) if "--top" in args else TOP
    covered = float(args[args.index("--covered") + 1]) if "--covered" in args else COVERED

    existing = _existing_keys()
    print("Harvesting candidates…")
    cands = harvest_referential(existing) + harvest_depth(sample) + harvest_coverage()
    print(f"  {len(cands)} raw candidates; deduping vs {len(core._embed_cache_load())} pages (covered≥{covered})…")
    ranked, dropped = dedup_and_rank(cands, top, covered)
    print(f"  dropped {dropped} as already-covered\n")

    by = {"referential": [], "depth": [], "coverage": []}
    for c in ranked:
        by[c["strategy"]].append(c)
    for strat in ("referential", "depth", "coverage"):
        items = by[strat]
        if not items:
            continue
        print(f"=== {strat.upper()} ({len(items)}) ===")
        for c in items:
            print(f"  [{c['coverage']:.2f}] {c['q']}")
            print(f"        ↳ {c['reason']}  (nearest: {c['nearest']})")
        print()
    print(f"Proposed {len(ranked)} gap-questions (sorted by gap size; lower score = bigger gap).")


if __name__ == "__main__":
    main()
