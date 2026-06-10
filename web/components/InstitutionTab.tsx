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

// Preference programs ("initiatives"): a PRIMARY institution that leads the
// recommendation + SECONDARY payer programs (e.g. Evolent) surfaced as alignment
// flags. Each initiative holds its own formulary + preferred pathways.
export default function InstitutionTab() {
  const [data, setData] = useState<InstitutionData | null>(null);
  const [initId, setInitId] = useState("institution");
  const [sub, setSub] = useState<"formulary" | "pathways">("formulary");
  const [filter, setFilter] = useState("");
  const [disease, setDisease] = useState("");
  const [pathwayText, setPathwayText] = useState("");
  const [saved, setSaved] = useState<string | null>(null);

  useEffect(() => {
    api.institution().then(setData);
  }, []);

  const init = data?.initiatives[initId];
  const flash = (m: string) => {
    setSaved(m);
    setTimeout(() => setSaved(null), 1500);
  };

  const saveFormulary = async (drug: string, status: string, note: string) => {
    setData((d) => {
      if (!d) return d;
      const inits = { ...d.initiatives };
      const cur = { ...inits[initId] };
      const f = { ...cur.formulary };
      if (status) f[drug] = { status, note };
      else delete f[drug];
      cur.formulary = f;
      inits[initId] = cur;
      return { ...d, initiatives: inits };
    });
    await api.setFormulary(initId, drug, status, note);
    flash(`Saved ${drug}`);
  };

  const savePathway = async () => {
    if (!disease) return;
    await api.setPathway(initId, disease, pathwayText);
    setData((d) => {
      if (!d) return d;
      const inits = { ...d.initiatives };
      const cur = { ...inits[initId] };
      const p = { ...cur.pathways };
      if (pathwayText.trim()) p[disease] = pathwayText.trim();
      else delete p[disease];
      cur.pathways = p;
      inits[initId] = cur;
      return { ...d, initiatives: inits };
    });
    flash("Pathway saved");
  };

  const drugs = useMemo(() => {
    if (!data || !init) return [];
    const f = filter.trim().toLowerCase();
    return data.drugs
      .filter((d) =>
        f ? d.title.toLowerCase().includes(f) || d.stem.includes(f) : init.formulary[d.stem],
      )
      .slice(0, 60);
  }, [data, init, filter]);

  if (!data || !init) return <div className="px-6 py-5 text-sm text-slate-400">Loading…</div>;

  const setCount = Object.keys(init.formulary).length;
  const pathCount = Object.keys(init.pathways).length;

  return (
    <div className="px-6 py-5 max-w-3xl mx-auto">
      <h2 className="text-lg font-semibold mb-1">Preference programs</h2>
      <p className="text-sm text-slate-500 mb-4">
        Your <span className="font-medium">primary</span> institution leads the
        recommendation; <span className="font-medium">secondary</span> programs
        (e.g. Evolent) are surfaced as alignment flags — when a recommendation is
        also on their pathway, the answer says so; when it diverges, it flags a
        possible prior-auth.
      </p>

      <div className="flex items-center gap-2 mb-4">
        <select
          value={initId}
          onChange={(e) => {
            setInitId(e.target.value);
            setDisease("");
            setPathwayText("");
            setFilter("");
          }}
          className="border border-slate-300 rounded-lg px-3 py-2 text-sm"
        >
          {Object.entries(data.initiatives).map(([id, v]) => (
            <option key={id} value={id}>
              {v.label} {v.role === "primary" ? "(primary)" : "(secondary)"}
            </option>
          ))}
        </select>
        <span
          className={`text-[10px] px-2 py-0.5 rounded-full ${
            init.role === "primary"
              ? "bg-emerald-100 text-emerald-700"
              : "bg-slate-100 text-slate-500"
          }`}
        >
          {init.role}
        </span>
        {saved && <span className="ml-auto text-xs text-green-700">✓ {saved}</span>}
      </div>

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
              const cur = init.formulary[d.stem];
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
                    {/* secondary programs may use a free 'on-pathway' status */}
                    {init.role !== "primary" && <option value="on-pathway">on-pathway</option>}
                  </select>
                  <input
                    defaultValue={cur?.note || ""}
                    key={`${d.stem}-${cur?.note || ""}`}
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
              setPathwayText(init.pathways[e.target.value] || "");
            }}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm mb-3"
          >
            <option value="">Select a disease…</option>
            {data.diseases.map((d) => (
              <option key={d.stem} value={d.stem}>
                {d.title}
                {init.pathways[d.stem] ? "  ✓" : ""}
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
