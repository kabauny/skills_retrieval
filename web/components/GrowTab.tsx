"use client";

import { Dispatch, SetStateAction, useState } from "react";
import { api, GrowItem, GrowRunState } from "@/lib/api";

const STRATEGY_LABEL: Record<GrowItem["strategy"], string> = {
  referential: "🔗 Referential (mentioned but undocumented)",
  depth: "🔍 Depth (follow-ups from existing notes)",
  coverage: "🗺️ Coverage (cancer × line/biomarker gaps)",
};

// State (items/selected/run/log) is lifted to App so it survives tab switches.
export default function GrowTab({
  user,
  onAfterChange,
  items,
  setItems,
  selected,
  setSelected,
  run,
  setRun,
  log,
  setLog,
}: {
  user: string;
  onAfterChange: () => void;
  items: GrowItem[] | null;
  setItems: Dispatch<SetStateAction<GrowItem[] | null>>;
  selected: Set<string>;
  setSelected: Dispatch<SetStateAction<Set<string>>>;
  run: GrowRunState | null;
  setRun: Dispatch<SetStateAction<GrowRunState | null>>;
  log: string[];
  setLog: Dispatch<SetStateAction<string[]>>;
}) {
  const [proposing, setProposing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const propose = async () => {
    setProposing(true);
    setError(null);
    setItems(null);
    setSelected(new Set());
    setRun(null);
    setLog([]);
    try {
      const res = await api.growPropose();
      setItems(res.items);
      // pre-select the biggest gaps (referential + depth) by default
      setSelected(
        new Set(res.items.filter((i) => i.strategy !== "coverage").map((i) => i.q)),
      );
    } catch (e: any) {
      setError(e.message || "Proposal failed.");
    } finally {
      setProposing(false);
    }
  };

  const toggle = (q: string) =>
    setSelected((prev) => {
      const n = new Set(prev);
      n.has(q) ? n.delete(q) : n.add(q);
      return n;
    });

  const runSelected = async () => {
    if (!items) return;
    const queue = items.filter((i) => selected.has(i.q));
    if (!queue.length) return;
    const state: GrowRunState = { done: 0, total: queue.length, created: 0, covered: 0, failed: 0 };
    setRun({ ...state });
    setLog([]);
    for (const item of queue) {
      try {
        const res = await api.query(item.q, user, true); // auto-ingest on
        if (res.needs_ingest && res.token) {
          const fin = await api.finalize(res.token, user);
          if (fin.turn.note_created) {
            state.created++;
            setLog((l) => [`✓ note: ${item.q.slice(0, 70)}`, ...l]);
          } else {
            setLog((l) => [`· saved (no note): ${item.q.slice(0, 60)}`, ...l]);
          }
        } else {
          state.covered++;
          setLog((l) => [`◦ already covered: ${item.q.slice(0, 60)}`, ...l]);
        }
      } catch (e: any) {
        state.failed++;
        setLog((l) => [`✗ failed: ${item.q.slice(0, 55)} — ${e.message}`, ...l]);
      }
      state.done++;
      setRun({ ...state });
    }
    // Drop the just-run questions from the list (they're now notes/covered) and
    // clear selection, so the list reflects reality and you can re-scan for more.
    const ranQs = new Set(queue.map((i) => i.q));
    setItems((prev) => (prev || []).filter((i) => !ranQs.has(i.q)));
    setSelected(new Set());
    onAfterChange();
  };

  const grouped = (s: GrowItem["strategy"]) => (items || []).filter((i) => i.strategy === s);

  return (
    <div className="px-6 py-5 max-w-3xl mx-auto">
      <h2 className="text-lg font-semibold mb-1">Grow the wiki</h2>
      <p className="text-sm text-slate-500 mb-4">
        The agent reads what the wiki has generated and proposes gap-questions
        (deduped against existing pages). Review, select, and run them — approved
        questions flow through auto-ingest into new searchable notes.
      </p>

      <div className="flex items-center gap-3 mb-5">
        <button
          onClick={propose}
          disabled={proposing || (!!run && run.done < run.total)}
          className="btn-primary"
        >
          {proposing ? "Finding gaps… (~30s)" : items ? "Re-scan for gaps" : "Find gaps"}
        </button>
        {items && (
          <span className="text-sm text-slate-500">
            {items.length} proposed · {selected.size} selected
          </span>
        )}
      </div>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2 mb-3">{error}</div>
      )}

      {run && (
        <div className="border border-slate-200 rounded-lg p-3 mb-4 bg-slate-50">
          <div className="text-sm font-medium">
            Running {run.done}/{run.total} · {run.created} notes · {run.covered} already-covered
            {run.failed ? ` · ${run.failed} failed` : ""}
            {run.done < run.total && (
              <span className="ml-2 inline-block animate-spin h-3 w-3 border-2 border-slate-300 border-t-slate-600 rounded-full align-middle" />
            )}
          </div>
          <div className="mt-2 max-h-40 overflow-y-auto text-xs text-slate-600 space-y-0.5">
            {log.map((l, i) => (
              <div key={i}>{l}</div>
            ))}
          </div>
        </div>
      )}

      {items && !items.length && (
        <p className="text-sm text-slate-400">
          No gaps found — the wiki already covers the proposed questions. Build more
          breadth first, then re-scan.
        </p>
      )}

      {items &&
        items.length > 0 &&
        (["referential", "depth", "coverage"] as const).map((strat) => {
          const list = grouped(strat);
          if (!list.length) return null;
          return (
            <div key={strat} className="mb-5">
              <h3 className="text-sm font-semibold text-slate-600 mb-2">
                {STRATEGY_LABEL[strat]} ({list.length})
              </h3>
              <div className="space-y-1.5">
                {list.map((it) => (
                  <label
                    key={it.q}
                    className="flex gap-2 items-start text-sm border border-slate-200 rounded-md px-3 py-2 cursor-pointer hover:bg-slate-50"
                  >
                    <input
                      type="checkbox"
                      checked={selected.has(it.q)}
                      onChange={() => toggle(it.q)}
                      disabled={!!run}
                      className="mt-1"
                    />
                    <span>
                      <span className="font-medium">{it.q}</span>
                      <span className="block text-[11px] text-slate-400 mt-0.5">
                        gap {it.coverage.toFixed(2)} · {it.reason}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </div>
          );
        })}

      {items && items.length > 0 && (
        <div className="sticky bottom-0 bg-paper py-3 border-t border-slate-200">
          <button
            onClick={runSelected}
            disabled={!selected.size || (!!run && run.done < run.total)}
            className="btn-primary"
          >
            {run && run.done < run.total
              ? "Running…"
              : `Run selected (${selected.size}) → new notes`}
          </button>
          {run && run.done === run.total && (
            <span className="ml-3 text-sm text-green-700">
              ✓ Done — {run.created} new note(s) created. Review them under Review → Notes.
            </span>
          )}
        </div>
      )}
    </div>
  );
}
