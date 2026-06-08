"use client";

import { useState } from "react";

// Input is isolated in its own component so keystrokes only re-render this box —
// NOT the chat history (each TurnCard renders Markdown, which is expensive). When
// `input` lived in ChatTab, every keystroke re-rendered all TurnCards → typing lag.
export default function ChatInput({
  busy,
  blocked = false,
  onSubmit,
}: {
  busy: boolean;
  // True while a Grow run is active. Chat and Grow share the same session file
  // with no backend lock, so we block one while the other runs to avoid racing
  // on turn-index assignment / session rewrite.
  blocked?: boolean;
  onSubmit: (text: string) => void;
}) {
  const [input, setInput] = useState("");

  const send = () => {
    const q = input.trim();
    if (!q || busy || blocked) return;
    setInput("");
    onSubmit(q);
  };

  return (
    <div className="border-t border-slate-200 bg-white px-6 py-3">
      <div className="max-w-3xl mx-auto">
        {blocked && (
          <div className="mb-2 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-1.5">
            🌱 A Grow run is in progress — chat is paused until it finishes (they
            share your session, so running both at once could drop a turn).
          </div>
        )}
        <div className="flex gap-2 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
            rows={1}
            disabled={blocked}
            placeholder={
              blocked
                ? "Paused while a Grow run is active…"
                : "Ask a question (e.g., 'How would you weight T-DXd over T-DM1 in residual disease?')"
            }
            className="flex-1 resize-none border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 max-h-40 disabled:bg-slate-100 disabled:cursor-not-allowed"
          />
          <button
            onClick={send}
            disabled={busy || blocked || !input.trim()}
            className="bg-blue-600 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-40 hover:bg-blue-700 transition"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
