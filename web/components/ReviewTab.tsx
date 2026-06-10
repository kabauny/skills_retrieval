"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ReviewItem } from "@/lib/api";
import ReviewCard from "./ReviewCard";

// Curation thresholds (embedding cosine). Above these, a note is flagged as a
// likely near-duplicate of another note / a shadow of curated entity content.
export const DUP_T = 0.92;
export const SHADOW_T = 0.9;

export const isFlagged = (n: ReviewItem) =>
  !n.verified ||
  (n.link_count ?? 99) <= 1 ||
  (n.dup_score ?? 0) >= DUP_T ||
  (n.shadow_score ?? 0) >= SHADOW_T;

// Higher = more in need of review: unverified, redundant, or weakly linked.
const triageScore = (n: ReviewItem) =>
  (n.verified ? 0 : 3) +
  ((n.shadow_score ?? 0) >= SHADOW_T ? 2 : 0) +
  ((n.dup_score ?? 0) >= DUP_T ? 2 : 0) +
  ((n.link_count ?? 99) <= 1 ? 1 : 0);

export default function ReviewTab({
  user,
  onAfterChange,
}: {
  user: string;
  onAfterChange: () => void;
}) {
  const [sub, setSub] = useState<"notes" | "stubs" | "searches">("notes");
  const [noteSort, setNoteSort] = useState<"triage" | "newest" | "overlap">("triage");
  const [flaggedOnly, setFlaggedOnly] = useState(false);
  const [notes, setNotes] = useState<ReviewItem[]>([]);
  const [stubs, setStubs] = useState<ReviewItem[]>([]);
  const [searches, setSearches] = useState<ReviewItem[]>([]);
  const [gaps, setGaps] = useState<string[]>([]);
  const [reconciling, setReconciling] = useState(false);
  const [reconcileMsg, setReconcileMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([api.notes(), api.stubs(), api.searches(), api.indexGaps()])
      .then(([n, s, q, g]) => {
        setNotes(n.items);
        setStubs(s.items);
        setSearches(q.items);
        setGaps(g.gaps);
      })
      .finally(() => setLoading(false));
  }, []);

  const runReconcile = async () => {
    setReconciling(true);
    setReconcileMsg(null);
    try {
      const r = await api.reconcile(user);
      setReconcileMsg(
        r.added.length
          ? `Indexed ${r.added.length} previously-unreachable page(s).`
          : "Index already complete — nothing to add.",
      );
      load();
      onAfterChange();
    } catch (e: any) {
      setReconcileMsg(`Reconcile failed: ${e.message}`);
    } finally {
      setReconciling(false);
    }
  };

  useEffect(() => {
    load();
  }, [load]);

  const afterChange = () => {
    load();
    onAfterChange();
  };

  let items = sub === "notes" ? notes : sub === "stubs" ? stubs : searches;
  if (sub === "notes") {
    let ns = [...notes];
    if (flaggedOnly) ns = ns.filter(isFlagged);
    ns.sort((a, b) => {
      if (noteSort === "overlap")
        return Math.max(b.shadow_score ?? 0, b.dup_score ?? 0) -
          Math.max(a.shadow_score ?? 0, a.dup_score ?? 0);
      if (noteSort === "newest")
        return (b.auto_date || "").localeCompare(a.auto_date || "");
      // triage: most-in-need first, then oldest
      return triageScore(b) - triageScore(a) || (a.auto_date || "").localeCompare(b.auto_date || "");
    });
    items = ns;
  }

  return (
    <div className="px-6 py-5 max-w-3xl mx-auto">
      <h2 className="text-lg font-semibold mb-1">Review queue</h2>
      <p className="text-sm text-slate-500 mb-4">
        Auto-generated stubs awaiting promotion + saved grounded searches.
        Actions log to <code>wiki/log.md</code>; deletions recover via{" "}
        <code>git restore</code>.
      </p>

      <div
        className={`mb-4 rounded-lg border px-4 py-3 flex items-center justify-between gap-3 ${
          gaps.length
            ? "border-amber-300 bg-amber-50"
            : "border-slate-200 bg-slate-50"
        }`}
      >
        <div className="text-sm">
          {gaps.length ? (
            <span className="text-amber-800">
              ⚠️ <strong>{gaps.length}</strong> page(s) exist on disk but aren't in{" "}
              <code>index.md</code> — the router can't reach them.
            </span>
          ) : (
            <span className="text-slate-600">
              ✓ Index is complete — every page is reachable by the router.
            </span>
          )}
          {reconcileMsg && (
            <span className="block text-xs text-slate-500 mt-1">{reconcileMsg}</span>
          )}
        </div>
        <button
          onClick={runReconcile}
          disabled={reconciling}
          className={gaps.length ? "btn-primary" : "btn-ghost"}
        >
          {reconciling ? "Reconciling…" : "Reconcile index"}
        </button>
      </div>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setSub("notes")}
          className={sub === "notes" ? "btn-primary" : "btn-ghost"}
        >
          📝 Notes ({notes.length})
        </button>
        <button
          onClick={() => setSub("stubs")}
          className={sub === "stubs" ? "btn-primary" : "btn-ghost"}
        >
          🌱 Stubs ({stubs.length})
        </button>
        <button
          onClick={() => setSub("searches")}
          className={sub === "searches" ? "btn-primary" : "btn-ghost"}
        >
          💾 Searches ({searches.length})
        </button>
      </div>

      {sub === "notes" && notes.length > 0 && (
        <div className="flex items-center gap-2 mb-3 text-xs text-slate-500">
          sort:
          {(["triage", "newest", "overlap"] as const).map((s) => (
            <button
              key={s}
              onClick={() => setNoteSort(s)}
              className={noteSort === s ? "btn-primary" : "btn-ghost"}
            >
              {s === "triage" ? "needs review" : s === "newest" ? "newest" : "most overlap"}
            </button>
          ))}
          <label className="ml-auto flex items-center gap-1.5 cursor-pointer">
            <input
              type="checkbox"
              checked={flaggedOnly}
              onChange={(e) => setFlaggedOnly(e.target.checked)}
            />
            flagged only ({notes.filter(isFlagged).length})
          </label>
        </div>
      )}

      {loading && <p className="text-sm text-slate-400">Loading…</p>}

      {!loading && items.length === 0 && (
        <p className="text-sm text-slate-400">
          {sub === "notes"
            ? "No auto-ingested notes yet. Turn on auto-ingest in the sidebar; when an internet fallback fires, the answer is saved here as a searchable, editable page."
            : sub === "stubs"
              ? "No auto-generated stubs awaiting review."
              : "No saved searches in raw/searches/."}
        </p>
      )}

      <div className="space-y-3">
        {items.map((it) => (
          <ReviewCard
            key={it.id}
            item={it}
            user={user}
            onAfterChange={afterChange}
          />
        ))}
      </div>
    </div>
  );
}
