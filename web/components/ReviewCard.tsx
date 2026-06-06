"use client";

import { useState } from "react";
import { api, ReviewItem } from "@/lib/api";
import Markdown from "./Markdown";

export default function ReviewCard({
  item,
  user,
  onAfterChange,
}: {
  item: ReviewItem;
  user: string;
  onAfterChange: () => void;
}) {
  const [viewing, setViewing] = useState(false);
  const [editing, setEditing] = useState(false);
  const [body, setBody] = useState<string | null>(null);
  const [content, setContent] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [reason, setReason] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [gone, setGone] = useState(false);

  const isStub = item.kind === "stub";
  const isNote = item.kind === "note";
  const [verified, setVerified] = useState(!!item.verified);
  const [verifiedBy, setVerifiedBy] = useState(item.verified_by || "");
  const [verifiedDate, setVerifiedDate] = useState(item.verified_date || "");

  const loadContent = async () => {
    if (content !== null) return;
    const p = await api.page(item.id);
    setBody(p.body);
    setContent(p.content);
  };

  const toggleView = async () => {
    if (!viewing) await loadContent();
    setViewing(!viewing);
  };

  const toggleEdit = async () => {
    if (!editing) await loadContent();
    setEditing(!editing);
  };

  const save = async () => {
    if (content === null) return;
    await api.savePage(item.id, content);
    setMsg("Saved.");
    setEditing(false);
    onAfterChange();
  };

  const promote = async () => {
    try {
      await api.promote(item.id, user);
      setGone(true);
      onAfterChange();
    } catch (e: any) {
      setMsg(`Promote failed: ${e.message}`);
    }
  };

  const verify = async () => {
    try {
      await api.verify(item.id, user);
      setVerified(true);
      setVerifiedBy(user);
      setVerifiedDate(new Date().toISOString().slice(0, 10));
      setMsg("Marked verified.");
      onAfterChange();
    } catch (e: any) {
      setMsg(`Verify failed: ${e.message}`);
    }
  };

  const confirmRemove = async () => {
    try {
      if (isStub) await api.reject(item.id, user, reason);
      else if (isNote) await api.deleteNote(item.id, user, reason);
      else await api.deleteSearch(item.id, user, reason);
      setGone(true);
      onAfterChange();
    } catch (e: any) {
      setMsg(`Failed: ${e.message}`);
    }
  };

  if (gone) {
    return (
      <div className="border border-slate-200 rounded-lg p-3 text-sm text-slate-400 italic">
        {isStub ? "Removed" : "Deleted"}: {item.title}
      </div>
    );
  }

  return (
    <div className="border border-slate-200 rounded-lg p-4 bg-white">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h4 className="font-semibold text-sm truncate">{item.title}</h4>
            {isNote &&
              (verified ? (
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-green-100 text-green-700">
                  ✓ verified{verifiedBy ? ` · ${verifiedBy}` : ""}
                  {verifiedDate ? ` · ${verifiedDate}` : ""}
                </span>
              ) : (
                <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700">
                  🌱 unverified
                </span>
              ))}
          </div>
          <p className="text-[11px] text-slate-400 mt-0.5">
            <code>{item.id}</code>
            {isNote && item.auto_date && ` · ingested ${item.auto_date}`}
            {!isNote && item.mtime && ` · ${new Date(item.mtime).toLocaleString()}`}
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mt-3">
        <button onClick={toggleView} className="btn-ghost">
          {viewing ? "Hide" : "View"}
        </button>
        <button onClick={toggleEdit} className="btn-ghost">
          {editing ? "Close edit" : "Edit"}
        </button>
        {isStub && (
          <button onClick={promote} className="btn-primary">
            Promote
          </button>
        )}
        {isNote && !verified && (
          <button onClick={verify} className="btn-primary">
            Mark verified
          </button>
        )}
        <button onClick={() => setConfirming(true)} className="btn-danger">
          {isStub ? "Reject" : "Delete"}
        </button>
      </div>

      {confirming && (
        <div className="mt-3 border border-amber-200 bg-amber-50 rounded-md p-3 text-sm">
          <p className="text-amber-800">
            Confirm {isStub ? "rejection" : "deletion"} of <code>{item.id}</code>.
            Recoverable via <code>git restore</code>.
          </p>
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Reason (optional, logged)"
            className="mt-2 w-full border border-slate-300 rounded px-2 py-1 text-sm"
          />
          <div className="flex gap-2 mt-2">
            <button onClick={confirmRemove} className="btn-danger">
              Yes, proceed
            </button>
            <button onClick={() => setConfirming(false)} className="btn-ghost">
              Cancel
            </button>
          </div>
        </div>
      )}

      {viewing && body !== null && (
        <div className="mt-3 border-t border-slate-100 pt-3 max-h-96 overflow-y-auto">
          <Markdown>{body}</Markdown>
        </div>
      )}

      {editing && content !== null && (
        <div className="mt-3 border-t border-slate-100 pt-3">
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full h-80 font-mono text-[12px] border border-slate-300 rounded p-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
          <button onClick={save} className="btn-primary mt-2">
            Save changes
          </button>
        </div>
      )}

      {msg && <p className="text-xs text-slate-500 mt-2">{msg}</p>}
    </div>
  );
}
