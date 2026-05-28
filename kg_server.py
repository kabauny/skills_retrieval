#!/usr/bin/env python3
"""
knowledge-graph MCP server for the Oncology Care Wiki.

Parses the wiki's ``[[wikilink]]`` structure into a directed graph and exposes
graph-retrieval tools (the ``kg_*`` family described in SCHEMA.md § Graph tools)
over it. Nodes are wiki pages keyed by filename stem (wikilinks resolve by stem,
per the schema's "keep filenames unique" rule). Edges are wikilinks.

The append-only ``log.md`` and the navigational ``index.md`` are excluded from
the graph: they link to nearly every page and would drown out the real topic
structure in centrality and community detection. Everything else under
``wiki/`` (sources, entities, concepts, avatar, overview) is included.

Transport: stdio (the default for Claude Code project MCP servers).

Usage:
    python3 kg_server.py            # run as an MCP server (stdio)
    python3 kg_server.py --stats    # build the graph, print a summary, exit
    python3 kg_server.py --selftest # exercise every read tool once, exit
"""

from __future__ import annotations

import json
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "networkx is required for the knowledge-graph server.\n"
        "Install dependencies with: pip install -r requirements.txt\n"
    )
    raise

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    sys.stderr.write(
        "The 'mcp' package is required for the knowledge-graph server.\n"
        "Install dependencies with: pip install -r requirements.txt\n"
    )
    raise

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
WIKI = ROOT / "wiki"
CACHE_PATH = ROOT / ".kg_cache.json"

# Pages that link to nearly everything — kept out of the graph so they don't
# dominate centrality/communities. They remain on disk; they are just not nodes.
EXCLUDE_STEMS = {"index", "log"}

WIKILINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
TOKEN_RE = re.compile(r"[a-z0-9]+")

# BM25 parameters
BM25_K1 = 1.5
BM25_B = 0.75

# Field boosts (token repetition) for the search index
BOOST_TITLE = 3
BOOST_ALIAS = 3
BOOST_TAG = 2

STOPWORDS = {
    "the", "a", "an", "of", "to", "in", "for", "and", "or", "is", "are", "was",
    "with", "on", "at", "by", "as", "be", "it", "this", "that", "vs", "what",
    "how", "do", "you", "tell", "me", "about", "can", "would", "should", "if",
    "from", "into", "than", "then", "but", "not", "no",
}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def kebab(text: str, max_len: int = 80) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text).strip("-")
    return text[:max_len]


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if len(t) >= 2 and t not in STOPWORDS]


def link_target_stem(raw: str) -> str | None:
    """Normalise a wikilink target to a node stem.

    Handles ``[[target|display]]``, ``[[target#heading]]`` and path-qualified
    targets like ``[[avatar/jim.chen/decisions]]`` (→ ``decisions``).
    """
    raw = raw.split("|", 1)[0].split("#", 1)[0].strip()
    if not raw:
        return None
    if raw.endswith(".md"):
        raw = raw[:-3]
    return Path(raw).name or None


