import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { api, type Attempt, type AttemptSummary, type PracticeGroup } from "../api";
import { qtypeLabel } from "../labels";
import WritingPractice from "./WritingPractice";

type Dim = "qtype" | "topic" | "level";
type Filters = Partial<Record<Dim, string>>;
const LEVELS = { easy: "Easy", medium: "Medium", hard: "Hard" } as const;

export default function PracticePage() {
  const navigate = useNavigate();
  const [skill, setSkill] = useState<"reading" | "listening" | "writing">("reading");
  const options = useQuery({
    queryKey: ["practice-options", skill],
    queryFn: () => api<PracticeGroup[]>(`/practice/options?skill=${skill}`),
    enabled: skill !== "writing",
  });
  const attempts = useQuery({ queryKey: ["attempts"], queryFn: () => api<AttemptSummary[]>("/attempts") });
  const [filters, setFilters] = useState<Filters>({});
  const start = useMutation({
    mutationFn: () => api<Attempt>("/practice/sessions", { method: "POST", body: { skill, ...filters } }),
    onSuccess: (a) => navigate(`/practice/${a.id}`),
  });

  const groups = options.data ?? [];
  // A group counts for a filter row if it matches every *other* row, so the numbers show what each choice would give.
  const matches = (g: PracticeGroup, except?: Dim) =>
    (["qtype", "topic", "level"] as Dim[]).every((d) => d === except || !filters[d] || g[d] === filters[d]);
  const available = groups.filter((g) => matches(g));
  const total = available.reduce((n, g) => n + g.questions, 0);
  const fresh = available.filter((g) => !g.seen).reduce((n, g) => n + g.questions, 0);

  function row(dim: Dim, title: string, label: (g: PracticeGroup) => string, order?: string[]) {
    const counts = new Map<string, { label: string; n: number }>();
    for (const g of groups.filter((g) => matches(g, dim))) {
      const c = counts.get(g[dim]) ?? { label: label(g), n: 0 };
      counts.set(g[dim], { ...c, n: c.n + g.questions });
    }
    const values = order ?? [...counts.keys()].sort((a, b) => counts.get(a)!.label.localeCompare(counts.get(b)!.label));
    return (
      <fieldset className="filter">
        <legend>{title}</legend>
        <button className="pick" aria-pressed={!filters[dim]} onClick={() => setFilters({ ...filters, [dim]: undefined })}>
          Any
        </button>
        {values.map((v) => (
          <button
            key={v}
            className="pick"
            aria-pressed={filters[dim] === v}
            disabled={!counts.get(v)}
            onClick={() => setFilters({ ...filters, [dim]: v })}
          >
            {counts.get(v)?.label ?? LEVELS[v as keyof typeof LEVELS]} <span>{counts.get(v)?.n ?? 0}</span>
          </button>
        ))}
      </fieldset>
    );
  }

  const sessions = attempts.data?.filter((a) => a.mode === "practice") ?? [];
  return (
    <>
      <section className="hero">
        <h1>Practice</h1>
        <p className="lead">
          No clock. Check each group of questions when you're ready to see the answer, why it's right, and where it is in the
          passage or recording.
        </p>
      </section>

      <fieldset className="filter">
        <legend>Section</legend>
        {(["reading", "listening", "writing"] as const).map((s) => (
          <button
            key={s}
            className="pick"
            aria-pressed={skill === s}
            onClick={() => {
              setSkill(s);
              setFilters({});
            }}
          >
            {s[0].toUpperCase() + s.slice(1)}
          </button>
        ))}
      </fieldset>
      {skill === "writing" ? (
        <WritingPractice />
      ) : (
        <>
          {options.error && <p className="error">{options.error.message}</p>}
          {row("qtype", "Question type", (g) => qtypeLabel(g.qtype))}
          {row("topic", "Topic", (g) => g.topic_label)}
          {row("level", "Difficulty", (g) => LEVELS[g.level], Object.keys(LEVELS))}

          <div className="startbar">
            <button className="button" disabled={!total || start.isPending} onClick={() => start.mutate()}>
              Start practice
            </button>
            <span className="muted">
              {total ? `${total} questions match, ${fresh} of them new to you. Each session picks about 10.` : "Nothing matches these filters."}
            </span>
          </div>
          {start.error && <p className="error">{start.error.message}</p>}
        </>
      )}

      <h2 className="section-title">Recent sessions</h2>
      {sessions.length === 0 && <p className="muted">Sessions you start will appear here.</p>}
      <ul className="attempts">
        {sessions.map((a) => (
          <li key={a.id}>
            <span className="when">{new Date(a.started_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}</span>
            <span className="what">{a.skills[0][0].toUpperCase() + a.skills[0].slice(1)} practice</span>
            {a.status === "completed" ? (
              <Link to={`/report/${a.id}`}>View summary</Link>
            ) : (
              <>
                <span className="chip live">In progress</span>
                <Link to={`/practice/${a.id}`}>Resume</Link>
              </>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
