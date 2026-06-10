"""
Wire the disease layer to the drug layer so the entity corpus is reachable.

Today drugs link UP to their cancer, but cancers don't link DOWN to their drugs,
and disease frameworks link only to lenses — so a disease-level query can't reach
the drug entities it should use. This adds, deterministically (no tokens):
  - cancer entity  -> each drug that treats it  (inverted from seed_backbone.DRUGS)
  - cancer entity  -> its disease framework      (if not already)
  - framework      -> its cancer entity          (so a framework pick can reach it)

Existing content is never overwritten — links are merged into ## Related.

Run:  .venv/bin/python wire_disease_drugs.py [--dry-run]
"""

from __future__ import annotations

import sys
from collections import defaultdict

import core
import seed_backbone as sb

ENT = core.WIKI / "entities"
PRIN = core.PRINCIPLES_DIR


def main() -> None:
    dry = "--dry-run" in sys.argv
    cancer_drugs: dict[str, list[str]] = defaultdict(list)
    for dstem, d in sb.DRUGS.items():
        for c in d["cancers"]:
            if c in sb.CANCERS:
                cancer_drugs[c].append(dstem)

    cancers_wired = drugs_linked = frameworks_wired = 0
    for cstem in sb.CANCERS:
        framework = f"{cstem}-approach"
        epath = ENT / f"{cstem}.md"
        if epath.exists():
            targets = sorted(set(cancer_drugs.get(cstem, [])))
            if (PRIN / f"{framework}.md").exists():
                targets.append(framework)
            text = epath.read_text(encoding="utf-8")
            new, added = sb._merge_related(text, targets)
            if added:
                cancers_wired += 1
                drugs_linked += sum(1 for a in added if a != framework)
                if not dry:
                    epath.write_text(new, encoding="utf-8")
        # framework -> cancer entity (so a framework pick can reach the entity)
        fpath = PRIN / f"{framework}.md"
        if fpath.exists() and epath.exists():
            ftext = fpath.read_text(encoding="utf-8")
            fnew, fadded = sb._merge_related(ftext, [cstem])
            if fadded:
                frameworks_wired += 1
                if not dry:
                    fpath.write_text(fnew, encoding="utf-8")

    tag = "[dry-run] " if dry else ""
    print(f"{tag}cancers wired to drugs: {cancers_wired} ({drugs_linked} drug links added); "
          f"frameworks linked to their entity: {frameworks_wired}")


if __name__ == "__main__":
    main()