def _parse_list_value(val: str, lines: list[str], idx: int) -> tuple[list[str], int]:
    """Parse a YAML list value, inline (``[a, b]``) or block (``- a`` lines)."""
    val = val.strip()
    if val.startswith("["):
        inner = val.strip("[]")
        items = [
            x.strip().strip('"').strip("'").lstrip("#")
            for x in inner.split(",")
            if x.strip()
        ]
        return items, idx
    items: list[str] = []
    j = idx + 1
    while j < len(lines):
        m = re.match(r"^\s*-\s+(.*)$", lines[j])
        if not m:
            break
        items.append(m.group(1).strip().strip('"').strip("'").lstrip("#"))
        j += 1
    return items, j - 1


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Light YAML frontmatter parse. Returns (frontmatter_dict, body)."""
    fm: dict = {"tags": [], "aliases": []}
    if not text.startswith("---\n"):
        return fm, text
    rest = text[4:]
    m = re.search(r"\n---[ \t]*\n", rest)
    if not m:
        return fm, text
    fm_block = rest[: m.start()]
    body = rest[m.end():]

    lines = fm_block.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        km = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if not km:
            i += 1
            continue
        key, val = km.group(1), km.group(2)
        if key in ("tags", "aliases"):
            items, i = _parse_list_value(val, lines, i)
            fm[key] = items
        else:
            fm[key] = val.strip().strip('"').strip("'")
        i += 1
    return fm, body


def kind_for(path: Path) -> str:
    rel = path.relative_to(WIKI)
    return rel.parts[0] if len(rel.parts) > 1 else "root"


def parse_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    links: list[str] = []
    for raw in WIKILINK_RE.findall(text):
        stem = link_target_stem(raw)
        if stem and stem not in EXCLUDE_STEMS:
            links.append(stem)
    stat = path.stat()
    return {
        "stem": path.stem,
        "path": str(path.relative_to(ROOT)),
        "kind": kind_for(path),
        "title": (fm.get("title") or path.stem).strip(),
        "tags": fm.get("tags", []),
        "aliases": fm.get("aliases", []),
        "entity_type": fm.get("entity_type", ""),
        "auto_generated": str(fm.get("auto_generated", "")).lower() == "true",
        "user": fm.get("user", ""),
        "links": links,
        "body": body,
        "mtime": stat.st_mtime,
        "size": stat.st_size,
    }


def iter_wiki_files() -> list[Path]:
    out: list[Path] = []
    if not WIKI.exists():
        return out
    for p in WIKI.rglob("*.md"):
        if any(part.startswith(".") for part in p.parts):
            continue
        if p.stem in EXCLUDE_STEMS:
            continue
        out.append(p)
    return out


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------


class KnowledgeGraph:
    """In-memory graph + search index over the wiki, with incremental refresh."""

    def __init__(self) -> None:
        self.records: dict[str, dict] = {}      # stem -> parsed record
        self.G = nx.DiGraph()
        self.UG = nx.Graph()
        self.dangling: dict[str, list[str]] = {}  # stem -> unresolved link targets
        self.pagerank: dict[str, float] = {}
        self.betweenness: dict[str, float] = {}
        self.communities: list[list[str]] = []
        self.node_community: dict[str, int] = {}
        # Search index
        self.doc_freq: dict[str, Counter] = {}
        self.doc_len: dict[str, int] = {}
        self.df: Counter = Counter()
        self.avgdl: float = 0.0
        self.last_index: dict = {}
        self._loaded_cache = False

    # -- cache ------------------------------------------------------------

    def _load_cache(self) -> None:
        if self._loaded_cache:
            return
        self._loaded_cache = True
        if not CACHE_PATH.exists():
            return
        try:
            data = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
            self.records = data.get("files", {})
        except (OSError, json.JSONDecodeError):
            self.records = {}

    def _save_cache(self) -> None:
        try:
            CACHE_PATH.write_text(
                json.dumps({"files": self.records}, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    # -- indexing ---------------------------------------------------------

    def ensure(self, force: bool = False) -> dict:
        """Refresh the graph if any wiki file changed. Cheap when nothing moved."""
        self._load_cache()
        t0 = time.perf_counter()

        on_disk = {p.stem: p for p in iter_wiki_files()}
        changed: list[str] = []
        removed: list[str] = []

        # Drop deleted files
        for stem in list(self.records):
            if stem not in on_disk:
                del self.records[stem]
                removed.append(stem)

        # Parse new / modified files
        for stem, path in on_disk.items():
            stat = path.stat()
            rec = self.records.get(stem)
            if (
                rec is None
                or rec.get("mtime") != stat.st_mtime
                or rec.get("size") != stat.st_size
            ):
                self.records[stem] = parse_file(path)
                changed.append(stem)

        rebuilt = force or changed or removed or self.G.number_of_nodes() == 0
        if rebuilt:
            self._rebuild()
            self._save_cache()

        self.last_index = {
            "nodes": self.G.number_of_nodes(),
            "edges": self.G.number_of_edges(),
            "files_indexed": len(self.records),
            "files_changed": sorted(changed),
            "files_removed": sorted(removed),
            "dangling_links": sum(len(v) for v in self.dangling.values()),
            "communities": len(self.communities),
            "rebuilt": bool(rebuilt),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000, 1),
        }
        return self.last_index

    def _rebuild(self) -> None:
        stems = set(self.records)

        # Directed graph (weighted by link multiplicity)
        G = nx.DiGraph()
        G.add_nodes_from(stems)
        dangling: dict[str, list[str]] = {}
        for stem, rec in self.records.items():
            miss: list[str] = []
            for tgt in rec.get("links", []):
                if tgt == stem:
                    continue
                if tgt in stems:
                    if G.has_edge(stem, tgt):
                        G[stem][tgt]["weight"] += 1
                    else:
                        G.add_edge(stem, tgt, weight=1)
                else:
                    miss.append(tgt)
            if miss:
                dangling[stem] = sorted(set(miss))
        self.G = G
        self.dangling = dangling

        # Undirected projection (summed weights) for symmetric algorithms
        UG = nx.Graph()
        UG.add_nodes_from(G.nodes())
        for u, v, d in G.edges(data=True):
            w = d.get("weight", 1)
            if UG.has_edge(u, v):
                UG[u][v]["weight"] += w
            else:
                UG.add_edge(u, v, weight=w)
        self.UG = UG

        self._rebuild_centrality()
        self._rebuild_communities()
        self._rebuild_search()

    def _rebuild_centrality(self) -> None:
        if self.G.number_of_nodes() == 0:
            self.pagerank, self.betweenness = {}, {}
            return
        try:
            self.pagerank = nx.pagerank(self.G, weight="weight")
        except Exception:
            self.pagerank = {n: 1 / self.G.number_of_nodes() for n in self.G}
        try:
            self.betweenness = nx.betweenness_centrality(self.UG)
        except Exception:
            self.betweenness = {n: 0.0 for n in self.UG}

    def _rebuild_communities(self) -> None:
        self.communities = []
        self.node_community = {}
        if self.UG.number_of_nodes() == 0:
            return
        comms: list[set] = []
        try:
            from networkx.algorithms.community import louvain_communities

            comms = list(
                louvain_communities(self.UG, weight="weight", seed=42)
            )
        except Exception:
            comms = list(nx.connected_components(self.UG))
        self.communities = sorted(([sorted(c) for c in comms]), key=len, reverse=True)
        for cid, members in enumerate(self.communities):
            for m in members:
                self.node_community[m] = cid

    def _rebuild_search(self) -> None:
        self.doc_freq, self.doc_len, self.df = {}, {}, Counter()
        total_len = 0
        for stem, rec in self.records.items():
            tokens: list[str] = []
            tokens += tokenize(rec.get("title", "")) * BOOST_TITLE
            for a in rec.get("aliases", []):
                tokens += tokenize(a) * BOOST_ALIAS
            for tg in rec.get("tags", []):
                tokens += tokenize(tg) * BOOST_TAG
            tokens += tokenize(rec.get("body", ""))
            cnt = Counter(tokens)
            self.doc_freq[stem] = cnt
            self.doc_len[stem] = sum(cnt.values())
            total_len += self.doc_len[stem]
            for term in cnt:
                self.df[term] += 1
        n = len(self.records)
        self.avgdl = (total_len / n) if n else 0.0

    # -- resolution -------------------------------------------------------

    def resolve(self, name: str) -> str | None:
        if not name:
            return None
        raw = name.strip().strip("[]")
        raw = raw.split("|", 1)[0].split("#", 1)[0].strip()
        if raw.endswith(".md"):
            raw = raw[:-3]
        stem = Path(raw).name
        if stem in self.records:
            return stem
        low = stem.lower()
        for s in self.records:
            if s.lower() == low:
                return s
        for s, rec in self.records.items():
            if low in [a.lower() for a in rec.get("aliases", [])]:
                return s
            if rec.get("title", "").lower() == low:
                return s
        return None

    # -- search -----------------------------------------------------------

    def search(self, query: str, limit: int = 10) -> list[dict]:
        qterms = tokenize(query)
        if not qterms or not self.records:
            return []
        n = len(self.records)
        scores: dict[str, float] = {}
        for stem, freqs in self.doc_freq.items():
            dl = self.doc_len[stem] or 1
            score = 0.0
            for t in qterms:
                f = freqs.get(t, 0)
                if not f:
                    continue
                df = self.df.get(t, 0)
                idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
                denom = f + BM25_K1 * (1 - BM25_B + BM25_B * dl / (self.avgdl or 1))
                score += idf * (f * (BM25_K1 + 1)) / denom
            if score > 0:
                scores[stem] = score
        ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)[:limit]
        results = []
        for stem, score in ranked:
            rec = self.records[stem]
            results.append({
                "node": stem,
                "title": rec["title"],
                "kind": rec["kind"],
                "score": round(score, 3),
                "snippet": self._snippet(rec.get("body", ""), qterms),
            })
        return results

    @staticmethod
    def _snippet(body: str, qterms: list[str], width: int = 220) -> str:
        low = body.lower()
        pos = -1
        for t in qterms:
            i = low.find(t)
            if i != -1 and (pos == -1 or i < pos):
                pos = i
        if pos == -1:
            chunk = body.strip()[:width]
        else:
            start = max(0, pos - width // 3)
            chunk = body[start:start + width]
        return re.sub(r"\s+", " ", chunk).strip()

    # -- node views -------------------------------------------------------

    def node_view(self, stem: str) -> dict:
        rec = self.records[stem]
        out_links = sorted(set(self.G.successors(stem))) if stem in self.G else []
        in_links = sorted(set(self.G.predecessors(stem))) if stem in self.G else []
        return {
            "node": stem,
            "title": rec["title"],
            "kind": rec["kind"],
            "path": rec["path"],
            "tags": rec.get("tags", []),
            "aliases": rec.get("aliases", []),
            "entity_type": rec.get("entity_type", ""),
            "auto_generated": rec.get("auto_generated", False),
            "out_links": out_links,
            "in_links": in_links,
            "dangling_out_links": self.dangling.get(stem, []),
            "out_degree": len(out_links),
            "in_degree": len(in_links),
            "pagerank": round(self.pagerank.get(stem, 0.0), 5),
            "community": self.node_community.get(stem),
        }

    def community_summary(self, cid: int) -> dict:
        members = self.communities[cid]
        tag_counter: Counter = Counter()
        for m in members:
            for tg in self.records[m].get("tags", []):
                tag_counter[tg] += 1
        ranked_members = sorted(
            members, key=lambda m: self.pagerank.get(m, 0.0), reverse=True
        )
        return {
            "community_id": cid,
            "size": len(members),
            "top_nodes": [
                {"node": m, "title": self.records[m]["title"],
                 "pagerank": round(self.pagerank.get(m, 0.0), 5)}
                for m in ranked_members[:5]
            ],
            "common_tags": [t for t, _ in tag_counter.most_common(5)],
        }


KG = KnowledgeGraph()


# ---------------------------------------------------------------------------
# MCP server + tools
# ---------------------------------------------------------------------------

mcp = FastMCP("knowledge-graph")


def _dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _not_found(name: str) -> str:
    suggestions = KG.search(name, limit=5)
    return _dumps({
        "error": f"No node resolves to '{name}'.",
        "did_you_mean": [s["node"] for s in suggestions],
    })


@mcp.tool()
def kg_index() -> str:
    """Rebuild the knowledge graph from the current wiki state. Run after every
    ingest. Incremental: only changed files are re-parsed. Returns node/edge
    counts, the list of changed files, dangling-link count, and timing."""
    return _dumps(KG.ensure(force=True))


@mcp.tool()
def kg_search(query: str, limit: int = 10) -> str:
    """Search the wiki (BM25 lexical scoring over page title, aliases, tags, and
    body, with title/alias/tag boosting). Use when the index.md catalog is not
    enough to find relevant pages. Returns ranked nodes with score and snippet."""
    KG.ensure()
    return _dumps(KG.search(query, limit=limit))


@mcp.tool()
def kg_node(name: str) -> str:
    """Look up a single node: its metadata, outbound/inbound wikilinks, dangling
    links, degree, PageRank, and community. Accepts a stem, title, or alias."""
    KG.ensure()
    stem = KG.resolve(name)
    if not stem:
        return _not_found(name)
    return _dumps(KG.node_view(stem))


@mcp.tool()
def kg_neighbors(name: str, hops: int = 1, limit: int = 50) -> str:
    """Explore the N-hop neighbourhood of a node (undirected). Returns connected
    nodes with their distance from the center, sorted by distance then degree."""
    KG.ensure()
    stem = KG.resolve(name)
    if not stem:
        return _not_found(name)
    if stem not in KG.UG:
        return _dumps({"center": stem, "hops": hops, "neighbors": []})
    dist = nx.single_source_shortest_path_length(KG.UG, stem, cutoff=hops)
    neighbors = [
        {
            "node": n,
            "title": KG.records[n]["title"],
            "kind": KG.records[n]["kind"],
            "distance": d,
            "degree": KG.UG.degree(n),
        }
        for n, d in dist.items()
        if n != stem
    ]
    neighbors.sort(key=lambda x: (x["distance"], -x["degree"]))
    return _dumps({"center": stem, "hops": hops, "count": len(neighbors),
                   "neighbors": neighbors[:limit]})


@mcp.tool()
def kg_paths(source: str, target: str, max_paths: int = 5, cutoff: int = 6) -> str:
    """Find connection routes between two nodes (undirected shortest simple
    paths, up to ``cutoff`` hops). Useful for tracing how two entities relate
    (e.g. drug → trial → cancer)."""
    KG.ensure()
    s, t = KG.resolve(source), KG.resolve(target)
    if not s:
        return _not_found(source)
    if not t:
        return _not_found(target)
    if s == t:
        return _dumps({"source": s, "target": t, "paths": [[s]]})
    if s not in KG.UG or t not in KG.UG or not nx.has_path(KG.UG, s, t):
        return _dumps({"source": s, "target": t, "paths": [],
                       "note": "no connection within the graph"})
    paths: list[list[str]] = []
    for path in nx.shortest_simple_paths(KG.UG, s, t):
        if len(path) - 1 > cutoff:
            break
        paths.append(path)
        if len(paths) >= max_paths:
            break
    return _dumps({"source": s, "target": t, "count": len(paths), "paths": paths})


@mcp.tool()
def kg_common(a: str, b: str) -> str:
    """Find the shared neighbours of two nodes (undirected) — what two entities
    have directly in common in the wikilink graph."""
    KG.ensure()
    sa, sb = KG.resolve(a), KG.resolve(b)
    if not sa:
        return _not_found(a)
    if not sb:
        return _not_found(b)
    common = []
    if sa in KG.UG and sb in KG.UG:
        for n in set(KG.UG.neighbors(sa)) & set(KG.UG.neighbors(sb)):
            common.append({"node": n, "title": KG.records[n]["title"],
                           "kind": KG.records[n]["kind"], "degree": KG.UG.degree(n)})
    common.sort(key=lambda x: -x["degree"])
    return _dumps({"a": sa, "b": sb, "common_neighbors": common})


@mcp.tool()
def kg_subgraph(name: str, hops: int = 1) -> str:
    """Extract the localised connected component (ego graph) around a node out to
    ``hops`` hops. Returns the member nodes and the edges among them."""
    KG.ensure()
    stem = KG.resolve(name)
    if not stem:
        return _not_found(name)
    if stem not in KG.UG:
        return _dumps({"center": stem, "hops": hops, "nodes": [stem], "edges": []})
    ego = nx.ego_graph(KG.UG, stem, radius=hops)
    nodes = [
        {"node": n, "title": KG.records[n]["title"], "kind": KG.records[n]["kind"]}
        for n in ego.nodes()
    ]
    edges = [[u, v] for u, v in ego.edges()]
    return _dumps({"center": stem, "hops": hops, "node_count": len(nodes),
                   "edge_count": len(edges), "nodes": nodes, "edges": edges})


@mcp.tool()
def kg_bridges(limit: int = 15) -> str:
    """Rank the wiki's bridge pages by betweenness centrality — the connector
    nodes that the most shortest paths run through."""
    KG.ensure()
    ranked = sorted(KG.betweenness.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return _dumps([
        {"node": n, "title": KG.records[n]["title"], "kind": KG.records[n]["kind"],
         "betweenness": round(score, 5)}
        for n, score in ranked if n in KG.records
    ])


@mcp.tool()
def kg_central(limit: int = 15) -> str:
    """Rank the wiki's most important pages by PageRank — the most connected /
    referenced nodes in the graph."""
    KG.ensure()
    ranked = sorted(KG.pagerank.items(), key=lambda kv: kv[1], reverse=True)[:limit]
    return _dumps([
        {"node": n, "title": KG.records[n]["title"], "kind": KG.records[n]["kind"],
         "pagerank": round(score, 5)}
        for n, score in ranked if n in KG.records
    ])


@mcp.tool()
def kg_communities() -> str:
    """List the wiki's topic clusters (Louvain community detection on the
    undirected graph), largest first, each with size, top nodes, and common
    tags. Use to understand the wiki's thematic structure."""
    KG.ensure()
    return _dumps({
        "community_count": len(KG.communities),
        "communities": [KG.community_summary(cid) for cid in range(len(KG.communities))],
    })


