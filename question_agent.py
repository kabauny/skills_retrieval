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
            "kind": "breadth",
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
            "Given this clinical note, write up to 3 PATIENT-SCENARIO questions that "
            "force a real clinical DECISION the note does NOT already settle. Each "
            "question MUST:\n"
            "  (a) embed a brief patient profile — age, key biomarker/stage, and a "
            "performance-status or comorbidity detail;\n"
            "  (b) pose an explicit choice between >=2 defensible options (e.g. "
            "'drug A alone vs A+chemo', 'switch vs continue + local therapy');\n"
            "  (c) be answerable from current evidence, in the note's disease area.\n"
            "Cover decisions the note leaves open: next-line therapy, acquired "
            "resistance, toxicity-driven changes, sequencing, special populations.\n"
            "Do NOT use 'What is...' or 'Summarize...' phrasing — these must read like "
            "a clinician deciding on a specific patient.\n"
            'Return STRICTLY a JSON array of question strings.\n\nNOTE: ' + title + "\n\n" + body[:1500]
        )
        resp = core.get_client().models.generate_content(model=core.MODEL_FLASH, contents=prompt)
        qs = core._extract_json(resp.text or "")
        if isinstance(qs, list):
            for q in qs[:3]:
                if isinstance(q, str) and len(q) > 12:
                    out.append({"q": q.strip(), "strategy": "depth", "kind": "judgment",
                                "reason": f"follow-up from [[{p.stem}]]"})
    return out


_LINK_RE = re.compile(r"\[\[([^\]|#]+)")
CONTRACT_CAP = 25  # most graph-impactful contract gaps to surface per scan

# Phrasing for each kind of missing contract edge. {t} = entity title.
_PRINCIPLE_Q = {
    "efficacy":
        "Summarize the efficacy of {t}: the pivotal endpoint(s), the effect size, "
        "and which patient subsets derive the most benefit.",
    "adverse-events":
        "What is the adverse-event profile of {t}, and how does its toxicity "
        "interact with common comorbidities when selecting treatment?",
    "biomarker-testing":
        "What biomarker testing guides systemic therapy selection in {t}?",
    "staging-and-resectability":
        "How is {t} staged, and what determines resectability and curative-intent "
        "eligibility?",
}


def _entity_pages() -> list:
    d = core.WIKI / "entities"
    return list(d.glob("*.md")) if d.exists() else []


def _contract_item(stem: str, title: str, etype: str, *, principle: str = "", need_type: str = "") -> dict:
    if principle:
        q = _PRINCIPLE_Q.get(principle, f"Describe {principle.replace('-', ' ')} for {{t}}.").format(t=title)
        reason = f"{etype} [[{stem}]] missing required link [[{principle}]]"
    else:
        q = (f"In which cancer type(s) and histology was {title} studied or indicated?"
             if need_type == "cancer" else
             f"Which {need_type}(s) does {title} involve?")
        reason = f"{etype} [[{stem}]] missing a required link to a {need_type} entity"
    return {
        "q": q, "strategy": "contract", "kind": "structure", "reason": reason,
        "coverage": 0.0, "nearest": stem,
    }


def harvest_contract() -> list[dict]:
    """Scan entity pages against core.LINK_CONTRACT and propose a fix-question for
    each missing required edge (principle lens or anchoring entity link). These
    are STRUCTURAL gaps, so they skip the semantic-coverage dedup — a missing
    [[efficacy]] link is a gap even if an efficacy note exists elsewhere."""
    contract = core.LINK_CONTRACT
    pages = _entity_pages()
    type_of: dict[str, str] = {}
    for p in pages:
        try:
            fm, _ = core.parse_frontmatter(p.read_text(encoding="utf-8"))
        except OSError:
            continue
        type_of[p.stem] = (fm.get("entity_type", "") or "").strip().strip('"').strip("'").lower()
    out: list[dict] = []
    for p in pages:
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        fm, _ = core.parse_frontmatter(text)
        # Supportive-care agents (antiemetics, steroids), drug classes, and
        # modalities are marked contract_exempt — the "must link a cancer" rule
        # doesn't sensibly apply to an antiemetic, so don't flag them.
        if str(fm.get("contract_exempt", "")).strip().strip('"').lower() in ("true", "yes", "1"):
            continue
        etype = (fm.get("entity_type", "") or "").strip().strip('"').strip("'").lower()
        rule = contract.get(etype)
        if not rule:
            continue
        title = (fm.get("title", p.stem) or p.stem).strip().strip('"')
        links = {l.strip() for l in _LINK_RE.findall(text)}
        for pr in rule.get("principles", []):
            if pr not in links:
                out.append(_contract_item(p.stem, title, etype, principle=pr))
        for need_type in rule.get("entity_types", []):
            if not any(type_of.get(l) == need_type for l in links):
                out.append(_contract_item(p.stem, title, etype, need_type=need_type))
    return out


def harvest_coverage() -> list[dict]:
    out = []
    for c in CANCERS:
        for ax in AXES:
            out.append({
                "q": f"What is the {ax} for {c}?",
                "strategy": "coverage",
                "kind": "breadth",
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
    # Contract gaps bypass semantic dedup (structural, not topical). Rank by graph
    # payoff so the most-connected entities' missing edges surface first, then cap.
    contract = harvest_contract()
    for item in contract:
        item["connectivity"] = _connectivity(item["q"], item.get("reason", ""), adj)
    contract.sort(key=lambda c: -c["connectivity"])
    return ranked + contract[:CONTRACT_CAP]


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
