import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router";
import { api, type Attempt, type AttemptSection, type User } from "../api";
import "./exam.css";
import QuestionGroup from "./Questions";
import ListeningAudio from "./ListeningAudio";
import ReadingView from "./ReadingView";
import SpeakingView, { MicCheck } from "./SpeakingView";
import { isAnswered, useResponses } from "./useResponses";
import WritingView, { wordCount } from "./WritingView";

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
    const listening = section.skill === "listening";
    const writing = section.skill === "writing";
    if (section.skill === "speaking") return <SpeakingIntro attempt={a} section={section} start={() => start.mutate(section.id)} error={start.error} />;
    return (
      <div className="intro">
        {a.sections.length > 1 && (
          <p className="muted">
            Full mock: section {a.sections.indexOf(section) + 1} of {a.sections.length}
            {section !== a.sections[0] && ". The previous section is submitted; start this one when you are ready."}
          </p>
        )}
        <h1>
          {a.test_title}: {listening ? "Listening" : writing ? "Academic Writing" : "Academic Reading"}
        </h1>
        <p>
          {listening
            ? `About ${minutes} minutes. Four parts, 40 questions.`
            : writing
              ? `Time: ${minutes} minutes. Two tasks.`
              : `Time: ${minutes} minutes. Three passages, 40 questions.`}
        </p>
        <ul>
          {listening && <li>You will hear each recording ONCE only. It cannot be paused or replayed.</li>}
          {listening && <li>Answer while you listen. After the recording you have 2 minutes to check your answers.</li>}
          {writing && <li>Answer both tasks. Spend about 20 minutes on Task 1 and 40 minutes on Task 2.</li>}
          {writing && <li>Task 2 counts twice as much as Task 1. Write full sentences and paragraphs, not notes.</li>}
          {!writing && <li>Answer all the questions. You can change your answers at any time during the test.</li>}
          <li>The timer starts when you press Start and cannot be paused. Your answers are saved automatically.</li>
          <li>When time is up, the test is submitted with the answers saved so far.</li>
        </ul>
        {listening && <SoundCheck />}
        {start.error && <p className="error">{start.error.message}</p>}
        <button className="primary" disabled={start.isPending} onClick={() => start.mutate(section.id)}>
          Start test
        </button>
      </div>
    );
  }
  if (section.skill === "speaking") return <SpeakingExam key={section.id} attempt={a} section={section} user={user} />;
  return <ExamShell key={section.id} attempt={a} section={section} user={user} />;
}

function SpeakingIntro(props: { attempt: Attempt; section: AttemptSection; start: () => void; error: Error | null }) {
  const { attempt: a, section } = props;
  const [micOk, setMicOk] = useState(false);
  return (
    <div className="intro">
      {a.sections.length > 1 && (
        <p className="muted">
          Full mock: section {a.sections.indexOf(section) + 1} of {a.sections.length}. The previous section is submitted; start
          this one when you are ready.
        </p>
      )}
      <h1>{a.test_title}: Speaking</h1>
      <p>About 11–14 minutes. Three parts: questions about yourself, a long turn on a topic card, then a discussion.</p>
      <ul>
        <li>The examiner asks each question once. Answer aloud, then click <b>Finish answer</b>.</li>
        <li>Part 2: you get a topic card and one minute to prepare (you can make notes), then speak for up to two minutes.</li>
        <li>As in the real test, the examiner moves on when the time for an answer or a part is up.</li>
        <li>Your answers are recorded and saved one by one. They are scored afterwards, not during the test.</li>
      </ul>
      <MicCheck onOk={() => setMicOk(true)} />
      {props.error && <p className="error">{props.error.message}</p>}
      <button className="primary" disabled={!micOk} onClick={props.start}>
        Start test
      </button>
      {!micOk && <p className="muted">Test your microphone first.</p>}
    </div>
  );
}

function SpeakingExam({ attempt, section, user }: { attempt: Attempt; section: AttemptSection; user: User }) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const submitted = useRef(false);
  const submit = useMutation({
    mutationFn: () => api<Attempt>(`/attempts/${attempt.id}/sections/${section.id}/submit`, { method: "POST" }),
    onSuccess: (a) => {
      qc.setQueryData(["attempt", attempt.id], a);
      navigate(a.status === "completed" ? `/report/${attempt.id}` : `/exam/${attempt.id}`, { replace: true });
    },
  });
  const finish = useCallback(() => {
    if (submitted.current) return;
    submitted.current = true;
    submit.mutate();
  }, [submit]);
  return (
    <div className="exam">
      <header className="examhead">
        <span>{user.display_name}</span>
        <span className="timer">Speaking</span>
        <span />
      </header>
      <SpeakingView attempt={attempt} section={section} onFinish={finish} />
      {submit.error && (
        <p className="toast error">
          {submit.error.message}{" "}
          <button
            onClick={() => {
              submitted.current = false;
              finish();
            }}
          >
            Try again
          </button>
        </p>
      )}
    </div>
  );
}

