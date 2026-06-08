"""
Note entity-linker — turn graph-orphan notes into connected graph nodes.

Two passes:
  1. Extract entities (name + type) from every note (one Flash call each), and
     count how often each undocumented entity recurs across notes.
  2. Create lightweight hub-stubs (wiki/stubs/) for entities mentioned in >= MIN_FREQ
     notes, then append a `## Related` section of [[wikilinks]] to each note,
     pointing at matched existing curated pages AND the new hub-stubs.

So 4 notes mentioning osimertinib all link to a single [[osimertinib]] hub —
that's what makes the graph connected. Hub-stubs are quarantined (excluded from
synthesis) and double as the Grow tab's referential queue. Prose/citations/
verified status untouched; idempotent.

Usage:  .venv/bin/python link_notes.py            # apply
        .venv/bin/python link_notes.py --dry-run  # report, write nothing
"""

from __future__ import annotations

import re
import sys
from collections import Counter

import core

DRY = "--dry-run" in sys.argv
MIN_FREQ = 2  # stub an undocumented entity only if >= this many notes mention it


def _target_key_map() -> dict[str, str]:
    """normalized name/alias/stem -> stem, for existing curated link targets."""
    m: dict[str, str] = {}
    for p in core.list_wiki_pages():
        if p.parent.name not in ("entities", "concepts", "sources"):
            continue
        stem = p.stem
        keys = {stem.lower(), stem.replace("-", " ").lower()}
        try:
            fm, _ = core.parse_frontmatter(p.read_text(encoding="utf-8"))
        except OSError:
            fm = {}
        title = (fm.get("title", "") or "").strip().strip('"').strip("'").lower()
        if title:
            keys.add(title)
        for a in re.findall(r'"([^"]+)"', fm.get("aliases", "") or ""):
            keys.add(a.lower())
        for k in keys:
            if len(k) >= 3:
                m.setdefault(k, stem)
    return m


def _match(name: str, keymap: dict[str, str]) -> str | None:
    for cand in (name.lower(), core.kebab(name), core.kebab(name).replace("-", " ")):
        if cand in keymap:
            return keymap[cand]
    return None


def _extract_entities(title: str, body: str) -> list[tuple[str, str]]:
    prompt = (
        "List the specific named entities this clinical note discusses that each merit "
        "their own wiki page — drugs, clinical trials, biomarkers/genes, cancer types, "
        "key concepts. Return STRICTLY a JSON array of objects {\"name\":..., \"type\":...} "
        'where type is one of drug|trial|biomarker|cancer|concept. Max 15.\n\n'
        f"NOTE: {title}\n\n{body[:1800]}"
    )
    resp = core.get_client().models.generate_content(model=core.MODEL_FLASH, contents=prompt)
    parsed = core._extract_json(resp.text or "")
    out = []
    if isinstance(parsed, list):
        for e in parsed:
            if isinstance(e, dict) and e.get("name"):
                out.append((str(e["name"]).strip(), str(e.get("type", "concept"))))
    return out


def _exists(stem: str) -> bool:
    return core._synthesis_page_path(stem) is not None or (core.STUBS_DIR / f"{stem}.md").exists()


def _set_related(text: str, stems: list[str]) -> str:
    text = re.sub(r"\n## Related\n.*?(?=\n## |\Z)", "\n", text, flags=re.DOTALL)
    block = "## Related\n\n" + "\n".join(f"- [[{s}]]" for s in stems) + "\n"
    if "## Provenance" in text:
        return text.replace("## Provenance", block + "\n## Provenance", 1)
    return text.rstrip() + "\n\n" + block


def main() -> None:
    keymap = _target_key_map()
    notes = sorted(core.NOTES_DIR.glob("*.md"))

    # ---- PASS 1: extract entities per note + count undocumented recurrence ----
    print(f"Pass 1: extracting entities from {len(notes)} notes…")
    note_ents: dict = {}
    undoc_freq: Counter = Counter()
    undoc_type: dict[str, tuple[str, str]] = {}
    for nf in notes:
        fm, body = core.parse_frontmatter(nf.read_text(encoding="utf-8"))
        title = (fm.get("title", nf.stem) or nf.stem).strip().strip('"')
        ents = _extract_entities(title, body)
        note_ents[nf] = ents
        seen = set()
        for name, typ in ents:
            if _match(name, keymap):
                continue
            key = core.kebab(name)
            if not key or key in seen:
                continue
            seen.add(key)
            undoc_freq[key] += 1
            undoc_type.setdefault(key, (name, typ))

    # ---- create hub-stubs for entities recurring across >= MIN_FREQ notes ----
    stub_for: dict[str, str] = {}
    created = 0
    for key, freq in undoc_freq.items():
        if freq < MIN_FREQ:
            continue
        name, typ = undoc_type[key]
        # Only stub SPECIFIC named entities. Generic concepts/endpoints/orgs
        # (chemotherapy, overall-survival, ASCO…) make non-discriminating hubs
        # and pollute the graph — skip them.
        if typ not in ("drug", "trial", "biomarker", "cancer"):
            continue
        if DRY:
            stub_for[key] = key
            continue
        if not _exists(key):
            entity = {
                "name": name,
                "filename": key,
                "type": typ if typ in ("drug", "trial", "cancer", "biomarker") else "concept",
                "brief": f"(graph hub — auto-created node referenced by {freq} notes; expand via the Grow tab)",
                "aliases": [],
                "relevance": "Auto-created as a graph hub to connect related notes.",
            }
            src = next((nf for nf, es in note_ents.items() if any(core.kebab(n) == key for n, _ in es)), notes[0])
            core.write_entity_stub(entity, str(src))
            created += 1
        if _exists(key):
            stub_for[key] = key
    print(f"  hub-stubs {'to create' if DRY else 'created'}: "
          f"{sum(1 for k, f in undoc_freq.items() if f >= MIN_FREQ)} "
          f"(entities recurring in >= {MIN_FREQ} notes)")

    # ---- PASS 2: link each note to matched existing pages + hub-stubs ----
    linked, edges = 0, 0
    hub_use: Counter = Counter()
    for nf in notes:
        stems: list[str] = []
        for name, typ in note_ents[nf]:
            s = _match(name, keymap) or stub_for.get(core.kebab(name))
            if s and s != nf.stem and s not in stems:
                stems.append(s)
                hub_use[s] += 1
        if not stems:
            continue
        if not DRY:
            nf.write_text(_set_related(nf.read_text(encoding="utf-8"), stems), encoding="utf-8")
        linked += 1
        edges += len(stems)

    print(f"\n{'[dry-run] ' if DRY else ''}{linked}/{len(notes)} notes linked, {edges} edges, "
          f"{created} hub-stubs created.")
    print("Top hubs:", ", ".join(f"{s}({c})" for s, c in hub_use.most_common(12)))
    if not DRY:
        print("\nNext: re-run kg_index so the graph includes the new note edges + hubs.")


if __name__ == "__main__":
    main()
