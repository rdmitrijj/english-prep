import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router";
import {
  api,
  ApiError,
  type Answer,
  type Attempt,
  type AttemptSection,
  type Highlight,
  type SaveOut,
  type User,
} from "../api";
import "./exam.css";
import QuestionGroup from "./Questions";
import ReadingView from "./ReadingView";

const AUTOSAVE_MS = 5000;
const GRACE_MS = 11_000; // the server accepts saves for 10 s after the deadline, then auto-submits

export const isAnswered = (a: Answer | undefined) => (Array.isArray(a) ? a.length > 0 : !!a?.trim());

/** Loads the attempt and shows the intro screen, the running exam, or (when finished) the report. */
export default function ExamPage({ user }: { user: User }) {
  const id = Number(useParams().attemptId);
  const qc = useQueryClient();
  const attempt = useQuery({
    queryKey: ["attempt", id],
    queryFn: () => api<Attempt>(`/attempts/${id}`),
    staleTime: Infinity, // local state owns the answers while the exam runs
    refetchOnWindowFocus: false,
  });
  const start = useMutation({
    mutationFn: (sid: number) => api<Attempt>(`/attempts/${id}/sections/${sid}/start`, { method: "POST" }),
    onSuccess: (a) => qc.setQueryData(["attempt", id], a),
  });

  if (attempt.isPending) return <p className="center">Loading…</p>;
  if (attempt.error) return <p className="center error">{attempt.error.message}</p>;
  const a = attempt.data;
  const section = a.sections.find((s) => !s.submitted_at);
  if (a.status === "completed" || !section) return <Navigate to={`/report/${id}`} replace />;

  if (!section.started_at) {
    const minutes = Math.round((section.duration_s ?? 0) / 60);
    return (
      <div className="intro">
        <h1>{a.test_title}: Academic Reading</h1>
        <p>Time: {minutes} minutes. Three passages, 40 questions.</p>
        <ul>
          <li>Answer all the questions. You can change your answers at any time during the test.</li>
          <li>The timer starts when you press Start and cannot be paused. Your answers are saved automatically.</li>
          <li>When time is up, the test is submitted with the answers saved so far.</li>
        </ul>
        {start.error && <p className="error">{start.error.message}</p>}
        <button className="primary" disabled={start.isPending} onClick={() => start.mutate(section.id)}>
          Start test
        </button>
      </div>
    );
  }
  return <ExamShell key={section.id} attempt={a} section={section} user={user} />;
}

type Prefs = { font: "standard" | "large" | "xlarge"; scheme: "standard" | "white-on-black" | "yellow-on-black" };

function usePrefs(): [Prefs, (p: Prefs) => void] {
  const [prefs, setPrefs] = useState<Prefs>(() => {
    try {
      return { font: "standard", scheme: "standard", ...JSON.parse(localStorage.getItem("exam-prefs") ?? "{}") };
    } catch {
      return { font: "standard", scheme: "standard" };
    }
  });
  const save = (p: Prefs) => {
    setPrefs(p);
    try {
      localStorage.setItem("exam-prefs", JSON.stringify(p));
    } catch {
      /* private mode: prefs just don't persist */
    }
  };
  return [prefs, save];
}

