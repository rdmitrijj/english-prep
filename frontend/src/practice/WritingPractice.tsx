import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router";
import { api, type Attempt, type WritingOption } from "../api";

/** Writing practice: pick one task (filtered by task and type) and write it untimed on the exam's writing screen. */
export default function WritingPractice() {
  const navigate = useNavigate();
  const options = useQuery({ queryKey: ["practice-writing"], queryFn: () => api<WritingOption[]>("/practice/writing") });
  const [task, setTask] = useState<number | null>(null);
  const [kind, setKind] = useState<string | null>(null);
  const start = useMutation({
    mutationFn: (taskId: number) =>
      api<Attempt>("/practice/sessions", { method: "POST", body: { skill: "writing", writing_task_id: taskId } }),
    onSuccess: (a) => navigate(`/exam/${a.id}`),
  });

  const all = options.data ?? [];
  const byTask = all.filter((o) => task === null || o.task_number === task);
  const kinds = [...new Map(byTask.map((o) => [o.kind, o.kind_label])).entries()];
  const shown = byTask.filter((o) => kind === null || o.kind === kind);
  return (
    <>
      {options.error && <p className="error">{options.error.message}</p>}
      <fieldset className="filter">
        <legend>Task</legend>
        {([null, 1, 2] as const).map((n) => (
          <button
            key={n ?? "any"}
            className="pick"
            aria-pressed={task === n}
            onClick={() => {
              setTask(n);
              setKind(null);
            }}
          >
            {n === null ? "Any" : n === 1 ? "Task 1: describe a visual" : "Task 2: essay"}{" "}
            <span>{all.filter((o) => n === null || o.task_number === n).length}</span>
          </button>
        ))}
      </fieldset>
      <fieldset className="filter">
        <legend>Type</legend>
        <button className="pick" aria-pressed={kind === null} onClick={() => setKind(null)}>
          Any
        </button>
        {kinds.map(([k, label]) => (
          <button key={k} className="pick" aria-pressed={kind === k} onClick={() => setKind(k)}>
            {label} <span>{byTask.filter((o) => o.kind === k).length}</span>
          </button>
        ))}
      </fieldset>
      <p className="muted">
        No clock, but your writing time is measured. After you submit, the essay waits for scoring: say <b>score my essays</b>{" "}
        in Claude Code.
      </p>
      <ul className="attempts">
        {shown.map((o) => (
          <li key={o.task_id}>
            <span className="when">Task {o.task_number}</span>
            <span className="what">
              {o.title} <span className="muted">· {o.topic_label}</span>
            </span>
            {o.seen && <span className="chip">Written before</span>}
            <button className="button" disabled={start.isPending} onClick={() => start.mutate(o.task_id)}>
              Write
            </button>
          </li>
        ))}
      </ul>
      {start.error && <p className="error">{start.error.message}</p>}
    </>
  );
}