@mcp.tool()
def kg_community(community_id: int) -> str:
    """Get the full member list of one community (by id from kg_communities)."""
    KG.ensure()
    if community_id < 0 or community_id >= len(KG.communities):
        return _dumps({"error": f"community_id {community_id} out of range "
                                f"(0..{len(KG.communities) - 1})"})
    summary = KG.community_summary(community_id)
    summary["members"] = [
        {"node": m, "title": KG.records[m]["title"], "kind": KG.records[m]["kind"]}
        for m in sorted(KG.communities[community_id])
    ]
    return _dumps(summary)


# -- mutation tools ---------------------------------------------------------


def _safe_in_wiki(path: Path) -> bool:
    try:
        path.resolve().relative_to(WIKI.resolve())
        return True
    except ValueError:
        return False


@mcp.tool()
def kg_create_node(
    name: str,
    kind: str = "entity",
    title: str = "",
    summary: str = "",
    tags: list[str] | None = None,
    aliases: list[str] | None = None,
    entity_type: str = "",
) -> str:
    """Create a new wiki page (markdown file with frontmatter) and add it to the
    graph. ``kind`` is one of entity | concept | source (→ wiki/entities,
    wiki/concepts, wiki/sources). Refuses to overwrite an existing page."""
    folder_map = {"entity": "entities", "concept": "concepts", "source": "sources"}
    if kind not in folder_map:
        return _dumps({"error": f"kind must be one of {list(folder_map)}"})
    stem = kebab(name)
    if not stem:
        return _dumps({"error": "name produced an empty filename"})
    if stem in EXCLUDE_STEMS:
        return _dumps({"error": f"'{stem}' is a reserved page name"})
    target_dir = WIKI / folder_map[kind]
    path = target_dir / f"{stem}.md"
    if not _safe_in_wiki(path):
        return _dumps({"error": "refusing to write outside wiki/"})
    if path.exists() or stem in KG.records:
        return _dumps({"error": f"node '{stem}' already exists", "path": str(path.relative_to(ROOT))})

    title = title.strip() or name.strip()
    tags = tags or []
    aliases = aliases or []
    tags_yaml = "[" + ", ".join(tags) + "]"
    aliases_yaml = json.dumps(aliases) if aliases else "[]"

    if kind == "entity":
        fm = (
            f"---\ntitle: \"{title}\"\n"
            f"entity_type: {entity_type or 'other'}\n"
            f"aliases: {aliases_yaml}\n"
            f"tags: {tags_yaml}\n---\n"
        )
    elif kind == "source":
        fm = f"---\ntitle: \"{title}\"\nsource_type: note\ntags: {tags_yaml}\n---\n"
    else:  # concept
        fm = f"---\ntitle: \"{title}\"\ntags: {tags_yaml}\n---\n"

    body = f"\n# {title}\n\n{summary.strip() or '(stub)'}\n"
    target_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(fm + body, encoding="utf-8")
    KG.ensure(force=True)
    return _dumps({"created": str(path.relative_to(ROOT)), "node": KG.node_view(stem)})


