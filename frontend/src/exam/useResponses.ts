import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, ApiError, type Answer, type Attempt, type AttemptSection, type Highlight, type SaveOut } from "../api";
import { useQuestionTimer } from "./useQuestionTimer";

const AUTOSAVE_MS = 5000;

export const isAnswered = (a: Answer | undefined) => (Array.isArray(a) ? a.length > 0 : !!a?.trim());

/** Answers, review flags, highlights and the current question (an id) of one section. Changes are
 * autosaved every 5 s, when the tab is hidden, and before submit; time per question is measured too.
 * Writing reuses all of it: task ids stand in for question ids, and the essay text is the answer. */
export function useResponses(attempt: Attempt, section: AttemptSection) {
  const qc = useQueryClient();
  const writing = section.skill === "writing";
  const ids = useMemo(
    () =>
      writing
        ? section.parts!.map((p) => p.writing!.id)
        : section.parts!.flatMap((p) => p.groups.flatMap((g) => g.questions.map((q) => q.id))),
    [section, writing],
  );

  const [answers, setAnswers] = useState<Record<number, Answer>>(() =>
    writing
      ? Object.fromEntries(section.essays.map((e) => [e.writing_task_id, e.text]))
      : Object.fromEntries(section.responses.map((r) => [r.question_id, r.answer])),
  );
  const [flags, setFlags] = useState<Record<number, boolean>>(() =>
    Object.fromEntries(section.responses.map((r) => [r.question_id, r.flagged])),
  );
  const [highlights, setHighlightsState] = useState<Highlight[]>(section.ui_state.highlights ?? []);
  const saved = section.ui_state.current;
  const [current, setCurrentState] = useState(saved && ids.includes(saved) ? saved : ids[0]);

  const pending = useRef({ ids: new Set<number>(), time: new Map<number, number>(), ui: false });
  const latest = useRef({ answers, flags, highlights, current });
  latest.current = { answers, flags, highlights, current };
  const clockOffset = useRef(Date.parse(attempt.server_now) - Date.now());
  const chain = useRef(Promise.resolve()); // saves run one after another, never in parallel
  const url = `/attempts/${attempt.id}/sections/${section.id}`;

  const refresh = useCallback(() => qc.invalidateQueries({ queryKey: ["attempt", attempt.id] }), [qc, attempt.id]);

  const save = useCallback(
    (keepalive = false) => {
      const run = async () => {
        const p = pending.current;
        const changed = new Set([...p.ids, ...p.time.keys()]);
        if (!changed.size && !p.ui) return;
        const { answers, flags, highlights, current } = latest.current;
        pending.current = { ids: new Set(), time: new Map(), ui: false };
        try {
          const r = await api<SaveOut>(`${url}/responses`, {
            method: "PUT",
            keepalive,
            body: {
              [writing ? "essays" : "responses"]: [...changed].map((id) =>
                writing
                  ? { writing_task_id: id, text: answers[id] ?? "", time_ms: p.time.get(id) ?? 0 }
                  : { question_id: id, answer: answers[id] ?? null, flagged: !!flags[id], time_ms: p.time.get(id) ?? 0 },
              ),
              ui_state: p.ui ? { highlights, current } : undefined,
            },
          });
          clockOffset.current = Date.parse(r.server_now) - Date.now();
        } catch (e) {
          if (e instanceof ApiError && e.status === 409) return void refresh(); // closed or locked: reload from the server
          const n = pending.current; // network trouble: keep the changes for the next attempt
          p.ids.forEach((i) => n.ids.add(i));
          p.time.forEach((t, i) => n.time.set(i, (n.time.get(i) ?? 0) + t));
          n.ui ||= p.ui;
        }
      };
      chain.current = chain.current.then(run);
      return chain.current;
    },
    [url, refresh, writing],
  );

  useEffect(() => {
    const autosave = setInterval(() => save(), AUTOSAVE_MS);
    const onHide = () => document.visibilityState === "hidden" && save(true);
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("pagehide", onHide);
    return () => {
      clearInterval(autosave);
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("pagehide", onHide);
    };
  }, [save]);

  const currentId = useCallback(() => latest.current.current, []);
  const addTime = useCallback((qid: number, ms: number) => {
    pending.current.time.set(qid, (pending.current.time.get(qid) ?? 0) + ms);
  }, []);
  useQuestionTimer(currentId, addTime);

  return {
    answers,
    flags,
    highlights,
    current,
    clockOffset,
    save,
    refresh,
    setAnswer: (qids: number[], value: Answer) => {
      setAnswers((a) => ({ ...a, ...Object.fromEntries(qids.map((i) => [i, value])) }));
      qids.forEach((i) => pending.current.ids.add(i));
    },
    toggleFlag: (qid: number) => {
      setFlags((f) => ({ ...f, [qid]: !f[qid] }));
      pending.current.ids.add(qid);
    },
    setHighlights: (h: Highlight[]) => {
      setHighlightsState(h);
      pending.current.ui = true;
    },
    setCurrent: (qid: number) => {
      setCurrentState(qid);
      pending.current.ui = true;
    },
  };
}
