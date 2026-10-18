import { useEffect, useMemo, useRef, useState } from "react";
import { ApiError, type Attempt, type AttemptSection, type Part, type Segment } from "../api";

const PART_CAP_S: Record<number, number> = { 1: 300, 3: 300 }; // like a real examiner, move on after about 5 minutes
const PREP_S = 60;

type Step = { part: Part; line: number; seg: Segment };
type Phase = "mic" | "examiner" | "blocked" | "prep" | "answer" | "saving" | "error" | "done";

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

/** Plays one examiner line out of the part's recording; resolves when the line ends. Returns a cancel function. */
function playLine(el: HTMLAudioElement, url: string, seg: Segment, onEnd: () => void, onBlocked: () => void) {
  let done = false;
  const finish = () => {
    if (done) return;
    done = true;
    el.pause();
    onEnd();
  };
  const tick = () => el.currentTime * 1000 >= seg.end_ms && finish();
  const go = () => {
    el.currentTime = seg.start_ms / 1000;
    el.play().catch(() => !done && onBlocked()); // no click on this page yet (e.g. after a refresh)
  };
  el.addEventListener("timeupdate", tick);
  el.addEventListener("ended", finish);
  if (el.src.endsWith(url)) go();
  else {
    el.addEventListener("loadedmetadata", go, { once: true });
    el.src = url;
  }
  return () => {
    done = true;
    el.removeEventListener("timeupdate", tick);
    el.removeEventListener("ended", finish);
    el.removeEventListener("loadedmetadata", go);
    el.pause();
  };
}

async function upload(url: string, blob: Blob, ms: number) {
  for (let i = 0; ; i++) {
    const res = await fetch(`/api${url}?duration_ms=${Math.round(ms)}`, {
      method: "PUT",
      body: blob,
      headers: { "Content-Type": blob.type || "audio/webm" },
    }).catch(() => null);
    if (res?.ok) return;
    if (res && res.status < 500) throw new ApiError(res.status, (await res.json().catch(() => ({}))).detail ?? res.statusText);
    if (i === 2) throw new Error("Your answer couldn't be saved. Check your connection and try again.");
    await new Promise((r) => setTimeout(r, 1500 * (i + 1)));
  }
}

/** The interview: the examiner's lines play one by one; after each question your answer is recorded and uploaded at once.
 * Real-test rules: Part 2 gives one minute to prepare with the cue card, then up to two minutes; Parts 1 and 3 stop
 * after about five minutes. There is no visible clock, as in the real interview. */