type Prefs = {
  font: "standard" | "large" | "xlarge";
  scheme: "standard" | "white-on-black" | "yellow-on-black";
  volume: number; // 0–1, Listening
};
const DEFAULT_PREFS: Prefs = { font: "standard", scheme: "standard", volume: 0.8 };

function usePrefs(): [Prefs, (p: Prefs) => void] {
  const [prefs, setPrefs] = useState<Prefs>(() => {
    try {
      return { ...DEFAULT_PREFS, ...JSON.parse(localStorage.getItem("exam-prefs") ?? "{}") };
    } catch {
      return DEFAULT_PREFS;
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
  const [overlay, setOverlay] = useState<null | OverlayKind>(null);
  const [timeUp, setTimeUp] = useState(false);
  const [prefs, setPrefs] = usePrefs();
  const listening = section.skill === "listening";
  const writing = section.skill === "writing";
  const [reviewing, setReviewing] = useState(false); // Listening: the recording has ended
  const audioPart = useRef(0);

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
      if (a.status === "completed") navigate(`/report/${attempt.id}`, { replace: true });
    },
  });
  const { save, refresh } = r;
  const onExpire = useCallback(() => {
    setTimeUp(true);
    save().then(() => setTimeout(refresh, GRACE_MS));
  }, [save, refresh]);

  const unanswered = questions.filter((q) => !isAnswered(answers[q.id])).length;
  const confirmSubmit = () => {
    const msg = writing
      ? "Submit your writing now? You won't be able to change it afterwards."
      : unanswered
        ? `You have ${unanswered} unanswered questions. Submit anyway?`
        : "Submit your answers now?";
    if (window.confirm(msg)) submit.mutate();
  };

  // Listening: when the recording moves to a new part, the questions follow (you can still navigate freely).
  const { setCurrent } = r;
  const onAudioPart = useCallback(
    (n: number) => {
      if (audioPart.current === n) return;
      audioPart.current = n;
      setCurrent(parts.find((p) => p.number === n)!.groups[0].questions[0].id);
    },
    [parts, setCurrent],
  );
  const onAudioDone = useCallback(() => setReviewing(true), []);

  const index = questions.findIndex((q) => q.id === current);
  const part = writing ? parts.find((p) => p.writing!.id === current)! : parts.find((p) => p.number === questions[index].part)!;
  const overlays = overlay && (
    <Overlay kind={overlay} close={() => setOverlay(null)} prefs={prefs} setPrefs={setPrefs} writing={writing} />
  );

  if (writing) {
    const task = part.writing!;
    return (
      <div className={`exam font-${prefs.font} scheme-${prefs.scheme}`}>
        <header className="examhead">
          <span>{user.display_name}</span>
          {section.deadline_at ? (
            <Timer deadline={section.deadline_at} offset={r.clockOffset} onExpire={onExpire} flash />
          ) : (
            <span className="timer">Untimed practice</span>
          )}
          <span className="tools">
            <button onClick={() => setOverlay("settings")}>Settings</button>
            <button onClick={() => setOverlay("help")}>Help</button>
            <button onClick={() => setOverlay("hidden")}>Hide</button>
          </span>
        </header>
        <div className="partbar">
          <strong>Part {task.task_number}</strong>
          <span>
            You should spend about {task.task_number === 1 ? 20 : 40} minutes on this task. Write at least{" "}
            {task.task_number === 1 ? 150 : 250} words.
          </span>
        </div>
        <WritingView key={task.id} task={task} text={(answers[task.id] as string) ?? ""} onChange={(t) => r.setAnswer([task.id], t)} />
        <footer className="navbar">
          {parts.map((p) => (
            <div key={p.number} className={`navpart${p === part ? " active" : ""}`}>
              <button className="partlabel" onClick={() => r.setCurrent(p.writing!.id)}>
                Part {p.number}
              </button>
              <span className="count">{wordCount((answers[p.writing!.id] as string) ?? "")} words</span>
            </div>
          ))}
          <button className="primary" disabled={submit.isPending || timeUp} onClick={confirmSubmit}>
            Submit
          </button>
        </footer>
        {submit.error && <p className="toast error">{submit.error.message}</p>}
        {timeUp && (
          <div className="cover">
            <p>Time is up. Your writing is being submitted…</p>
          </div>
        )}
        {overlays}
      </div>
    );
  }

  return (
    <div className={`exam font-${prefs.font} scheme-${prefs.scheme}`}>
      <header className="examhead">
        <span>{user.display_name}</span>
        <Timer deadline={section.deadline_at!} offset={r.clockOffset} onExpire={onExpire} flash={!listening} />
        <span className="tools">
          {listening && (
            <label className="volume">
              Volume{" "}
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={prefs.volume}
                onChange={(e) => setPrefs({ ...prefs, volume: Number(e.target.value) })}
              />
            </label>
          )}
          <button onClick={() => setOverlay("settings")}>Settings</button>
          <button onClick={() => setOverlay("help")}>Help</button>
          <button onClick={() => setOverlay("hidden")}>Hide</button>
        </span>
      </header>

      <div className="partbar">
        <strong>Part {part.number}</strong>
        <span>
          {listening ? "Listen and answer" : "Read the text and answer"} questions {part.groups[0].questions[0].number}–
          {part.groups.at(-1)!.questions.at(-1)!.number}.
        </span>
        {reviewing && <span className="reviewing">The recording has ended. Check your answers before the time runs out.</span>}
      </div>

      {listening ? (
        <div className="listening">
          <ListeningAudio
            parts={parts}
            startedAt={section.started_at!}
            offset={r.clockOffset}
            volume={prefs.volume}
            onPart={onAudioPart}
            onDone={onAudioDone}
          />
          <div className="questions">
            {part.groups.map((g) => (
              <QuestionGroup key={g.id} group={g} answers={answers} setAnswer={r.setAnswer} current={current} focus={r.setCurrent} />
            ))}
          </div>
        </div>
      ) : (
        <ReadingView key={part.number} part={part} highlights={r.highlights} setHighlights={r.setHighlights}>
          {part.groups.map((g) => (
            <QuestionGroup key={g.id} group={g} answers={answers} setAnswer={r.setAnswer} current={current} focus={r.setCurrent} />
          ))}
        </ReadingView>
      )}

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
      {overlays}
    </div>
  );
}

