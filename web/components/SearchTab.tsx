"use client";

import { useEffect, useRef, useState } from "react";
import { api, SearchResult, PageDetail } from "@/lib/api";
import Markdown from "./Markdown";

const KIND_COLOR: Record<string, string> = {
  entities: "bg-blue-100 text-blue-700",
  principles: "bg-violet-100 text-violet-700",
  concepts: "bg-amber-100 text-amber-700",
  notes: "bg-emerald-100 text-emerald-700",
  sources: "bg-slate-100 text-slate-600",
};

// Instant lexical known-item search — for when you know what you're looking for
// (complements the semantic Chat/graph retrieval). Debounced; click a result to
// read the rendered page.
export default function SearchTab() {
  const [q, setQ] = useState("");
  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [page, setPage] = useState<PageDetail | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);
  const seq = useRef(0);

  useEffect(() => {
    const term = q.trim();
    if (!term) {
      setResults(null);
      setSearching(false);
      return;
    }
    setSearching(true);
    const mine = ++seq.current;
    const t = setTimeout(async () => {
      try {
        const res = await api.search(term);
        if (mine === seq.current) setResults(res.results);
      } catch {
        if (mine === seq.current) setResults([]);
      } finally {
        if (mine === seq.current) setSearching(false);
      }
    }, 220);
    return () => clearTimeout(t);
  }, [q]);

  const open = async (id: string) => {
    setOpenId(id);
    setPage(null);
    try {
      setPage(await api.page(id));
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="flex h-full">
      {/* left: query + results */}
      <div className="w-[26rem] shrink-0 border-r border-slate-200 flex flex-col">
        <div className="px-4 py-3 border-b border-slate-200">
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search pages by content, title, or alias…"
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <div className="text-[11px] text-slate-400 mt-1 h-4">
            {searching
              ? "searching…"
              : results
                ? `${results.length} result${results.length === 1 ? "" : "s"}`
                : "type to search — instant, no AI"}
          </div>
        </div>
        <div className="flex-1 overflow-y-auto">
          {results && results.length === 0 && !searching && (
            <div className="text-sm text-slate-400 px-4 py-6">No matches.</div>
          )}
          {results?.map((r) => (
            <button
              key={r.id}
              onClick={() => open(r.id)}
              className={`w-full text-left px-4 py-2.5 border-b border-slate-100 hover:bg-slate-50 ${
                openId === r.id ? "bg-blue-50" : ""
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium truncate">{r.title}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded-full shrink-0 ${
                    KIND_COLOR[r.kind] || "bg-slate-100 text-slate-600"
                  }`}
                >
                  {r.kind}
                </span>
              </div>
              <div className="text-[11px] text-slate-500 mt-0.5 line-clamp-2">{r.snippet}</div>
            </button>
          ))}
        </div>
      </div>

      {/* right: rendered page */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {!openId && (
          <div className="text-center text-slate-400 text-sm py-20">
            Select a result to read the page.
          </div>
        )}
        {openId && !page && <div className="text-sm text-slate-400">Loading…</div>}
        {page && (
          <div className="max-w-3xl mx-auto">
            <div className="text-xs text-slate-400 mb-2 font-mono">{page.id}</div>
            <Markdown>{page.body}</Markdown>
          </div>
        )}
      </div>
    </div>
  );
}
