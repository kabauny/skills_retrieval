"use client";

import { useCallback, useEffect, useState } from "react";
import { api, StateResp, Turn } from "@/lib/api";
import Sidebar from "./Sidebar";
import ChatTab from "./ChatTab";
import CasesTab from "./CasesTab";
import ReviewTab from "./ReviewTab";

type Tab = "chat" | "cases" | "review";

const DEFAULT_USER = "jim.chen";

export default function App() {
  const [user, setUser] = useState(DEFAULT_USER);
  const [autoIngest, setAutoIngest] = useState(false);
  const [tab, setTab] = useState<Tab>("chat");
  const [state, setState] = useState<StateResp | null>(null);
  const [apiKeyMissing, setApiKeyMissing] = useState(false);
  const [history, setHistory] = useState<Turn[]>([]);

  const refreshState = useCallback(async (u: string) => {
    const s = await api.state(u);
    setState(s);
    setHistory(s.history);
  }, []);

  useEffect(() => {
    api.health().then((h) => setApiKeyMissing(!h.api_key_present)).catch(() => {});
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
              onAfterChange={() => refreshState(user)}
            />
          )}
          {tab === "cases" && (
            <CasesTab user={user} onAfterChange={() => refreshState(user)} />
          )}
          {tab === "review" && (
            <ReviewTab user={user} onAfterChange={() => refreshState(user)} />
          )}
        </div>
      </main>
    </div>
  );
}