@mcp.tool()
def kg_annotate_node(name: str, content: str, section: str = "") -> str:
    """Append content to an existing node (append-only, at end of file). If
    ``section`` is given, the content is added under a ``## section`` heading."""
    KG.ensure()
    stem = KG.resolve(name)
    if not stem:
        return _not_found(name)
    path = ROOT / KG.records[stem]["path"]
    if not path.exists() or not _safe_in_wiki(path):
        return _dumps({"error": f"cannot annotate '{stem}'"})
    text = path.read_text(encoding="utf-8")
    addition = f"\n\n## {section.strip()}\n\n{content.strip()}\n" if section.strip() \
        else f"\n\n{content.strip()}\n"
    path.write_text(text.rstrip() + addition, encoding="utf-8")
    KG.ensure(force=True)
    return _dumps({"annotated": str(path.relative_to(ROOT)), "node": KG.node_view(stem)})


_RELATED_MARKER = "## Related (graph)"


@mcp.tool()
def kg_add_link(source: str, target: str, label: str = "") -> str:
    """Add a wikilink from ``source`` to ``target`` (a bullet under a
    '## Related (graph)' section at the end of the source page). The target need
    not exist yet; a dangling link is reported but still written."""
    KG.ensure()
    s = KG.resolve(source)
    if not s:
        return _not_found(source)
    t = KG.resolve(target) or kebab(target)
    target_exists = t in KG.records
    path = ROOT / KG.records[s]["path"]
    if not path.exists() or not _safe_in_wiki(path):
        return _dumps({"error": f"cannot edit '{s}'"})
    link_text = f"[[{t}|{label.strip()}]]" if label.strip() else f"[[{t}]]"
    text = path.read_text(encoding="utf-8")
    if any(tok in text for tok in (f"[[{t}]]", f"[[{t}|", f"[[{t}#")):
        return _dumps({"note": f"link to '{t}' already present in {s}", "skipped": True})
    if _RELATED_MARKER in text:
        new_text = text.rstrip() + f"\n- {link_text}\n"
    else:
        new_text = text.rstrip() + f"\n\n{_RELATED_MARKER}\n\n- {link_text}\n"
    path.write_text(new_text, encoding="utf-8")
    KG.ensure(force=True)
    return _dumps({
        "source": s, "target": t, "target_exists": target_exists,
        "dangling": not target_exists, "edited": str(path.relative_to(ROOT)),
    })


