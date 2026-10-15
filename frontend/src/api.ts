// Tiny fetch wrapper. The session cookie is sent automatically (same origin).
// ponytail: hand-written types mirroring backend/app/schemas; openapi-typescript needs TS 5 (we run 7),
// switch to codegen once it supports TS 7 or the type list outgrows this file.

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init?: { method?: string; body?: unknown; keepalive?: boolean }): Promise<T> {
  const res = await fetch(`/api${path}`, {
    method: init?.method ?? "GET",
    keepalive: init?.keepalive, // lets the last autosave finish while the page closes
    headers: init?.body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: init?.body !== undefined ? JSON.stringify(init.body) : undefined,
  });
  if (!res.ok) {
    const detail = await res.json().then((j) => j.detail, () => res.statusText);
    throw new ApiError(res.status, typeof detail === "string" ? detail : res.statusText);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export type User = { id: number; email: string; display_name: string; target_band: number };

export type Skill = "listening" | "reading" | "writing" | "speaking";
export type Answer = string | string[] | null;
export type Option = { letter: string; text: string };

export type Question = { id: number; number: number; prompt: string; options: Option[] | null };
export type Layout = {
  title: string | null;
  template: string | null;
  table: { columns: string[]; rows: string[][] } | null;
  steps: string[] | null;
};
export type Group = {
  id: number;
  qtype: string;
  instructions: string;
  max_words: number | null;
  options: Option[] | null;
  layout: Layout | null;
  pick: number;
  questions: Question[];
};
export type Passage = { title: string; paragraphs: { label: string; text: string }[]; glossary: Record<string, string> };
export type Part = { number: number; passage: Passage | null; groups: Group[] };

export type Highlight = { id: string; p: string; start: number; end: number; note?: string };
export type UiState = { highlights?: Highlight[]; current?: number };

export type AttemptSection = {
  id: number;
  skill: Skill;
  duration_s: number | null;
  started_at: string | null;
  deadline_at: string | null;
  submitted_at: string | null;
  submit_reason: "user" | "timeout" | null;
  ui_state: UiState;
  responses: { question_id: number; answer: Answer; flagged: boolean }[];
  parts: Part[] | null;
};
export type Attempt = {
  id: number;
  mode: string;
  status: "in_progress" | "completed";
  test_title: string;
  server_now: string;
  sections: AttemptSection[];
};
export type AttemptSummary = {
  id: number;
  mode: string;
  status: "in_progress" | "completed";
  test_title: string;
  skills: Skill[];
  started_at: string;
  bands: (number | null)[];
};
export type MockTest = { id: number; title: string; sections: { skill: Skill; duration_s: number | null }[] };
export type SaveOut = { server_now: string; deadline_at: string | null };

export type ReportQuestion = {
  number: number;
  part: number;
  qtype: string;
  answer: Answer;
  accepted: string[];
  is_correct: boolean;
  error_class: string | null;
  time_ms: number;
  flagged: boolean;
};
export type ReportSection = {
  skill: Skill;
  raw: number;
  total: number;
  band: number;
  band_is_estimate: boolean;
  submit_reason: "user" | "timeout";
  time_used_ms: number;
  by_type: { qtype: string; correct: number; total: number }[];
  parts: { number: number; correct: number; total: number; time_ms: number }[];
  slowest: { number: number; time_ms: number }[];
  questions: ReportQuestion[];
};
export type Report = {
  id: number;
  test_title: string;
  mode: string;
  finished_at: string;
  overall_band: number | null;
  report: { sections: ReportSection[] };
};
