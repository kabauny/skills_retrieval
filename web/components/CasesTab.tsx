"use client";

import { useCallback, useEffect, useState } from "react";
import { api, CaseItem, CaseQuestion } from "@/lib/api";
import Markdown from "./Markdown";

function QuestionBlock({
  user,
  caseStem,
  q,
  index,
  onSaved,
}: {
  user: string;
  caseStem: string;
  q: CaseQuestion;
  index: number;
  onSaved: () => void;
}) {
  const [selected, setSelected] = useState<string[]>([]);
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const toggle = (k: string) =>
    setSelected((prev) =>
      prev.includes(k) ? prev.filter((x) => x !== k) : [...prev, k],
    );

  const save = async () => {
    if (selected.length === 0 && !comment.trim()) {
      setMsg("Pick at least one option or leave a comment.");
      return;
    }
    setSaving(true);
    try {
      await api.caseAnswer(user, caseStem, q.label, selected, comment);
      setMsg("Saved to decisions.md");
      setSelected([]);
      setComment("");
      onSaved();
    } catch (e: any) {
      setMsg(`Failed: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="border border-slate-200 rounded-lg p-4">
      <p className="font-medium text-sm mb-2">
        Q{index}. {q.captured && <span className="text-green-600">✓ </span>}
        {q.text}
      </p>
      {q.captured && (
        <p className="text-[11px] text-slate-400 mb-2">
          Already answered. Saving again appends a fresh entry (useful as your
          reasoning evolves).
        </p>
      )}
      <div className="space-y-1.5">
        {q.options.map((o) => (
          <label
            key={o.key}
            className="flex gap-2 items-start text-sm cursor-pointer"
          >
            <input
              type="checkbox"
              checked={selected.includes(o.key)}
              onChange={() => toggle(o.key)}
              className="mt-0.5"
            />
            <span>
              <strong>{o.key}.</strong> {o.text}
            </span>
          </label>
        ))}
      </div>
      <textarea
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        rows={2}
        placeholder="Comment (optional — reasoning, caveats, anything to record)"
        className="mt-3 w-full border border-slate-300 rounded-md px-2 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
      />
      <div className="flex items-center gap-3 mt-2">
        <button onClick={save} disabled={saving} className="btn-primary">
          {saving ? "Saving…" : "Save this answer"}
        </button>
        {msg && <span className="text-xs text-slate-500">{msg}</span>}
      </div>
    </div>
  );
}

function CaseBlock({
  user,
  c,
  onSaved,
}: {
  user: string;
  c: CaseItem;
  onSaved: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [showSkeleton, setShowSkeleton] = useState(false);
  const answered = c.questions.filter((q) => q.captured).length;

  return (
    <div className="border border-slate-200 rounded-lg bg-white overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 text-left"
      >
        <span className="font-medium text-sm">
          {c.captured ? "✓ " : "📋 "}
          {c.title}
        </span>
        <span className="text-xs text-slate-400">
          {answered}/{c.questions.length} answered {open ? "▾" : "▸"}
        </span>
      </button>

      {open && (
        <div className="px-4 pb-4 border-t border-slate-100 pt-3 space-y-3">
          <p className="text-[11px] text-slate-400">
            Source: <code>{c.stem}</code>
          </p>

          {c.skeleton && (
            <div>
              <button
                onClick={() => setShowSkeleton(!showSkeleton)}
                className="btn-ghost"
              >
                {showSkeleton ? "Hide" : "📖 Show"} decision skeleton
              </button>
              {showSkeleton && (
                <div className="mt-2 border border-slate-200 rounded-md p-3 bg-slate-50">
                  <Markdown>{c.skeleton}</Markdown>
                </div>
              )}
            </div>
          )}

          {c.questions.map((q, i) => (
            <QuestionBlock
              key={q.label}
              user={user}
              caseStem={c.stem}
              q={q}
              index={i + 1}
              onSaved={onSaved}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export default function CasesTab({
  user,
  onAfterChange,
}: {
  user: string;
  onAfterChange: () => void;
}) {
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    api
      .cases(user)
      .then((r) => setCases(r.cases))
      .finally(() => setLoading(false));
  }, [user]);

  useEffect(() => {
    load();
  }, [load]);

  const onSaved = () => {
    load();
    onAfterChange();
  };

  const available = cases.filter((c) => !c.captured);
  const captured = cases.filter((c) => c.captured);

  return (
    <div className="px-6 py-5 max-w-3xl mx-auto">
      <h2 className="text-lg font-semibold mb-1">Captureable cases</h2>
      <p className="text-sm text-slate-500 mb-5">
        Concept pages with a <code>## Questions</code> section. Each question
        saves independently to <code>wiki/avatar/{user}/decisions.md</code>.
      </p>

      {loading && <p className="text-sm text-slate-400">Loading cases…</p>}

      {!loading && cases.length === 0 && (
        <p className="text-sm text-slate-400">
          No concept pages with a <code>## Questions</code> section found.
        </p>
      )}

      {available.length > 0 && (
        <>
          <h3 className="text-sm font-semibold text-slate-600 mb-2">To capture</h3>
          <div className="space-y-2 mb-6">
            {available.map((c) => (
              <CaseBlock key={c.stem} user={user} c={c} onSaved={onSaved} />
            ))}
          </div>
        </>
      )}

      {captured.length > 0 && (
        <>
          <h3 className="text-sm font-semibold text-slate-600 mb-2">
            Already captured (revisit / revise)
          </h3>
          <div className="space-y-2">
            {captured.map((c) => (
              <CaseBlock key={c.stem} user={user} c={c} onSaved={onSaved} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
