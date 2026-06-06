"use client";

import { useState } from "react";
import { api, Turn } from "@/lib/api";
import Markdown from "./Markdown";
import ReviewCard from "./ReviewCard";

const ORIGIN_BADGE: Record<Turn["origin"], { label: string; cls: string }> = {
  wiki: { label: "🟢 Wiki only", cls: "bg-green-100 text-green-700" },
  mixed: { label: "🟡 Wiki + internet", cls: "bg-amber-100 text-amber-700" },
  internet: { label: "🌐 Internet only", cls: "bg-blue-100 text-blue-700" },
};

function Collapsible({
  title,
  defaultOpen = false,
  children,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border border-slate-200 rounded-lg mt-2 overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
      >
        <span>{title}</span>
        <span className="text-slate-400">{open ? "▾" : "▸"}</span>
      </button>
      {open && <div className="px-3 py-3 border-t border-slate-100">{children}</div>}
    </div>
  );
}

export default function TurnCard({
  turn,
  user,
  onCaptured,
  onAfterChange,
}: {
  turn: Turn;
  user: string;
  onCaptured: (t: Turn) => void;
  onAfterChange: () => void;
}) {
  const [choice, setChoice] = useState<string>("");
  const [reasoning, setReasoning] = useState("");
  const [saving, setSaving] = useState(false);
  const badge = ORIGIN_BADGE[turn.origin];

  const captureMc = async () => {
    if (!choice || !turn.mc) return;
    setSaving(true);
    try {
      const res = await api.preference(user, turn.idx, choice, reasoning);
      onCaptured(res.turn);
      onAfterChange();
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mb-6">
      {/* user question */}
      <div className="flex justify-end mb-2">
        <div className="bg-blue-600 text-white rounded-2xl rounded-br-sm px-4 py-2 text-sm max-w-[85%]">
          {turn.question}
        </div>
      </div>

      {/* assistant answer */}
      <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-sm p-4">
        <div className="flex flex-wrap items-center gap-2 text-[11px] text-slate-500 mb-2">
          <span className={`px-2 py-0.5 rounded-full font-medium ${badge.cls}`}>
            {badge.label}
          </span>
          <span>{turn.sources.length} pages</span>
          <span>·</span>
          <span>{turn.gemini_calls} Gemini calls</span>
          <span>·</span>
          <span>{turn.tokens.total.toLocaleString()} tokens</span>
        </div>

        <Markdown>{turn.answer}</Markdown>

        {turn.sources.length > 0 && (
          <Collapsible title={`📄 Pages consulted (${turn.sources.length})`}>
            <ul className="text-sm text-slate-600 space-y-1">
              {turn.sources.map((s) => (
                <li key={s}>
                  <code>{s}.md</code>
                </li>
              ))}
            </ul>
          </Collapsible>
        )}

        {turn.saved_search_path && (
          <Collapsible title="💾 Grounded search saved">
            <code className="text-xs break-all">{turn.saved_search_path}</code>
            <p className="text-xs text-slate-400 mt-1">
              Saved in the same format as agent-driven search.py — frontmatter,
              resolved URLs, token tracking.
            </p>
          </Collapsible>
        )}

        {turn.stubs_created.length > 0 && (
          <Collapsible
            title={`🌱 Auto-ingested (${turn.stubs_created.length} stubs) — review inline`}
          >
            <div className="space-y-2">
              {turn.stubs_created.map((p) => {
                const stem = p.split("/").pop()?.replace(/\.md$/, "") || p;
                const rel = p.includes("/wiki/")
                  ? "wiki/" + p.split("/wiki/")[1]
                  : p;
                return (
                  <ReviewCard
                    key={p}
                    item={{
                      id: rel,
                      stem,
                      title: stem,
                      kind: "stub",
                      mtime: null,
                    }}
                    user={user}
                    onAfterChange={onAfterChange}
                  />
                );
              })}
            </div>
          </Collapsible>
        )}

        {turn.note_created && (
          <div className="mt-2 text-xs text-emerald-700 bg-emerald-50 border border-emerald-200 rounded-md px-3 py-2">
            📝 Saved as a searchable note — ask this again and it'll be answered
            from the wiki, no internet call. Review/verify it under{" "}
            <strong>Review → Notes</strong>.
          </div>
        )}

        {/* MC preference probe */}
        {turn.mc && !turn.mc.captured && (
          <div className="mt-3 border border-indigo-200 bg-indigo-50/50 rounded-lg p-4">
            <p className="text-sm font-semibold text-indigo-900 mb-1">
              🧭 {turn.mc.question}
            </p>
            {turn.mc.rationale && (
              <p className="text-xs text-indigo-700/70 italic mb-3">
                Why this question: {turn.mc.rationale}
              </p>
            )}
            <div className="space-y-1.5">
              {turn.mc.options.map((o) => (
                <label
                  key={o.key}
                  className={`flex gap-2 items-start text-sm rounded-md px-2 py-1.5 cursor-pointer border ${
                    choice === o.key
                      ? "border-indigo-400 bg-white"
                      : "border-transparent hover:bg-white/60"
                  }`}
                >
                  <input
                    type="radio"
                    name={`mc-${turn.idx}`}
                    checked={choice === o.key}
                    onChange={() => setChoice(o.key)}
                    className="mt-0.5"
                  />
                  <span>
                    <strong>{o.key}.</strong> {o.text}
                  </span>
                </label>
              ))}
            </div>
            <input
              value={reasoning}
              onChange={(e) => setReasoning(e.target.value)}
              placeholder="Reasoning (optional)"
              className="mt-3 w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
            />
            <button
              onClick={captureMc}
              disabled={!choice || saving}
              className="btn-primary mt-2"
            >
              {saving ? "Saving…" : "Save preference to avatar"}
            </button>
          </div>
        )}
        {turn.mc && turn.mc.captured && (
          <p className="text-sm text-green-700 mt-3">✓ Preference captured to avatar</p>
        )}
      </div>
    </div>
  );
}