function ExamShell({ attempt, section, user }: { attempt: Attempt; section: AttemptSection; user: User }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const parts = section.parts!;
  const questions = useMemo(
    () => parts.flatMap((p) => p.groups.flatMap((g) => g.questions.map((q) => ({ id: q.id, number: q.number, part: p.number })))),
    [parts],
  );
  const idOf = useMemo(() => new Map(questions.map((q) => [q.number, q.id])), [questions]);

  const [answers, setAnswers] = useState<Record<number, Answer>>(() =>
    Object.fromEntries(section.responses.map((r) => [r.question_id, r.answer])),
  );
  const [flags, setFlags] = useState<Record<number, boolean>>(() =>
    Object.fromEntries(section.responses.map((r) => [r.question_id, r.flagged])),
  );
  const [highlights, setHighlightsState] = useState<Highlight[]>(section.ui_state.highlights ?? []);
  const [current, setCurrentState] = useState(section.ui_state.current ?? questions[0].number);
  const [overlay, setOverlay] = useState<null | "settings" | "help" | "hidden">(null);
  const [timeUp, setTimeUp] = useState(false);
  const [prefs, setPrefs] = usePrefs();

  // ---- autosave: changes collect here and go out every 5 s, on tab hide, and before submit ----
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
        const ids = new Set([...p.ids, ...p.time.keys()]);
        if (!ids.size && !p.ui) return;
        const { answers, flags, highlights, current } = latest.current;
        pending.current = { ids: new Set(), time: new Map(), ui: false };
        try {
          const r = await api<SaveOut>(`${url}/responses`, {
            method: "PUT",
            keepalive,
            body: {
              responses: [...ids].map((qid) => ({
                question_id: qid,
                answer: answers[qid] ?? null,
                flagged: !!flags[qid],
                time_ms: p.time.get(qid) ?? 0,
              })),
              ui_state: p.ui ? { highlights, current } : undefined,
            },
          });
          clockOffset.current = Date.parse(r.server_now) - Date.now();
        } catch (e) {
          if (e instanceof ApiError && e.status === 409) return void refresh(); // closed by the server → report
          const n = pending.current; // network trouble: keep the changes for the next attempt
          p.ids.forEach((i) => n.ids.add(i));
          p.time.forEach((t, i) => n.time.set(i, (n.time.get(i) ?? 0) + t));
          n.ui ||= p.ui;
        }
      };
      chain.current = chain.current.then(run);
      return chain.current;
    },
    [url, refresh],
  );

  useEffect(() => {
    const autosave = setInterval(() => save(), AUTOSAVE_MS);
    // ponytail: 1 s ticks, no idle detection yet; M4's useQuestionTimer adds the 45 s idle pause.
    const tick = setInterval(() => {
      if (document.hidden) return;
      const qid = idOf.get(latest.current.current)!;
      pending.current.time.set(qid, (pending.current.time.get(qid) ?? 0) + 1000);
    }, 1000);
    const onHide = () => document.visibilityState === "hidden" && save(true);
    document.addEventListener("visibilitychange", onHide);
    window.addEventListener("pagehide", onHide);
    return () => {
      clearInterval(autosave);
      clearInterval(tick);
      document.removeEventListener("visibilitychange", onHide);
      window.removeEventListener("pagehide", onHide);
    };
  }, [save, idOf]);

  const setAnswer = (ids: number[], value: Answer) => {
    setAnswers((a) => ({ ...a, ...Object.fromEntries(ids.map((i) => [i, value])) }));
    ids.forEach((i) => pending.current.ids.add(i));
  };
  const setHighlights = (h: Highlight[]) => {
    setHighlightsState(h);
    pending.current.ui = true;
  };
  const setCurrent = (n: number) => {
    setCurrentState(n);
    pending.current.ui = true;
  };
  const go = (n: number) => {
    setCurrent(n);
    requestAnimationFrame(() => {
      const el = document.getElementById(`q-${n}`);
      el?.scrollIntoView({ block: "center", behavior: "smooth" });
      (el instanceof HTMLInputElement ? el : el?.querySelector("input"))?.focus({ preventScroll: true });
    });
  };
  const currentId = idOf.get(current)!;
  const toggleFlag = () => {
    setFlags((f) => ({ ...f, [currentId]: !f[currentId] }));
    pending.current.ids.add(currentId);
  };

  const submit = useMutation({
    mutationFn: async () => {
      await save();
      return api<Attempt>(`${url}/submit`, { method: "POST" });
    },
    onSuccess: (a) => {
      qc.setQueryData(["attempt", attempt.id], a);
      navigate(`/report/${attempt.id}`, { replace: true });
    },
  });
  const onExpire = useCallback(() => {
    setTimeUp(true);
    save().then(() => setTimeout(refresh, GRACE_MS));
  }, [save, refresh]);

  const unanswered = questions.filter((q) => !isAnswered(answers[q.id])).length;
  const confirmSubmit = () => {
    const msg = unanswered ? `You have ${unanswered} unanswered questions. Submit anyway?` : "Submit your answers now?";
    if (window.confirm(msg)) submit.mutate();
  };

  const part = parts.find((p) => p.number === questions.find((q) => q.number === current)!.part)!;
  const index = questions.findIndex((q) => q.number === current);

  return (
    <div className={`exam font-${prefs.font} scheme-${prefs.scheme}`}>
      <header className="examhead">
        <span>{user.display_name}</span>
        <Timer deadline={section.deadline_at!} offset={clockOffset} onExpire={onExpire} />
        <span className="tools">
          <button onClick={() => setOverlay("settings")}>Settings</button>
          <button onClick={() => setOverlay("help")}>Help</button>
          <button onClick={() => setOverlay("hidden")}>Hide</button>
        </span>
      </header>

      <div className="partbar">
        <strong>Part {part.number}</strong>
        <span>Read the text and answer questions {part.groups[0].questions[0].number}–{part.groups.at(-1)!.questions.at(-1)!.number}.</span>
      </div>

      <ReadingView key={part.number} part={part} highlights={highlights} setHighlights={setHighlights}>
        {part.groups.map((g) => (
          <QuestionGroup key={g.id} group={g} answers={answers} setAnswer={setAnswer} current={current} focus={setCurrent} />
        ))}
      </ReadingView>

      <footer className="navbar">
        {parts.map((p) => {
          const qs = questions.filter((q) => q.part === p.number);
          return (
            <div key={p.number} className={`navpart${p.number === part.number ? " active" : ""}`}>
              <button className="partlabel" onClick={() => go(qs[0].number)}>
                Part {p.number}
              </button>
              {p.number === part.number ? (
                qs.map((q) => (
                  <button
                    key={q.id}
                    className={[
                      "qnum",
                      isAnswered(answers[q.id]) && "answered",
                      flags[q.id] && "flagged",
                      q.number === current && "current",
                    ].filter(Boolean).join(" ")}
                    aria-label={`Question ${q.number}${isAnswered(answers[q.id]) ? ", answered" : ""}${flags[q.id] ? ", marked for review" : ""}`}
                    onClick={() => go(q.number)}
                  >
                    {q.number}
                  </button>
                ))
              ) : (
                <span className="count">
                  {qs.filter((q) => isAnswered(answers[q.id])).length} of {qs.length}
                </span>
              )}
            </div>
          );
        })}
        <label className="review">
          <input type="checkbox" checked={!!flags[currentId]} onChange={toggleFlag} /> Review
        </label>
        <button aria-label="Previous question" disabled={index === 0} onClick={() => go(questions[index - 1].number)}>
          ◀
        </button>
        <button aria-label="Next question" disabled={index === questions.length - 1} onClick={() => go(questions[index + 1].number)}>
          ▶
        </button>
        <button className="primary" disabled={submit.isPending || timeUp} onClick={confirmSubmit}>
          Submit
        </button>
      </footer>

      {submit.error && <p className="toast error">{submit.error.message}</p>}
      {timeUp && (
        <div className="cover">
          <p>Time is up. Your answers are being submitted…</p>
        </div>
      )}
      {overlay === "hidden" && (
        <div className="cover">
          <p>The test is hidden. The timer is still running.</p>
          <button className="primary" onClick={() => setOverlay(null)}>
            Show test
          </button>
        </div>
      )}
      {overlay === "help" && (
        <div className="cover" onClick={() => setOverlay(null)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h2>Help</h2>
            <ul>
              <li>Select words in the passage to highlight them or add a note. Click a highlight to clear it.</li>
              <li>Drag the bar between the passage and the questions to resize them.</li>
              <li>Matching questions: drag an option onto a gap, or click an option and then click the gap. Click a filled gap to empty it.</li>
              <li>Tick <b>Review</b> to mark the current question; it turns into a circle in the bar below.</li>
              <li>Answers are saved automatically every few seconds.</li>
            </ul>
            <button onClick={() => setOverlay(null)}>Close</button>
          </div>
        </div>
      )}
      {overlay === "settings" && (
        <div className="cover" onClick={() => setOverlay(null)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h2>Settings</h2>
            <label>
              Text size{" "}
              <select value={prefs.font} onChange={(e) => setPrefs({ ...prefs, font: e.target.value as Prefs["font"] })}>
                <option value="standard">Standard</option>
                <option value="large">Large</option>
                <option value="xlarge">Extra large</option>
              </select>
            </label>
            <label>
              Colours{" "}
              <select value={prefs.scheme} onChange={(e) => setPrefs({ ...prefs, scheme: e.target.value as Prefs["scheme"] })}>
                <option value="standard">Black on white</option>
                <option value="white-on-black">White on black</option>
                <option value="yellow-on-black">Yellow on black</option>
              </select>
            </label>
            <button onClick={() => setOverlay(null)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}

/** "37 minutes left". Red in the last 10 minutes, flashing for 10 s at the 10- and 5-minute marks. */
function Timer({ deadline, offset, onExpire }: { deadline: string; offset: { current: number }; onExpire: () => void }) {
  const end = Date.parse(deadline);
  const remainingS = () => Math.ceil((end - (Date.now() + offset.current)) / 1000);
  const [left, setLeft] = useState(remainingS);
  const [hidden, setHidden] = useState(false);
  const expired = useRef(false);

  useEffect(() => {
    const t = setInterval(() => setLeft(remainingS()), 250);
    return () => clearInterval(t);
  });
  useEffect(() => {
    if (left <= 0 && !expired.current) {
      expired.current = true;
      onExpire();
    }
  }, [left, onExpire]);

  const s = Math.max(0, left);
  const text = s >= 60 ? `${Math.ceil(s / 60)} minutes left` : `${s} seconds left`;
  const flashing = (s <= 600 && s > 590) || (s <= 300 && s > 290);
  return (
    <span className="timer">
      {!hidden && <span className={`${s <= 600 ? "warn" : ""} ${flashing ? "flash" : ""}`}>{text}</span>}{" "}
      <button className="link" onClick={() => setHidden(!hidden)}>
        {hidden ? "Show timer" : "Hide timer"}
      </button>
    </span>
  );
}
