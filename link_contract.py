"""
Close the mechanical part of the link contract:
  1. Mark supportive-care / drug-class / modality entities `contract_exempt: true`
     so the "drug must link a cancer" rule stops flagging them (an antiemetic has
     no single tumor indication).
  2. Merge the universal principle links into every non-exempt entity by type:
     drug -> efficacy, adverse-events; cancer -> staging-and-resectability,
     biomarker-testing; trial -> efficacy.

Entity-type links (drug->cancer, trial->drug/cancer) need knowledge, so they are
handled separately by a research pass — not here.

Run:  .venv/bin/python link_contract.py [--dry-run]
"""

from __future__ import annotations

import sys

import core
import seed_backbone as sb

# Not single-indication antineoplastics — supportive care, classes, modalities.
EXEMPT = {
    "ondansetron", "prednisone", "leucovorin", "infliximab",
    "immune-checkpoint-inhibitor", "mek-inhibitor", "aromatase-inhibitor",
    "ovarian-function-suppression",
}

PRINCIPLES_BY_TYPE = {
    "drug": ["efficacy", "adverse-events"],
    "cancer": ["staging-and-resectability", "biomarker-testing"],
    "trial": ["efficacy"],
}

# Knowledge-based entity-type links — each target is an EXISTING entity of the
# right type, so the link resolves and satisfies the contract. Drugs/regimens get
# their cancer; trials get their investigational drug + disease. (merge skips any
# already present, so listing both is safe.)
ENTITY_TYPE_LINKS = {
    # drugs / regimens -> cancer
    "amivantamab": ["non-small-cell-lung-cancer"],
    "lazertinib": ["non-small-cell-lung-cancer"],
    "sunvozertinib": ["non-small-cell-lung-cancer"],
    "belantamab-mafodotin": ["multiple-myeloma"],
    "ciltacabtagene-autoleucel": ["multiple-myeloma"],
    "daraxonrasib": ["pancreatic-cancer"],
    "sonrotoclax": ["chronic-lymphocytic-leukemia"],
    "vepdegestrant": ["breast-cancer"],
    "trifluridine-tipiracil": ["colorectal-cancer"],
    "i-131-iobenguane": ["paraganglioma"],
    "bacillus-calmette-guerin": ["urothelial-carcinoma"],
    "folfiri": ["colorectal-cancer"],
    "folfox": ["colorectal-cancer"],
    "pola-r-chp": ["diffuse-large-b-cell-lymphoma"],
    "r-chop": ["diffuse-large-b-cell-lymphoma"],
    # trials -> investigational drug + disease
    "altair-trial": ["trifluridine-tipiracil", "colorectal-cancer"],
    "cobra-trial": ["folfox", "colorectal-cancer"],
    "destiny-breast11": ["trastuzumab-deruxtecan", "breast-cancer"],
    "dreamm-7-trial": ["belantamab-mafodotin", "multiple-myeloma"],
    "dynamic-trial": ["oxaliplatin", "colorectal-cancer"],
    "majestec-3-trial": ["teclistamab", "multiple-myeloma"],
    "ofset-trial": ["breast-cancer"],
    "potomac-trial": ["durvalumab", "urothelial-carcinoma"],
    "rasolute-302": ["daraxonrasib", "pancreatic-cancer"],
    "rasolute-302-trial": ["daraxonrasib", "pancreatic-cancer"],
    "rxponder-trial": ["tamoxifen", "breast-cancer"],
    "tailorx-trial": ["tamoxifen", "breast-cancer"],
    "zest-trial": ["niraparib", "breast-cancer"],
}

ENT = core.WIKI / "entities"


def _is_exempt(fm: dict) -> bool:
    return str(fm.get("contract_exempt", "")).strip().strip('"').lower() in ("true", "yes", "1")


def stamp_exempt(stem: str, dry: bool) -> str:
    path = ENT / f"{stem}.md"
    if not path.exists():
        return "missing"
    text = path.read_text(encoding="utf-8")
    fm, _ = core.parse_frontmatter(text)
    if _is_exempt(fm):
        return "already"
    marker = "contract_exempt: true\n"
    if text.startswith("---\n") and (end := text.find("\n---\n", 4)) != -1:
        text = text[: end + 1] + marker + text[end + 1 :]
    else:
        text = f"---\n{marker}---\n\n{text}"
    if not dry:
        path.write_text(text, encoding="utf-8")
    return "stamped"


def main() -> None:
    dry = "--dry-run" in sys.argv
    stamped = 0
    for stem in sorted(EXEMPT):
        if stamp_exempt(stem, dry) == "stamped":
            stamped += 1
    merged = 0
    for p in sorted(ENT.glob("*.md")):
        if p.stem in EXEMPT:
            continue
        fm, _ = core.parse_frontmatter(p.read_text(encoding="utf-8"))
        if _is_exempt(fm):
            continue
        etype = (fm.get("entity_type", "") or "").strip().strip('"').strip("'").lower()
        needed = PRINCIPLES_BY_TYPE.get(etype)
        if not needed:
            continue
        text = p.read_text(encoding="utf-8")
        new, added = sb._merge_related(text, needed)
        if added:
            merged += 1
            if not dry:
                p.write_text(new, encoding="utf-8")
    # Entity-type links (knowledge-based), validated against existing entity types.
    type_of = {}
    for q in ENT.glob("*.md"):
        f, _ = core.parse_frontmatter(q.read_text(encoding="utf-8"))
        type_of[q.stem] = (f.get("entity_type", "") or "").strip().strip('"').strip("'").lower()
    typed = 0
    bad: list[str] = []
    for stem, targets in ENTITY_TYPE_LINKS.items():
        path = ENT / f"{stem}.md"
        if not path.exists():
            bad.append(f"{stem}(missing-page)")
            continue
        for t in targets:
            if type_of.get(t) not in ("drug", "cancer"):
                bad.append(f"{stem}->{t}(target not a typed entity)")
        text = path.read_text(encoding="utf-8")
        new, added = sb._merge_related(text, targets)
        if added:
            typed += 1
            if not dry:
                path.write_text(new, encoding="utf-8")
    tag = "[dry-run] " if dry else ""
    print(f"{tag}exempt stamped: {stamped}/{len(EXEMPT)}; principle links: {merged}; entity-type links: {typed}")
    if bad:
        print("  WARN unresolved targets:", "; ".join(bad))


if __name__ == "__main__":
    main()
