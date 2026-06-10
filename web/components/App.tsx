"use client";

import { useCallback, useEffect, useState } from "react";
import { api, StateResp, Turn, GrowItem, GrowRunState } from "@/lib/api";
import Sidebar from "./Sidebar";
import ChatTab from "./ChatTab";
import CasesTab from "./CasesTab";
import ReviewTab from "./ReviewTab";
import GrowTab from "./GrowTab";
import PrinciplesTab from "./PrinciplesTab";
import SearchTab from "./SearchTab";
import InstitutionTab from "./InstitutionTab";

type Tab = "chat" | "cases" | "review" | "grow" | "principles" | "search" | "institution";

const DEFAULT_USER = "jim.chen";

export default function App() {
  const [user, setUser] = useState(DEFAULT_USER);
  const [autoIngest, setAutoIngest] = useState(false);
  const [tab, setTab] = useState<Tab>("chat");
  const [state, setState] = useState<StateResp | null>(null);
  const [apiKeyMissing, setApiKeyMissing] = useState(false);
  const [history, setHistory] = useState<Turn[]>([]);

  // Grow-tab state lives here so it survives tab switches (was lost on unmount).
  const [growItems, setGrowItems] = useState<GrowItem[] | null>(null);
  const [growSelected, setGrowSelected] = useState<Set<string>>(new Set());
  const [growRun, setGrowRun] = useState<GrowRunState | null>(null);
  const [growLog, setGrowLog] = useState<string[]>([]);

  // Shared activity flags so Chat and Grow can guard against running at the same
  // time — they share the same session file (same user) and have no backend lock,
  // so concurrent queries would race on turn-index assignment / session rewrite.
  const [chatBusy, setChatBusy] = useState(false);
  const growActive = !!growRun && growRun.done < growRun.total;

  const refreshState = useCallback(async (u: string) => {
    const s = await api.state(u);
    setState(s);
    setHistory(s.history);
  }, []);

  // Stable across renders (only changes when `user` does) so memoized children
  // like TurnCard don't re-render on every parent render.
  const onAfterChange = useCallback(() => refreshState(user), [user, refreshState]);

  useEffect(() => {
    api.health().then((h) => setApiKeyMissing(!h.api_key_present)).catch(() => {});
    // Load the last saved proposal so the Grow tab is populated without
    // regenerating (survives reloads); drops questions already run into notes.
    api
      .growProposal()
      .then((r) => {
        if (r.items.length) {
          setGrowItems(r.items);
          setGrowSelected(
            new Set(r.items.filter((i) => i.strategy !== "coverage").map((i) => i.q)),
          );
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    refreshState(user).catch(() => setState(null));
  }, [user, refreshState]);

  const tabs: { id: Tab; label: string }[] = [
    { id: "chat", label: "💬 Chat" },
    {
      id: "cases",
      label: `📚 Cases${state ? ` (${state.stats.cases_available})` : ""}`,
    },
    {
      id: "review",
      label: `📋 Review${state ? ` (${state.stats.notes} notes)` : ""}`,
    },
    { id: "grow", label: "🌱 Grow" },
    { id: "principles", label: "🧭 Lenses" },
    { id: "institution", label: "🏥 Institution" },
    { id: "search", label: "🔎 Search" },
  ];

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar
        user={user}
        onUserChange={setUser}
        autoIngest={autoIngest}
        onAutoIngestChange={setAutoIngest}
        stats={state?.stats}
        sessionFile={state?.session_file}
      />

      <main className="flex-1 flex flex-col overflow-hidden">
        {apiKeyMissing && (
          <div className="bg-red-50 text-red-700 text-sm px-6 py-2 border-b border-red-200">
            ⚠️ GOOGLE_API_KEY not configured on the server — queries will fail. Add
            it to <code>.env</code> and restart the API.
          </div>
        )}

        <div className="flex gap-1 px-6 pt-4 border-b border-slate-200 bg-white">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`px-4 py-2 text-sm font-medium rounded-t-lg transition ${
                tab === t.id
                  ? "bg-paper text-ink border border-b-0 border-slate-200"
                  : "text-slate-500 hover:text-slate-800"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="flex-1 overflow-y-auto">
          {tab === "chat" && (
            <ChatTab
              user={user}
              autoIngest={autoIngest}
              history={history}
              setHistory={setHistory}
              onAfterChange={onAfterChange}
              busy={chatBusy}
              setBusy={setChatBusy}
              blocked={growActive}
            />
          )}
          {tab === "cases" && (
            <CasesTab user={user} onAfterChange={onAfterChange} />
          )}
          {tab === "review" && (
            <ReviewTab user={user} onAfterChange={onAfterChange} />
          )}
          {tab === "grow" && (
            <GrowTab
              user={user}
              onAfterChange={onAfterChange}
              chatBusy={chatBusy}
              items={growItems}
              setItems={setGrowItems}
              selected={growSelected}
              setSelected={setGrowSelected}
              run={growRun}
              setRun={setGrowRun}
              log={growLog}
              setLog={setGrowLog}
            />
          )}
          {tab === "principles" && <PrinciplesTab user={user} />}
          {tab === "institution" && <InstitutionTab />}
          {tab === "search" && <SearchTab />}
        </div>
      </main>
    </div>
  );
}
