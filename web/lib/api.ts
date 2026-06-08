// Typed client for the Wiki LM FastAPI backend.
//
// We call the backend DIRECTLY (CORS is open server-side) rather than via the
// Next.js dev rewrite proxy — that proxy drops long POSTs with ECONNRESET on
// some Node versions. Override the target with NEXT_PUBLIC_API_BASE; default is
// the local backend. Set it to "" to fall back to the same-origin rewrite.
const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE !== undefined
    ? process.env.NEXT_PUBLIC_API_BASE
    : "http://localhost:8000";

export interface TokenUsage {
  prompt: number;
  candidates: number;
  total: number;
}

export interface MCOption {
  key: string;
  text: string;
}

export interface MCQuestion {
  label: string;
  question: string;
  options: MCOption[];
  rationale: string;
  captured: boolean;
}

export interface Turn {
  idx: number;
  ts: string;
  question: string;
  answer: string;
  sources: string[];
  origin: "wiki" | "internet" | "mixed";
  gemini_calls: number;
  tokens: TokenUsage;
  mc: MCQuestion | null;
  saved_search_path: string | null;
  stubs_created: string[];
  note_created: string | null;
}

export interface Stats {
  wiki_pages: number;
  decisions: number;
  questions: number;
  session_queries: number;
  session_tokens: number;
  stubs: number;
  searches: number;
  notes: number;
  index_gaps: number;
  cases_available: number;
}

export interface StateResp {
  user: string;
  history: Turn[];
  stats: Stats;
  session_file: string;
}

export interface CaseQuestion {
  label: string;
  text: string;
  options: MCOption[];
  captured: boolean;
}

export interface CaseItem {
  stem: string;
  title: string;
  skeleton: string;
  questions: CaseQuestion[];
  captured: boolean;
}

export interface ReviewItem {
  id: string;
  stem: string;
  title: string;
  kind: "stub" | "search" | "note";
  mtime: string | null;
  verified?: boolean;
  verified_by?: string;
  verified_date?: string;
  auto_date?: string;
}

export interface GrowItem {
  q: string;
  strategy: "referential" | "depth" | "coverage";
  reason: string;
  coverage: number;
  nearest: string;
}

export interface GrowRunState {
  done: number;
  total: number;
  created: number;
  covered: number;
  failed: number;
}

export interface PageDetail {
  id: string;
  title: string;
  content: string;
  body: string;
  frontmatter: Record<string, string>;
  mtime: string;
}

async function req<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...opts,
    headers: { "Content-Type": "application/json", ...(opts?.headers || {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  health: () => req<{ api_key_present: boolean; model_pro: string; model_flash: string }>("/api/health"),

  state: (user: string) => req<StateResp>(`/api/state?user=${encodeURIComponent(user)}`),

  query: (question: string, user: string, auto_ingest: boolean) =>
    req<{ turn: Turn; needs_ingest: boolean; token: string | null }>("/api/query", {
      method: "POST",
      body: JSON.stringify({ question, user, auto_ingest }),
    }),

  finalize: (token: string, user: string) =>
    req<{ turn: Turn; warnings: string[] }>("/api/query/finalize", {
      method: "POST",
      body: JSON.stringify({ token, user }),
    }),

  probe: (user: string, turn_idx: number) =>
    req<{ turn: Turn }>("/api/preference/probe", {
      method: "POST",
      body: JSON.stringify({ user, turn_idx }),
    }),

  preference: (user: string, turn_idx: number, choice_key: string, reasoning: string) =>
    req<{ ok: boolean; turn: Turn }>("/api/preference", {
      method: "POST",
      body: JSON.stringify({ user, turn_idx, choice_key, reasoning }),
    }),

  cases: (user: string) => req<{ cases: CaseItem[] }>(`/api/cases?user=${encodeURIComponent(user)}`),

  caseAnswer: (
    user: string,
    case_stem: string,
    question_label: string,
    selected_keys: string[],
    comment: string,
  ) =>
    req<{ ok: boolean }>("/api/cases/answer", {
      method: "POST",
      body: JSON.stringify({ user, case_stem, question_label, selected_keys, comment }),
    }),

  stubs: () => req<{ items: ReviewItem[] }>("/api/review/stubs"),
  searches: () => req<{ items: ReviewItem[] }>("/api/review/searches"),
  notes: () => req<{ items: ReviewItem[] }>("/api/review/notes"),

  growProposal: () => req<{ items: GrowItem[]; saved: boolean }>("/api/grow/proposal"),

  growPropose: (depth_sample = 6, top = 30, covered = 0.82) =>
    req<{ items: GrowItem[] }>("/api/grow/propose", {
      method: "POST",
      body: JSON.stringify({ depth_sample, top, covered }),
    }),

  indexGaps: () => req<{ gaps: string[] }>("/api/review/index-gaps"),

  reconcile: (user: string) =>
    req<{ ok: boolean; added: string[] }>("/api/review/reconcile", {
      method: "POST",
      body: JSON.stringify({ id: "", user }),
    }),

  verify: (id: string, user: string) =>
    req<{ ok: boolean }>("/api/review/verify", {
      method: "POST",
      body: JSON.stringify({ id, user }),
    }),

  deleteNote: (id: string, user: string, reason: string) =>
    req<{ ok: boolean }>("/api/review/delete-note", {
      method: "POST",
      body: JSON.stringify({ id, user, reason }),
    }),

  page: (id: string) => req<PageDetail>(`/api/page?id=${encodeURIComponent(id)}`),

  savePage: (id: string, content: string) =>
    req<{ ok: boolean }>("/api/page", {
      method: "POST",
      body: JSON.stringify({ id, content }),
    }),

  promote: (id: string, user: string) =>
    req<{ ok: boolean }>("/api/review/promote", {
      method: "POST",
      body: JSON.stringify({ id, user }),
    }),

  reject: (id: string, user: string, reason: string) =>
    req<{ ok: boolean }>("/api/review/reject", {
      method: "POST",
      body: JSON.stringify({ id, user, reason }),
    }),

  deleteSearch: (id: string, user: string, reason: string) =>
    req<{ ok: boolean }>("/api/review/delete-search", {
      method: "POST",
      body: JSON.stringify({ id, user, reason }),
    }),
};
