import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { api, type Attempt, type AttemptSummary, type MockTest, type Skill } from "../api";

const READY: Skill[] = ["listening", "reading", "writing", "speaking"];
const SPEAKING_S = 14 * 60; // the interview itself; the section's server deadline (20 min) is only a safety net
const seconds = (s: { skill: Skill; duration_s: number | null }) => (s.skill === "speaking" ? SPEAKING_S : (s.duration_s ?? 0));
const hours = (s: number) => `${Math.floor(s / 3600)} h ${Math.round((s % 3600) / 60)} min`;

export default function Mock() {
  const navigate = useNavigate();
  const tests = useQuery({ queryKey: ["tests"], queryFn: () => api<MockTest[]>("/tests") });
  const attempts = useQuery({ queryKey: ["attempts"], queryFn: () => api<AttemptSummary[]>("/attempts") });
  const start = useMutation({
    mutationFn: (v: { test_id: number; skill?: Skill }) =>
      api<Attempt>("/attempts", { method: "POST", body: { mode: v.skill ? "section_mock" : "full_mock", ...v } }),
    onSuccess: (a) => navigate(`/exam/${a.id}`),
  });

  const mocks = attempts.data?.filter((a) => a.mode !== "practice") ?? [];
  return (
    <>
      <section className="hero">
        <h1>Mock exam</h1>
        <p className="lead">
          The whole test (Listening, Reading, Writing, then Speaking) or one section, under real conditions: the clock runs on the
          server, and your answers are submitted when time is up.
        </p>
      </section>
      {start.error && <p className="error">{start.error.message}</p>}

      <ul className="modes">
        {tests.data?.map((t) => (
          <li key={t.id}>
            <h2>{t.title}</h2>
            <div className="actions">
              <button className="button" disabled={start.isPending} onClick={() => start.mutate({ test_id: t.id })}>
                Full mock, {hours(t.sections.filter((s) => READY.includes(s.skill)).reduce((n, s) => n + seconds(s), 0))}
              </button>
              {t.sections
                .filter((s) => READY.includes(s.skill))
                .map((s) => (
                  <button
                    key={s.skill}
                    className="button"
                    disabled={start.isPending}
                    onClick={() => start.mutate({ test_id: t.id, skill: s.skill })}
                  >
                    Start {s.skill}, {Math.round(seconds(s) / 60)} min
                  </button>
                ))}
            </div>
          </li>
        ))}
      </ul>
      {tests.data?.length === 0 && <p className="lead">No mock tests yet. Load content with the seed command first.</p>}

      <h2 className="section-title">Your attempts</h2>
      {mocks.length === 0 && <p className="muted">Attempts you start will appear here.</p>}
      <ul className="attempts">
        {mocks.map((a) => (
          <li key={a.id}>
            <span className="when">{new Date(a.started_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}</span>
            <span className="what">
              {a.test_title}, {a.skills.join(", ")}
            </span>
            {a.status === "completed" ? (
              <>
                <span className="chip">
                  {a.bands.includes(null) ? "Awaiting scoring" : `Band ${a.bands.map((b) => b!.toFixed(1)).join(" / ")}`}
                </span>
                <Link to={`/report/${a.id}`}>View report</Link>
              </>
            ) : (
              <>
                <span className="chip live">In progress</span>
                <Link to={`/exam/${a.id}`}>Resume</Link>
              </>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