export default function SpeakingView({ attempt, section, onFinish }: { attempt: Attempt; section: AttemptSection; onFinish: () => void }) {
  const steps = useMemo<Step[]>(
    () => section.parts!.flatMap((part) => part.transcript!.map((seg, line) => ({ part, line, seg }))),
    [section.parts],
  );
  const resumeAt = useMemo(() => {
    const done = new Set(section.recorded.map((r) => `${r.part_number}:${r.line_no}`));
    return steps.findLastIndex((s) => done.has(`${s.part.number}:${s.line}`)) + 1;
  }, [steps, section.recorded]);

  const [i, setI] = useState(resumeAt);
  const [phase, setPhase] = useState<Phase>("mic");
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState("");
  const [notes, setNotes] = useState("");
  const audio = useRef<HTMLAudioElement>(null);
  const partStart = useRef<Record<number, number>>({});
  const prepped = useRef(new Set<number>());
  const pending = useRef<{ blob: Blob; ms: number } | null>(null);
  const step = steps[i] as Step | undefined;
  const base = `/attempts/${attempt.id}/sections/${section.id}`;

  const getMic = () =>
    navigator.mediaDevices
      .getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } })
      .then((s) => {
        setStream(s);
        setPhase("examiner");
      })
      .catch(() => setError("The microphone is blocked. Allow it for this site in the browser's address bar, then try again."));

  useEffect(() => {
    getMic();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- once
  useEffect(() => () => stream?.getTracks().forEach((t) => t.stop()), [stream]);

  // The server's deadline is the safety net: when it passes, the interview ends with what was recorded.
  useEffect(() => {
    const offset = Date.parse(attempt.server_now) - Date.now();
    const t = setTimeout(() => setPhase("done"), Date.parse(section.deadline_at!) - (Date.now() + offset));
    return () => clearTimeout(t);
  }, [attempt.server_now, section.deadline_at]);

  useEffect(() => {
    if (phase === "done") onFinish();
  }, [phase, onFinish]);

  // The examiner: play the current line, then record an answer or move on.
  useEffect(() => {
    if (phase !== "examiner") return;
    if (!step) {
      setPhase("done");
      return;
    }
    const n = step.part.number;
    partStart.current[n] ??= Date.now();
    if (step.seg.answer_s && PART_CAP_S[n] && (Date.now() - partStart.current[n]) / 1000 > PART_CAP_S[n]) {
      setI(i + 1); // time for this part is up: skip its remaining questions
      return;
    }
    if (step.part.cue_card && step.seg.answer_s && !prepped.current.has(n)) {
      setPhase("prep");
      return;
    }
    return playLine(
      audio.current!,
      step.part.audio!.url,
      step.seg,
      () => (step.seg.answer_s ? setPhase("answer") : setI(i + 1)),
      () => setPhase("blocked"),
    );
  }, [phase, i, step]);

  const save = async (blob: Blob, ms: number) => {
    pending.current = { blob, ms };
    setPhase("saving");
    try {
      await upload(`${base}/speaking/${step!.part.number}/${step!.line}`, blob, ms);
      pending.current = null;
      setI(i + 1);
      setPhase("examiner");
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) return setPhase("done"); // the section closed (deadline)
      setError((e as Error).message);
      setPhase("error");
    }
  };

  const longTurn = !!step?.part.cue_card && step.seg.answer_s === 120;
  const showCard = !!step?.part.cue_card && (phase === "prep" || longTurn || !prepped.current.has(step.part.number));
  return (
    <div className="speaking">
      <audio ref={audio} preload="auto" />
      <div className="partbar">
        <strong>Part {step?.part.number ?? 3}</strong>
        <span>
          {step?.part.number === 2
            ? "Talk about the topic on the card for one to two minutes."
            : "Answer the examiner's questions. Speak naturally and give full answers."}
        </span>
      </div>

      <div className="stage">
        {showCard && step!.part.cue_card && (
          <div className="cuecard">
            <p>
              <b>{step!.part.cue_card.task}</b>
            </p>
            <p>You should say:</p>
            <ul>
              {step!.part.cue_card.bullets.map((b) => (
                <li key={b}>{b}</li>
              ))}
            </ul>
            <p>{step!.part.cue_card.final}</p>
          </div>
        )}
        {(phase === "prep" || (longTurn && phase === "answer")) && (
          <textarea className="notes" aria-label="Your notes" placeholder="Notes (only you see these)" value={notes} onChange={(e) => setNotes(e.target.value)} />
        )}

        {phase === "mic" && (error ? <p className="error">{error}</p> : <p>Connecting the microphone…</p>)}
        {phase === "mic" && error && <button onClick={getMic}>Try again</button>}
        {phase === "examiner" && <p className="status">🔊 The examiner is speaking…</p>}
        {phase === "prep" && (
          <Prep
            onDone={() => {
              prepped.current.add(step!.part.number);
              setPhase("examiner");
            }}
          />
        )}
        {phase === "answer" && stream && (
          <Recorder
            key={i}
            stream={stream}
            maxS={step!.seg.answer_s!}
            longTurn={longTurn}
            onDone={save}
            onRepeat={step!.part.number === 2 ? undefined : () => setPhase("examiner")}
          />
        )}
        {phase === "saving" && <p className="status">Saving your answer…</p>}
        {phase === "error" && (
          <>
            <p className="error">{error}</p>
            <button className="primary" onClick={() => save(pending.current!.blob, pending.current!.ms)}>
              Try again
            </button>
          </>
        )}
      </div>

      {phase === "blocked" && (
        <div className="cover">
          <p>Click to continue the interview.</p>
          <button className="primary" onClick={() => setPhase("examiner")}>
            Continue
          </button>
        </div>
      )}
      {phase === "done" && (
        <div className="cover">
          <p>That is the end of the speaking test. Saving…</p>
        </div>
      )}
    </div>
  );
}

function Prep({ onDone }: { onDone: () => void }) {
  const [left, setLeft] = useState(PREP_S);
  const end = useRef(Date.now() + PREP_S * 1000);
  useEffect(() => {
    const t = setInterval(() => {
      const s = Math.ceil((end.current - Date.now()) / 1000);
      setLeft(s);
      if (s <= 0) onDone();
    }, 250);
    return () => clearInterval(t);
  }, [onDone]);
  return (
    <>
      <p className="status">Preparation time: {mmss(Math.max(0, left))}. Think about what you will say; you can make notes.</p>
      <button onClick={onDone}>I'm ready to speak</button>
    </>
  );
}

