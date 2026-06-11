"use client";

import { useEffect, useState } from "react";
import { Stats } from "@/lib/api";

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex justify-between text-sm py-1">
      <span className="text-slate-500">{label}</span>
      <span className="font-semibold tabular-nums">{value}</span>
    </div>
  );
}

export default function Sidebar({
  user,
  onUserChange,
  autoIngest,
  onAutoIngestChange,
  stats,
  sessionFile,
}: {
  user: string;
  onUserChange: (u: string) => void;
  autoIngest: boolean;
  onAutoIngestChange: (v: boolean) => void;
  stats?: Stats;
  sessionFile?: string;
}) {
  const [draft, setDraft] = useState(user);
  useEffect(() => setDraft(user), [user]);

  const commitUser = () => {
    const v = draft.trim().toLowerCase();
    if (v && v !== user) onUserChange(v);
  };

  return (
    <aside className="w-72 shrink-0 bg-white border-r border-slate-200 flex flex-col overflow-y-auto">
      <div className="p-5">
        <h1 className="text-xl font-bold flex items-center gap-2">📚 Wiki LM</h1>
        <p className="text-xs text-slate-500 mt-1 leading-relaxed">
          Local oncology KB + avatar capture
        </p>
      </div>

      <div className="px-5 pb-4 border-b border-slate-100">
        <label className="text-xs font-medium text-slate-500 uppercase tracking-wide">
          Active user
        </label>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commitUser}
          onKeyDown={(e) => e.key === "Enter" && commitUser()}
          className="mt-1 w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
        <p className="text-[11px] text-slate-400 mt-1">
          Avatar layer targets <code>wiki/avatar/{user}/</code>
        </p>
      </div>

      <div className="px-5 py-4 border-b border-slate-100">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={autoIngest}
            onChange={(e) => onAutoIngestChange(e.target.checked)}
            className="rounded"
          />
          <span className="text-sm font-medium">Auto-ingest grounded searches</span>
        </label>
        <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
          On by default. When on, an internet-fallback answer is saved as a
          searchable, editable note (Review → Notes) and indexed — so asking the
          same question again is answered locally, no re-search.
        </p>
      </div>

      <div className="px-5 py-4 border-b border-slate-100">
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Wiki state
        </h2>
        <Metric label="Shared pages" value={stats?.wiki_pages ?? "—"} />
        <Metric label={`Decisions (${user})`} value={stats?.decisions ?? "—"} />
        <Metric label={`Questions (${user})`} value={stats?.questions ?? "—"} />
      </div>

      <div className="px-5 py-4">
        <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Session
        </h2>
        <Metric label="Queries today" value={stats?.session_queries ?? "—"} />
        <Metric
          label="Tokens today"
          value={stats ? stats.session_tokens.toLocaleString() : "—"}
        />
        {sessionFile && (
          <p className="text-[11px] text-slate-400 mt-2 break-all">
            <code>{sessionFile}</code>
          </p>
        )}
      </div>

      <div className="mt-auto px-5 py-4 text-[11px] text-slate-400 border-t border-slate-100">
        Pro: synthesis + MC probe · Flash: routing + extraction
      </div>
    </aside>
  );
}