# ---------------------------------------------------------------------------
# Standalone diagnostics
# ---------------------------------------------------------------------------


def _print_stats() -> None:
    stats = KG.ensure(force=True)
    print(_dumps(stats))
    print("\nTop PageRank:")
    print(kg_central(limit=8))
    print("\nTop bridges (betweenness):")
    print(kg_bridges(limit=8))
    print("\nCommunities:")
    print(kg_communities())
    if KG.dangling:
        print("\nDangling links (source -> missing targets):")
        print(_dumps(KG.dangling))


def _selftest() -> None:
    KG.ensure(force=True)
    if not KG.records:
        print("No wiki pages found — nothing to test.")
        return
    # Pick a well-connected node to drive the tests
    center = max(KG.pagerank, key=KG.pagerank.get) if KG.pagerank else next(iter(KG.records))
    others = [n for n in KG.records if n != center]
    target = max(others, key=lambda n: KG.pagerank.get(n, 0)) if others else center

    checks = [
        ("kg_index", lambda: kg_index()),
        ("kg_search", lambda: kg_search("ctDNA MRD adjuvant escalation", 5)),
        ("kg_node", lambda: kg_node(center)),
        ("kg_neighbors", lambda: kg_neighbors(center, 2, 20)),
        ("kg_paths", lambda: kg_paths(center, target)),
        ("kg_common", lambda: kg_common(center, target)),
        ("kg_subgraph", lambda: kg_subgraph(center, 1)),
        ("kg_bridges", lambda: kg_bridges(5)),
        ("kg_central", lambda: kg_central(5)),
        ("kg_communities", lambda: kg_communities()),
        ("kg_community", lambda: kg_community(0)),
    ]
    for label, fn in checks:
        try:
            out = fn()
            parsed = json.loads(out)
            n = len(parsed) if isinstance(parsed, list) else 1
            print(f"[ok]   {label:16s} -> {n if isinstance(parsed, list) else 'dict'} "
                  f"({len(out)} bytes)")
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {label:16s} -> {type(exc).__name__}: {exc}")
    print(f"\ncenter={center}  target={target}  nodes={KG.G.number_of_nodes()}")


def main() -> None:
    if "--stats" in sys.argv:
        _print_stats()
        return
    if "--selftest" in sys.argv:
        _selftest()
        return
    mcp.run()


if __name__ == "__main__":
    main()
