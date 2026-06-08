"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, Turn } from "@/lib/api";
import TurnCard from "./TurnCard";
import ChatInput from "./ChatInput";

export default function ChatTab({
  user,
  autoIngest,
  history,
  setHistory,
  onAfterChange,
  busy,
  setBusy,
  blocked,
}: {
  user: string;
  autoIngest: boolean;
  history: Turn[];
  setHistory: (updater: (prev: Turn[]) => Turn[]) => void;
  onAfterChange: () => void;
  busy: boolean;
  setBusy: (b: boolean) => void;
  blocked: boolean;
}) {
  const [ingestStatus, setIngestStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history.length, busy]);

  // Stable identity so memoized TurnCards don't re-render on every parent render.
  const replaceTurn = useCallback(
    (t: Turn) => setHistory((prev) => prev.map((x) => (x.ts === t.ts ? t : x))),
    [setHistory],
  );

  const submit = async (q: string) => {
    if (!q || busy || blocked) return;
    setError(null);
    setBusy(true);
    try {
      const res = await api.query(q, user, autoIngest);
      setHistory((prev) => [...prev, res.turn]);
      setBusy(false);

      // Phase 2 — deferred save + auto-ingest, runs after the answer is shown.
      if (res.needs_ingest && res.token) {
        setIngestStatus("Saving grounded search + auto-ingesting novel entities…");
        try {
          const fin = await api.finalize(res.token, user);
          replaceTurn(fin.turn);
          const n = fin.turn.stubs_created.length;
          setIngestStatus(
            `✓ Ingest complete${fin.turn.saved_search_path ? " · saved" : ""}${
              n ? ` · ${n} stub(s) created` : ""
            }`,
          );
          setTimeout(() => setIngestStatus(null), 4000);
        } catch (e: any) {
          setIngestStatus(`⚠️ Ingest failed: ${e.message}`);
        }
      }
      onAfterChange();
    } catch (e: any) {
      setError(e.message || "Query failed.");
      setBusy(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-6 py-5">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-lg font-semibold mb-1">Ask the wiki</h2>
          <p className="text-sm text-slate-500 mb-5">
            Wiki-first retrieval — internet fallback only when needed. Equipoise
            becomes a multiple-choice probe to grow your avatar.
          </p>

          {history.length === 0 && !busy && (
            <div className="text-center text-slate-400 text-sm py-16">
              No questions yet today. Ask something below to get started.
            </div>
          )}

          {history.map((t, i) => (
            <TurnCard
              key={t.ts || `idx-${t.idx}-${i}`}
              turn={t}
              user={user}
              onCaptured={replaceTurn}
              onAfterChange={onAfterChange}
            />
          ))}

          {busy && (
            <div className="flex items-center gap-2 text-slate-500 text-sm py-4">
              <span className="animate-spin h-4 w-4 border-2 border-slate-300 border-t-slate-600 rounded-full" />
              Routing through the wiki…
            </div>
          )}

          {ingestStatus && (
            <div className="text-xs text-slate-500 bg-slate-100 rounded-md px-3 py-2 my-2">
              {ingestStatus}
            </div>
          )}

          {error && (
            <div className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2 my-2">
              {error}
            </div>
          )}

          <div ref={bottomRef} />
        </div>
      </div>

      <ChatInput busy={busy} blocked={blocked} onSubmit={submit} />
    </div>
  );
}
