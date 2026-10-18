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
export type Segment = { speaker: string; start_ms: number; end_ms: number; text: string; answer_s?: number | null };
export type CueCard = { task: string; bullets: string[]; final: string };
export type WritingTask = { id: number; task_number: number; prompt: string; visual_url: string | null };
export type Part = {
  number: number;
  passage: Passage | null;
  audio: { url: string; duration_ms: number } | null;
  transcript: Segment[] | null; // Listening practice; Speaking (the examiner's lines)
  writing: WritingTask | null;
  cue_card?: CueCard | null; // Speaking Part 2
  groups: Group[];
};

export type Highlight = { id: string; p: string; start: number; end: number; note?: string; ev?: number /* practice evidence: question id */ };
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
  feedback: Feedback[];
  essays: { writing_task_id: number; text: string }[];
  recorded: { part_number: number; line_no: number }[]; // Speaking: answers already uploaded
};
export type Feedback = {
  question_id: number;
  group_id: number;
  number: number;
  answer: Answer;
  accepted: string[];
  is_correct: boolean;
  error_class: string | null;
  explanation: { correct: string; distractors: { option: string; why_wrong: string }[] };
  evidence: { paragraph: string; quote: string };
};
export type PracticeGroup = {
  group_id: number;
  qtype: string;
  topic: string;
  topic_label: string;
  level: "easy" | "medium" | "hard";
  questions: number;
  seen: boolean;
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
  skill: "listening" | "reading";
  raw: number;
  total: number;
  band: number | null; // null for practice
  band_is_estimate: boolean;
  submit_reason: "user" | "timeout";
  time_used_ms: number;
  time_on_questions_ms: number;
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
  overall_band: number | null; // full mock only, once every section has a band
  overall_is_estimate: boolean;
  report: { sections: (ReportSection | WritingReport | SpeakingReport)[] };
};
export type Criterion = { band: number; justification: string; evidence: string[] };
export type EssayResult = {
  criteria: Record<string, Criterion>; // Writing: task, coherence_cohesion, lexical_resource, grammar (Speaking: see SpeakingReport)
  task_band: number; // unrounded mean of the four criteria
  runs: number;
  inconsistent: boolean;
  errors: { category: string; original: string; correction: string; explanation: string }[];
  weakness_tags: string[];
  to_reach_next_half_band: string[];
  improved_paragraph_example: string;
  off_topic_flags: string[];
};
export type WritingReport = {
  skill: "writing";
  band: number | null; // mock only, once both essays are scored
  submit_reason: "user" | "timeout";
  time_used_ms: number;
  tasks: {
    task_number: number;
    prompt: string;
    visual_url: string | null;
    text: string;
    word_count: number;
    min_words: number;
    time_ms: number;
    result: EssayResult | null; // null = waiting for the examiners
  }[];
};
export type SpeakingStats = { words: number; wpm: number; fillers: number; long_pauses: number; unsure_words: string[] };
export type SpeakingReport = {
  skill: "speaking";
  band: number | null; // once transcribed and scored
  submit_reason: "user" | "timeout";
  time_used_ms: number;
  transcribed: boolean;
  stats: SpeakingStats;
  parts: {
    number: number;
    cue_card: CueCard | null;
    answers: { id: number; question: string; duration_ms: number; transcript: string | null }[];
  }[];
  result: EssayResult | null; // criteria: fluency_coherence, lexical_resource, grammar, pronunciation
};
export type WritingOption = {
  task_id: number;
  task_number: number;
  title: string;
  kind: string;
  kind_label: string;
  topic: string;
  topic_label: string;
  seen: boolean;
};

export type TagStat = {
  skill: "reading" | "listening";
  kind: "qtype" | "topic" | "sub_skill";
  key: string;
  label: string;
  n: number;
  accuracy: number; // smoothed toward the section accuracy
  raw_accuracy: number;
  median_s: number | null;
  pace: number | null; // median time ÷ target (Reading only)
  score: number;
  weak: boolean;
};
export type SkillStats = {
  accuracy: number;
  answers: number;
  goal: number; // share correct needed for the target band
  target_s: number | null;
  tags: TagStat[];
  errors: { error_class: string; count: number }[];
};
export type Dashboard = {
  target_band: number;
  bands: { attempt_id: number; skill: Skill; band: number; date: string }[];
  reviews_due: number;
  weaknesses: TagStat[];
  skills: Partial<Record<"reading" | "listening", SkillStats>>;
  writing: {
    criteria: { key: string; n: number; average: number; weak: boolean }[];
    errors: { category: string; count: number; essays: number; per_100_words: number; weak: boolean }[];
  };
};
