"""
Reconcile wiki/index.md with the pages on disk.

Adds an index entry for every synthesis-eligible page (entities/concepts/notes)
that isn't catalogued yet, so the query router can reach it. Idempotent.

Usage:
    .venv/bin/python reconcile.py            # backfill missing pages
    .venv/bin/python reconcile.py --check    # report gaps, write nothing
"""

from __future__ import annotations

import sys

import core


def main() -> None:
    if "--check" in sys.argv:
        gaps = core.index_gaps()
        if not gaps:
            print("Index complete — every page is reachable.")
            return
        print(f"{len(gaps)} page(s) missing from index.md:")
        for p in gaps:
            print(f"  - {p.parent.name}/{p.stem}")
        sys.exit(1)

    added = core.reconcile_index()
    if added:
        print(f"Indexed {len(added)} previously-unreachable page(s):")
        for stem in added:
            print(f"  - {stem}")
    else:
        print("Index already complete — nothing to add.")


if __name__ == "__main__":
    main()
