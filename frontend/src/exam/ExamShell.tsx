import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router";
import { api, type Attempt, type AttemptSection, type User } from "../api";
import "./exam.css";
import QuestionGroup from "./Questions";
import ReadingView from "./ReadingView";
import { isAnswered, useResponses } from "./useResponses";

const GRACE_MS = 11_000; // the server accepts saves for 10 s after the deadline, then auto-submits

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
  const r = useResponses(attempt, section);
  const { answers, flags, current } = r;
  const [overlay, setOverlay] = useState<null | "settings" | "help" | "hidden">(null);
  const [timeUp, setTimeUp] = useState(false);
  const [prefs, setPrefs] = usePrefs();

  const go = (q: { id: number; number: number }) => {
    r.setCurrent(q.id);
    requestAnimationFrame(() => {
      const el = document.getElementById(`q-${q.number}`);
      el?.scrollIntoView({ block: "center", behavior: "smooth" });
      (el instanceof HTMLInputElement ? el : el?.querySelector("input"))?.focus({ preventScroll: true });
    });
  };

  const url = `/attempts/${attempt.id}/sections/${section.id}`;
  const submit = useMutation({
    mutationFn: async () => {
      await r.save();
      return api<Attempt>(`${url}/submit`, { method: "POST" });
    },
    onSuccess: (a) => {
      qc.setQueryData(["attempt", attempt.id], a);
      navigate(`/report/${attempt.id}`, { replace: true });
    },
  });
  const { save, refresh } = r;
  const onExpire = useCallback(() => {
    setTimeUp(true);
    save().then(() => setTimeout(refresh, GRACE_MS));
  }, [save, refresh]);

  const unanswered = questions.filter((q) => !isAnswered(answers[q.id])).length;
  const confirmSubmit = () => {
    const msg = unanswered ? `You have ${unanswered} unanswered questions. Submit anyway?` : "Submit your answers now?";
    if (window.confirm(msg)) submit.mutate();
  };

  const index = questions.findIndex((q) => q.id === current);
  const part = parts.find((p) => p.number === questions[index].part)!;

  return (
    <div className={`exam font-${prefs.font} scheme-${prefs.scheme}`}>
      <header className="examhead">
        <span>{user.display_name}</span>
        <Timer deadline={section.deadline_at!} offset={r.clockOffset} onExpire={onExpire} />
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

      <ReadingView key={part.number} part={part} highlights={r.highlights} setHighlights={r.setHighlights}>
        {part.groups.map((g) => (
          <QuestionGroup key={g.id} group={g} answers={answers} setAnswer={r.setAnswer} current={current} focus={r.setCurrent} />
        ))}
      </ReadingView>

      <footer className="navbar">
        {parts.map((p) => {
          const qs = questions.filter((q) => q.part === p.number);
          return (
            <div key={p.number} className={`navpart${p.number === part.number ? " active" : ""}`}>
              <button className="partlabel" onClick={() => go(qs[0])}>
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
                      q.id === current && "current",
                    ].filter(Boolean).join(" ")}
                    aria-label={`Question ${q.number}${isAnswered(answers[q.id]) ? ", answered" : ""}${flags[q.id] ? ", marked for review" : ""}`}
                    onClick={() => go(q)}
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
          <input type="checkbox" checked={!!flags[current]} onChange={() => r.toggleFlag(current)} /> Review
        </label>
        <button aria-label="Previous question" disabled={index === 0} onClick={() => go(questions[index - 1])}>
          ◀
        </button>
        <button aria-label="Next question" disabled={index === questions.length - 1} onClick={() => go(questions[index + 1])}>
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
