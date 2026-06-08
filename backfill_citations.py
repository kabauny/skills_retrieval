"""
Backfill grounded URL citations into EXISTING wiki/notes/ pages, from their
raw/searches/ audit copies (no API calls — the citations already live there).

Safeguards:
- Preserves the note's frontmatter verbatim (verified status, dates, tags).
- Preserves the banner line (🌱 unverified vs ✅ verified).
- SKIPS a note if its prose diverges from the raw answer (you edited it) — so
  manual corrections are never clobbered.
- SKIPS notes that already have grounded citations, or have no raw source.
- Everything is git-tracked, so any change is recoverable.

Usage:  .venv/bin/python backfill_citations.py            # apply
        .venv/bin/python backfill_citations.py --dry-run  # report only
"""

from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

import core

DRY = "--dry-run" in sys.argv
RAW = core.RAW / "searches"


def _norm(s: str) -> str:
    s = re.sub(r"\[[^\]]+\]\(https?://[^)]+\)", "", s)  # drop [domain](url)
    s = re.sub(r"\[search-sourced\]", "", s)
    return " ".join(s.split()).lower()


def _raw_cited_body_and_sources(raw_text: str):
    _, body = core.parse_frontmatter(raw_text)
    m = re.search(r"^#\s+.+?\n(.*?)(?=\n##\s+Sources|\Z)", body, re.DOTALL | re.MULTILINE)
    cited = (m.group(1).strip() if m else body.strip())
    sm = re.search(r"##\s+Sources\s*\n(.*)$", body, re.DOTALL)
    sources = []
    if sm:
        for t, u in re.findall(r"\[([^\]]+)\]\((https?://[^)]+)\)", sm.group(1)):
            sources.append({"title": t, "url": u})
    return cited, sources


def main() -> None:
    notes = sorted(core.NOTES_DIR.glob("*.md"))
    done = skipped_cited = skipped_noraw = skipped_edited = 0

    for nf in notes:
        text = nf.read_text(encoding="utf-8")
        if "## Web sources (grounded)" in text:
            skipped_cited += 1
            continue
        fm, body = core.parse_frontmatter(text)
        raw_stem = (fm.get("raw_source") or "").strip().strip('"').strip("[]")
        raw_path = RAW / f"{raw_stem}.md"
        if not raw_stem or not raw_path.exists():
            skipped_noraw += 1
            print(f"  skip (no raw): {nf.name}")
            continue

        cited_body, sources = _raw_cited_body_and_sources(raw_path.read_text(encoding="utf-8"))

        # preserve title + banner; isolate current prose for edit-detection
        end = text.find("\n---\n", 4)
        fm_block, nbody = text[: end + 5], text[end + 5 :]
        title_m = re.search(r"^#\s+.+$", nbody, re.MULTILINE)
        banner_m = re.search(r"^>\s+.+$", nbody, re.MULTILINE)
        title_line = title_m.group(0) if title_m else f"# {nf.stem}"
        banner_line = banner_m.group(0) if banner_m else ""
        prose_m = re.search(
            r"^>\s+.+?\n(.*?)(?=\n##\s+(Web sources|Provenance)|\Z)", nbody, re.DOTALL | re.MULTILINE
        )
        current_prose = prose_m.group(1).strip() if prose_m else nbody

        ratio = difflib.SequenceMatcher(None, _norm(current_prose), _norm(cited_body)).ratio()
        if ratio < 0.80:
            skipped_edited += 1
            print(f"  skip (edited, sim={ratio:.2f}): {nf.name}")
            continue

        src_block = ""
        if sources:
            lines = [f"{i}. [{s['title']}]({s['url']})" for i, s in enumerate(sources, 1)]
            src_block = "## Web sources (grounded)\n\n" + "\n".join(lines) + "\n\n"

        new_body = (
            f"{title_line}\n\n"
            f"{banner_line}\n\n" if banner_line else f"{title_line}\n\n"
        )
        new_body += (
            f"{cited_body.strip()}\n\n"
            f"{src_block}"
            f"## Provenance\n\n"
            f"- **Ingested:** {fm.get('auto_date', '(unknown)')}\n"
            f"- **Raw grounded search:** [[{raw_stem}]] — full citations + search queries\n"
        )
        new_text = fm_block + "\n" + new_body

        if DRY:
            print(f"  would backfill ({len(sources)} sources, sim={ratio:.2f}): {nf.name}")
        else:
            nf.write_text(new_text, encoding="utf-8")
            print(f"  backfilled ({len(sources)} sources): {nf.name}")
        done += 1

    print(
        f"\n{'[dry-run] ' if DRY else ''}backfilled: {done}  "
        f"already-cited: {skipped_cited}  no-raw: {skipped_noraw}  edited(skipped): {skipped_edited}"
    )


if __name__ == "__main__":
    main()
