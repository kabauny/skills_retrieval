"use client";

import { useCallback, useEffect, useState } from "react";
import { api, ReviewItem } from "@/lib/api";
import ReviewCard from "./ReviewCard";

export default function ReviewTab({
  user,
  onAfterChange,
}: {
  user: string;
  onAfterChange: () => void;
}) {
  const [sub, setSub] = useState<"notes" | "stubs" | "searches">("notes");
  const [notes, setNotes] = useState<ReviewItem[]>([]);
  const [stubs, setStubs] = useState<ReviewItem[]>([]);
  const [searches, setSearches] = useState<ReviewItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([api.notes(), api.stubs(), api.searches()])
      .then(([n, s, q]) => {
        setNotes(n.items);
        setStubs(s.items);
        setSearches(q.items);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const afterChange = () => {
    load();
    onAfterChange();
  };

  const items = sub === "notes" ? notes : sub === "stubs" ? stubs : searches;

  return (
    <div className="px-6 py-5 max-w-3xl mx-auto">
      <h2 className="text-lg font-semibold mb-1">Review queue</h2>
      <p className="text-sm text-slate-500 mb-4">
        Auto-generated stubs awaiting promotion + saved grounded searches.
        Actions log to <code>wiki/log.md</code>; deletions recover via{" "}
        <code>git restore</code>.
      </p>

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
