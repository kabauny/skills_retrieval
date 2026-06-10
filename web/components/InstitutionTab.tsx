"use client";

import { useEffect, useMemo, useState } from "react";
import { api, InstitutionData } from "@/lib/api";

const STATUS_COLOR: Record<string, string> = {
  preferred: "bg-emerald-100 text-emerald-700",
  "on-formulary": "bg-blue-100 text-blue-700",
  restricted: "bg-amber-100 text-amber-700",
  "non-formulary": "bg-rose-100 text-rose-700",
  biosimilar: "bg-violet-100 text-violet-700",
};

// Institutional policy overlay — formulary status + preferred pathways. These
// preference-weight the recommendation at answer time (lead with preferred, flag
// off-formulary). Shared across providers (one institution).
export default function InstitutionTab() {
  const [data, setData] = useState<InstitutionData | null>(null);
  const [sub, setSub] = useState<"formulary" | "pathways">("formulary");
  const [filter, setFilter] = useState("");
  const [disease, setDisease] = useState("");
  const [pathwayText, setPathwayText] = useState("");
  const [saved, setSaved] = useState<string | null>(null);

  const load = () => api.institution().then(setData);
  useEffect(() => {
    load();
  }, []);

  const flash = (m: string) => {
    setSaved(m);
    setTimeout(() => setSaved(null), 1500);
  };

  const saveFormulary = async (drug: string, status: string, note: string) => {
    setData((d) =>
      d
        ? {
            ...d,
            formulary: status
              ? { ...d.formulary, [drug]: { status, note } }
              : Object.fromEntries(Object.entries(d.formulary).filter(([k]) => k !== drug)),
          }
        : d,
    );
    await api.setFormulary(drug, status, note);
    flash(`Saved ${drug}`);
  };

  const savePathway = async () => {
    if (!disease) return;
    await api.setPathway(disease, pathwayText);
    setData((d) =>
      d
        ? {
            ...d,
            pathways: pathwayText.trim()
              ? { ...d.pathways, [disease]: pathwayText.trim() }
              : Object.fromEntries(Object.entries(d.pathways).filter(([k]) => k !== disease)),
          }
        : d,
    );
    flash("Pathway saved");
  };

  const drugs = useMemo(() => {
    if (!data) return [];
    const f = filter.trim().toLowerCase();
    // show drugs with a status set first, then matches to the filter
    return data.drugs
      .filter((d) => (f ? d.title.toLowerCase().includes(f) || d.stem.includes(f) : data.formulary[d.stem]))
      .slice(0, 60);
  }, [data, filter]);

  if (!data) return <div className="px-6 py-5 text-sm text-slate-400">Loading…</div>;

  const setCount = Object.keys(data.formulary).length;
  const pathCount = Object.keys(data.pathways).length;

  return (
    <div className="px-6 py-5 max-w-3xl mx-auto">
      <h2 className="text-lg font-semibold mb-1">Institutional preferences</h2>
      <p className="text-sm text-slate-500 mb-4">
        Your institution&apos;s formulary status and preferred pathways. These{" "}
        <span className="font-medium">preference-weight</span> answers — the
        recommendation leads with the preferred option and flags off-formulary
        choices, without hiding the evidence.
      </p>

      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setSub("formulary")}
          className={sub === "formulary" ? "btn-primary" : "btn-ghost"}
        >
          💊 Formulary ({setCount})
        </button>
        <button
          onClick={() => setSub("pathways")}
          className={sub === "pathways" ? "btn-primary" : "btn-ghost"}
        >
          🧭 Preferred pathways ({pathCount})
        </button>
        {saved && <span className="ml-auto text-xs text-green-700 self-center">✓ {saved}</span>}
      </div>

      {sub === "formulary" && (
        <div>
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter drugs to set status (empty = show only ones already set)…"
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm mb-3 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          {drugs.length === 0 && (
            <p className="text-sm text-slate-400">
              {filter ? "No matching drugs." : "No statuses set yet — type a drug name to begin."}
            </p>
          )}
          <div className="space-y-1.5">
            {drugs.map((d) => {
              const cur = data.formulary[d.stem];
              return (
                <div
                  key={d.stem}
                  className="flex items-center gap-2 border border-slate-200 rounded-md px-3 py-2"
                >
                  <span className="text-sm font-medium w-48 truncate" title={d.title}>
                    {d.title}
                  </span>
                  <select
                    value={cur?.status || ""}
                    onChange={(e) => saveFormulary(d.stem, e.target.value, cur?.note || "")}
                    className={`text-xs rounded-full px-2 py-1 border-0 ${
                      cur ? STATUS_COLOR[cur.status] || "bg-slate-100" : "bg-slate-100 text-slate-500"
                    }`}
                  >
                    <option value="">— unset —</option>
                    {data.statuses.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                  <input
                    defaultValue={cur?.note || ""}
                    onBlur={(e) => {
                      if (cur && e.target.value !== cur.note)
                        saveFormulary(d.stem, cur.status, e.target.value);
                    }}
                    placeholder="note (e.g. prior auth, biosimilar X)"
                    className="flex-1 text-xs border border-slate-200 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-400"
                  />
                </div>
              );
            })}
          </div>
        </div>
      )}

      {sub === "pathways" && (
        <div>
          <select
            value={disease}
            onChange={(e) => {
              setDisease(e.target.value);
              setPathwayText(data.pathways[e.target.value] || "");
            }}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm mb-3"
          >
            <option value="">Select a disease…</option>
            {data.diseases.map((d) => (
              <option key={d.stem} value={d.stem}>
                {d.title}
                {data.pathways[d.stem] ? "  ✓" : ""}
              </option>
            ))}
          </select>
          {disease && (
            <>
              <textarea
                value={pathwayText}
                onChange={(e) => setPathwayText(e.target.value)}
                placeholder={"Preferred regimen by line, e.g.:\nfirst-line: carbo + pemetrexed + pembrolizumab (non-squamous)\nsecond-line: docetaxel ± ramucirumab"}
                className="w-full h-40 text-sm border border-slate-300 rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <button onClick={savePathway} className="btn-primary mt-2">
                Save pathway
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