/** Records one answer; stops at the time limit or when you click Finish. */
function Recorder(props: { stream: MediaStream; maxS: number; longTurn: boolean; onDone: (b: Blob, ms: number) => void; onRepeat?: () => void }) {
  const { stream, maxS, longTurn } = props;
  const [elapsed, setElapsed] = useState(0);
  const rec = useRef<MediaRecorder | null>(null);
  const onDone = useRef(props.onDone);
  onDone.current = props.onDone;

  useEffect(() => {
    let discarded = false; // unmounted without Finish (e.g. "Hear the question again")
    const r = new MediaRecorder(stream, { audioBitsPerSecond: 32_000 });
    const chunks: Blob[] = [];
    const t0 = Date.now();
    r.ondataavailable = (e) => chunks.push(e.data);
    r.onstop = () => !discarded && onDone.current(new Blob(chunks, { type: r.mimeType }), Date.now() - t0);
    r.start();
    rec.current = r;
    const t = setInterval(() => {
      const s = (Date.now() - t0) / 1000;
      setElapsed(s);
      if (s >= maxS && r.state === "recording") r.stop();
    }, 200);
    return () => {
      clearInterval(t);
      discarded = true;
      if (r.state === "recording") r.stop();
    };
  }, [stream, maxS]);

  const stop = () => rec.current?.state === "recording" && rec.current.stop();
  return (
    <>
      <p className="status rec">
        <span className="dot" aria-hidden /> Recording your answer: {mmss(elapsed)}
        {longTurn && <> of 2:00{elapsed < 60 && " (aim for at least one minute)"}</>}
      </p>
      <MicLevel stream={stream} />
      <p>
        <button className="primary" onClick={stop}>
          Finish answer
        </button>{" "}
        {props.onRepeat && <button onClick={props.onRepeat}>Hear the question again</button>}
      </p>
    </>
  );
}

/** A live input level bar, so you can see the microphone is hearing you. */
export function MicLevel({ stream }: { stream: MediaStream }) {
  const bar = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const ctx = new AudioContext();
    const analyser = ctx.createAnalyser();
    ctx.createMediaStreamSource(stream).connect(analyser);
    const data = new Uint8Array(analyser.fftSize);
    let frame = 0;
    const draw = () => {
      analyser.getByteTimeDomainData(data);
      const peak = data.reduce((m, v) => Math.max(m, Math.abs(v - 128)), 0) / 128;
      if (bar.current) bar.current.style.width = `${Math.min(100, peak * 150)}%`;
      frame = requestAnimationFrame(draw);
    };
    draw();
    return () => {
      cancelAnimationFrame(frame);
      ctx.close();
    };
  }, [stream]);
  return (
    <span className="miclevel" aria-hidden>
      <span ref={bar} />
    </span>
  );
}

/** Before the Speaking test: record three seconds and play them back. Start stays disabled until this works. */
export function MicCheck({ onOk }: { onOk: () => void }) {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [state, setState] = useState<"idle" | "recording" | "played" | "error">("idle");
  useEffect(() => () => stream?.getTracks().forEach((t) => t.stop()), [stream]);
  const test = async () => {
    try {
      const s = stream ?? (await navigator.mediaDevices.getUserMedia({ audio: true }));
      setStream(s);
      setState("recording");
      const r = new MediaRecorder(s);
      const chunks: Blob[] = [];
      r.ondataavailable = (e) => chunks.push(e.data);
      r.onstop = () => {
        const url = URL.createObjectURL(new Blob(chunks, { type: r.mimeType }));
        const a = new Audio(url);
        a.onended = () => URL.revokeObjectURL(url);
        a.play();
        setState("played");
        onOk();
      };
      r.start();
      setTimeout(() => r.stop(), 3000);
    } catch {
      setState("error");
    }
  };
  return (
    <div className="soundcheck">
      <strong>Microphone check</strong>
      <p>Use headphones in a quiet room. Say a sentence after pressing the button; you will hear it played back.</p>
      <button onClick={test} disabled={state === "recording"}>
        {state === "recording" ? "Recording for 3 seconds…" : "Test microphone"}
      </button>
      {stream && <MicLevel stream={stream} />}
      {state === "played" && <p className="muted">Did you hear yourself clearly? If not, check the browser's microphone setting and test again.</p>}
      {state === "error" && <p className="error">No microphone available. Allow it for this site in the browser's address bar.</p>}
    </div>
  );
}
