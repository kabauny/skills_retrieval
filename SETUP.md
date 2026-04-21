# Obsidian Setup Guide

Step-by-step instructions to set up this wiki as an Obsidian vault.

---

## 1. Open the vault

1. Open Obsidian
2. Click **Open folder as vault**
3. Select the `skills_retrieval` directory (the root of this project)
4. Obsidian will create a `.obsidian/` config folder — this is gitignored

---

## 2. Configure core settings

Open Settings (gear icon in the bottom-left, or `Cmd+,`).

### Files and links

Navigate to **Settings > Files and links** and set:

| Setting | Value | Why |
|---------|-------|-----|
| **New link format** | Shortest path when possible | Keeps wikilinks clean — `[[pembrolizumab]]` instead of `[[wiki/entities/pembrolizumab]]` |
| **Use [[Wikilinks]]** | ON | The wiki uses Obsidian-style wikilinks, not standard markdown links |
| **Default location for new attachments** | In the folder specified below | Keeps images organized |
| **Attachment folder path** | `raw/assets` | All images and attachments go here |

### Editor

Navigate to **Settings > Editor**:

| Setting | Value | Why |
|---------|-------|-----|
| **Strict line breaks** | OFF | Normal markdown paragraph behavior |

---

## 3. Install community plugins

1. Go to **Settings > Community plugins**
2. If prompted, click **Turn on community plugins**
3. Click **Browse** and install each plugin below
4. After installing, enable each one via the toggle

### High priority

**Dataview**
- Lets you query wiki pages by frontmatter fields
- Example: create a note with a Dataview query to list all sources tagged `#cancer/lung`:
  ````
  ```dataview
  TABLE title, year, source_type
  FROM "wiki/sources"
  WHERE contains(tags, "cancer/lung")
  SORT year DESC
  ```
  ````

**Obsidian Web Clipper** (browser extension)
- Install from your browser's extension store (Chrome/Firefox/Safari)
- Configure the default save location to `raw/papers/` or `raw/guidelines/`
- After clipping an article, it appears as a markdown file ready for ingestion

### Medium priority

**Tag Wrangler**
- Right-click any tag in the tag pane to rename or merge it across the entire vault
- Useful as the tag taxonomy evolves

**Graph Analysis**
- Adds metrics (betweenness, degree) to the graph view
- Helps identify hub pages and isolated clusters

---

## 4. Configure the graph view

1. Open the graph view: `Cmd+G` (or click the graph icon in the left sidebar)
2. Click the settings gear in the graph panel
3. Under **Groups**, add color-coded groups:

| Group query | Suggested color | Purpose |
|-------------|-----------------|---------|
| `path:wiki/sources` | Blue | Source summaries |
| `path:wiki/entities` | Green | Entities (drugs, cancers, biomarkers) |
| `path:wiki/concepts` | Orange | Concepts and mechanisms |
| `path:wiki/preferences` | Purple | Personal preferences |
| `path:raw` | Gray | Raw sources (optional — can also hide these) |

4. Under **Filters**:
   - Toggle **Orphans** on to see disconnected pages (lint candidates)
   - Toggle **Attachments** off to reduce noise

5. Under **Display**:
   - Turn on **Arrows** to see link direction
   - Adjust **Node size** to scale by number of connections (hubs appear larger)

---

## 5. Set up excluded folders

To keep search results and graph clean:

1. Go to **Settings > Files and links**
2. Under **Excluded files**, add:
   - `.obsidian`
   - `.git`

---

## 6. Optional: Download images hotkey

If your sources contain images you want to reference locally:

1. Go to **Settings > Hotkeys**
2. Search for "Download all remote images"
3. Bind it to `Cmd+Shift+D` (or your preference)
4. After clipping an article, hit the hotkey to download all images to `raw/assets/`

This lets the LLM view and reference images directly instead of relying on URLs.

---

## 7. Verify the setup

Checklist to confirm everything works:

- [ ] Open Obsidian — vault loads without errors
- [ ] Navigate to `wiki/index.md` — renders correctly with the wikilink to `[[overview]]`
- [ ] Open graph view (`Cmd+G`) — you see `index` and `log` nodes, color-coded if groups are set
- [ ] Click `[[overview]]` link in index — Obsidian offers to create the file (expected — it doesn't exist yet)
- [ ] Check Settings > Files and links — wikilinks ON, link format set to shortest path
- [ ] Dataview plugin enabled — no errors in console

---

## 8. Start using the wiki

1. Drop a paper or guideline into `raw/papers/` or `raw/guidelines/`
   - Use Web Clipper for articles, or manually save PDFs/markdown files
2. Open your LLM agent (Claude Code, Codex, etc.)
3. Tell it to ingest the source: e.g. "ingest `raw/papers/my-paper.md`"
4. Watch the wiki grow — source summary, entity pages, cross-references will appear
5. Browse the results in Obsidian — follow wikilinks, check graph view, read the updated index
