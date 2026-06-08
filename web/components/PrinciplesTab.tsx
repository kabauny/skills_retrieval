"use client";

import { useEffect, useState } from "react";
import { api, PrincipleStatus } from "@/lib/api";

// Reasoning lenses & disease frameworks — the "how to think" layer. Each provider
// can fork any lens to flavor it; editing saves to their personal copy (the shared
// skeleton is never touched). The forked lens drives both how answers are reasoned
// and how the Grow agent frames questions.
export default function PrinciplesTab({ user }: { user: string }) {
  const [items, setItems] = useState<PrincipleStatus[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [forked, setForked] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadList = async () => {
    try {
      const res = await api.principles(user);
      setItems(res.items);
    } catch (e: any) {
      setError(e.message || "Failed to load lenses.");
    }
  };

  useEffect(() => {
    loadList();
    setSelected(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const open = async (stem: string) => {
    setSelected(stem);
    setLoading(true);
    setStatus(null);
    setError(null);
    try {
      const d = await api.principle(stem, user);
      setContent(d.content);
      setForked(d.forked);
    } catch (e: any) {
      setError(e.message || "Failed to load lens.");
    } finally {
      setLoading(false);
    }
  };

  const save = async () => {
    if (!selected) return;
    setSaving(true);
    setStatus(null);
    setError(null);
    try {
      await api.savePrinciple(selected, user, content);
      setForked(true);
      setStatus(`✓ Saved to your personal ${selected}. The shared default is untouched.`);
      loadList();
    } catch (e: any) {
      setError(e.message || "Save failed.");
    } finally {
      setSaving(false);
    }
  };

  const lenses = (items || []).filter((i) => i.principle_kind !== "disease-framework");
  const frameworks = (items || []).filter((i) => i.principle_kind === "disease-framework");

  const listGroup = (label: string, group: PrincipleStatus[]) =>
    group.length > 0 && (
      <div className="mb-4">
        <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">
          {label}
        </h3>
        <div className="space-y-1">
          {group.map((it) => (
            <button
              key={it.stem}
              onClick={() => open(it.stem)}
              className={`w-full text-left text-sm px-3 py-2 rounded-md border transition ${
                selected === it.stem
                  ? "border-blue-400 bg-blue-50"
                  : "border-slate-200 hover:bg-slate-50"
              }`}
            >
              <span className="font-medium">{it.title}</span>
              <span
                className={`ml-2 text-[10px] px-1.5 py-0.5 rounded-full ${
                  it.forked
                    ? "bg-emerald-100 text-emerald-700"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {it.forked ? "🎨 yours" : "shared"}
              </span>
            </button>
          ))}
        </div>
      </div>
    );

  return (
    <div className="px-6 py-5 max-w-5xl mx-auto">
      <h2 className="text-lg font-semibold mb-1">Reasoning lenses</h2>
      <p className="text-sm text-slate-500 mb-5">
        The “how to think” layer. These shape how answers are reasoned and how the
        Grow agent frames questions. Fork any lens to flavor it to your practice —
        editing saves to <span className="font-medium">your</span> personal copy;
        the shared default stays untouched.
      </p>

      {error && (
        <div className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2 mb-3">{error}</div>
      )}

      <div className="flex gap-6">
        <div className="w-72 shrink-0">
          {!items && <div className="text-sm text-slate-400">Loading…</div>}
          {listGroup("Lenses", lenses)}
          {listGroup("Disease frameworks", frameworks)}
        </div>

        <div className="flex-1 min-w-0">
          {!selected && (
            <div className="text-sm text-slate-400 py-16 text-center">
              Select a lens to view or personalize it.
            </div>
          )}
          {selected && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-sm text-slate-500">
                  Editing <code className="text-slate-700">{selected}</code> for{" "}
                  <span className="font-medium">{user}</span>
                </span>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                    forked ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {forked ? "🎨 your fork" : "shared default — edits will fork"}
                </span>
              </div>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                disabled={loading}
                spellCheck={false}
                className="w-full h-[60vh] font-mono text-xs border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <div className="flex items-center gap-3 mt-2">
                <button onClick={save} disabled={saving || loading} className="btn-primary">
                  {saving ? "Saving…" : "Save to my lens"}
                </button>
                {status && <span className="text-sm text-green-700">{status}</span>}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