type OverlayKind = "settings" | "help" | "hidden";

/** The Hide, Help and Settings screens. */
function Overlay(props: { kind: OverlayKind; close: () => void; prefs: Prefs; setPrefs: (p: Prefs) => void; writing: boolean }) {
  const { kind, close, prefs, setPrefs, writing } = props;
  return (
    <>
      {kind === "hidden" && (
        <div className="cover">
          <p>The test is hidden. The timer is still running.</p>
          <button className="primary" onClick={() => close()}>
            Show test
          </button>
        </div>
      )}
      {kind === "help" && (
        <div className="cover" onClick={() => close()}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <h2>Help</h2>
            <ul>
              {writing ? (
                <>
                  <li>Switch between the tasks with Part 1 and Part 2 in the bar below. Both are saved as you type.</li>
                  <li>Drag the bar between the task and your answer to resize them.</li>
                  <li>The word count updates as you type. Copy and paste work; spell check is off, as in the real test.</li>
                </>
              ) : (
                <>
                  <li>Select words in the passage to highlight them or add a note. Click a highlight to clear it.</li>
                  <li>Drag the bar between the passage and the questions to resize them.</li>
                  <li>
                    Matching questions: drag an option onto a gap, or click an option and then click the gap. Click a filled gap to
                    empty it.
                  </li>
                  <li>Tick <b>Review</b> to mark the current question; it turns into a circle in the bar below.</li>
                  <li>Answers are saved automatically every few seconds.</li>
                </>
              )}
            </ul>
            <button onClick={() => close()}>Close</button>
          </div>
        </div>
      )}
      {kind === "settings" && (
        <div className="cover" onClick={() => close()}>
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
            <button onClick={() => close()}>Close</button>
          </div>
        </div>
      )}
    </>
  );
}

/** "37 minutes left". Red in the last 10 minutes, flashing for 10 s at the 10- and 5-minute marks. */
function Timer(props: { deadline: string; offset: { current: number }; onExpire: () => void; flash: boolean }) {
  const { deadline, offset, onExpire } = props;
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
  const flashing = props.flash && ((s <= 600 && s > 590) || (s <= 300 && s > 290)); // Reading/Writing only (R§7)
  return (
    <span className="timer">
      {!hidden && <span className={`${s <= 600 ? "warn" : ""} ${flashing ? "flash" : ""}`}>{text}</span>}{" "}
      <button className="link" onClick={() => setHidden(!hidden)}>
        {hidden ? "Show timer" : "Hide timer"}
      </button>
    </span>
  );
}

/** Before a Listening test: set the volume with a test tone (generated in the browser, no test audio needed). */
function SoundCheck() {
  const [prefs, setPrefs] = usePrefs();
  const beep = () => {
    const ctx = new AudioContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    gain.gain.value = prefs.volume * 0.3;
    osc.frequency.value = 440;
    osc.connect(gain).connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 1);
    osc.onended = () => ctx.close();
  };
  return (
    <div className="soundcheck">
      <strong>Sound check</strong>
      <p>Put on your headphones, play the test sound and set a comfortable volume.</p>
      <button onClick={beep}>Play test sound</button>{" "}
      <label>
        Volume{" "}
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={prefs.volume}
          onChange={(e) => setPrefs({ ...prefs, volume: Number(e.target.value) })}
        />
      </label>
    </div>
  );
}
