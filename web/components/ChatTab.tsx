"use client";

import { useEffect, useRef, useState } from "react";
import { api, Turn } from "@/lib/api";
import TurnCard from "./TurnCard";

export default function ChatTab({
  user,
  autoIngest,
  history,
  setHistory,
  onAfterChange,
}: {
  user: string;
  autoIngest: boolean;
  history: Turn[];
  setHistory: (updater: (prev: Turn[]) => Turn[]) => void;
  onAfterChange: () => void;
}) {
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [ingestStatus, setIngestStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [history.length, busy]);

  const replaceTurn = (t: Turn) =>
    setHistory((prev) => prev.map((x) => (x.ts === t.ts ? t : x)));

  const submit = async () => {
    const q = input.trim();
    if (!q || busy) return;
    setInput("");
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

      <div className="border-t border-slate-200 bg-white px-6 py-3">
        <div className="max-w-3xl mx-auto flex gap-2 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
            rows={1}
            placeholder="Ask a question (e.g., 'How would you weight T-DXd over T-DM1 in residual disease?')"
            className="flex-1 resize-none border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 max-h-40"
          />
          <button
            onClick={submit}
            disabled={busy || !input.trim()}
            className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-40 hover:bg-blue-700 transition"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
