import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { api, type Answer, type Report, type User } from "../api";
import BandScale from "../components/BandScale";
import { errorLabel as error, qtypeLabel as qtype } from "../labels";
import WritingReportView from "./WritingReport";

const TARGET_S = 90; // Reading pace target per question (PLAN §4.4)
const secs = (ms: number) => Math.round(ms / 1000);
const mmss = (ms: number) => `${Math.floor(ms / 60000)}:${String(secs(ms) % 60).padStart(2, "0")}`;
const show = (a: Answer) => (Array.isArray(a) ? a.join(", ") : a) || "—";
export default function ReportPage() {
  const id = Number(useParams().attemptId);
  const report = useQuery({ queryKey: ["report", id], queryFn: () => api<Report>(`/attempts/${id}/report`) });
  const me = useQuery({ queryKey: ["me"], queryFn: () => api<User>("/auth/me") });

  if (report.isPending) return <p className="muted">Loading…</p>;
  if (report.error) return <p className="error">{report.error.message}</p>;
  const r = report.data;
  const practice = r.mode === "practice" || r.mode === "trainer";
  const unit = practice ? "Passage" : "Part";

  const bands = r.report.sections.map((s) => s.band);
  return (
    <>
      {r.mode === "full_mock" && (
        <section className="hero">
          <p className="muted">
            {r.test_title}, {new Date(r.finished_at).toLocaleDateString(undefined, { day: "numeric", month: "long" })}
          </p>
          <h1>{r.overall_band === null ? "Overall band: waiting for Writing" : `Estimated overall band ${r.overall_band.toFixed(1)}`}</h1>
          <p className="lead">
            {r.report.sections.map((s, i) => `${s.skill[0].toUpperCase() + s.skill.slice(1)} ${bands[i]?.toFixed(1) ?? "–"}`).join(" · ")}
            . Speaking not taken, so the overall is the average of these sections, rounded like the real one.
          </p>
          {r.overall_band !== null && <BandScale band={r.overall_band} target={me.data?.target_band ?? 7} estimate={r.overall_is_estimate} />}
        </section>
      )}
      {r.report.sections.map((s) => s.skill === "writing" ? (
        <WritingReportView key={s.skill} s={s} practice={practice} target={me.data?.target_band ?? 7} />
      ) : (
        <article key={s.skill} className="report">
          <section className="hero">
            <p className="muted">
              {r.test_title}, {new Date(r.finished_at).toLocaleDateString(undefined, { day: "numeric", month: "long" })}
            </p>
            {s.band === null ? (
              <>
                <h1>
                  Practice: {s.raw} of {s.total} correct
                </h1>
                <p className="lead">
                  {mmss(s.time_on_questions_ms)} of active time on the questions (idle minutes and hidden-tab time don't count).
                </p>
              </>
            ) : (
              <>
                <h1>
                  {s.skill[0].toUpperCase() + s.skill.slice(1)} band {s.band.toFixed(1)}
                </h1>
                <p className="lead">
                  {s.raw} of {s.total} correct in {mmss(s.time_used_ms)}.
                  {s.submit_reason === "timeout" && " Time ran out, so your saved answers were submitted automatically."}
                </p>
                <BandScale band={s.band} target={me.data?.target_band ?? 7} estimate={s.band_is_estimate} />
                {s.band_is_estimate && <p className="muted">* Below the official conversion table, so this band is an estimate.</p>}
              </>
            )}
          </section>

          <div className="panels">
            <section>
              <h2 className="section-title">Accuracy by question type</h2>
              <ul className="bars">
                {s.by_type.map((t) => (
                  <li key={t.qtype}>
                    <span>{qtype(t.qtype)}</span>
                    <span className="bar" aria-hidden>
                      <span style={{ width: `${(t.correct / t.total) * 100}%` }} />
                    </span>
                    <span className="num">
                      {t.correct}/{t.total}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
            <section>
              <h2 className="section-title">Pace by {unit.toLowerCase()}</h2>
              <p className="muted">
                {s.skill === "listening" ? "The recording sets the pace in Listening." : `Target: ${TARGET_S} s per question.`}
              </p>
              <table className="grid">
                <tbody>
                  {s.parts.map((p) => (
                    <tr key={p.number}>
                      <td>
                        {unit} {p.number}
                      </td>
                      <td>
                        {p.correct}/{p.total}
                      </td>
                      <td>{mmss(p.time_ms)}</td>
                      <td className={s.skill !== "listening" && p.time_ms / p.total / 1000 > TARGET_S ? "slow" : undefined}>
                        {secs(p.time_ms / p.total)} s per question
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <h2 className="section-title">Slowest questions</h2>
              <p>
                {s.slowest.map((q) => (
                  <span key={q.number} className="chip">
                    Q{q.number}: {secs(q.time_ms)} s
                  </span>
                ))}
              </p>
            </section>
          </div>

          <h2 className="section-title">Every answer</h2>
          <table className="grid answers">
            <thead>
              <tr>
                <th>Q</th>
                <th>Type</th>
                <th>Your answer</th>
                <th>Correct answer</th>
                <th>Result</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {s.questions.map((q) => (
                <tr key={q.number} className={q.is_correct ? "right" : "wrong"}>
                  <td>
                    {q.number}
                    {q.flagged && <span title="Marked for review"> ○</span>}
                  </td>
                  <td>{qtype(q.qtype)}</td>
                  <td>{show(q.answer)}</td>
                  <td>{q.accepted.join(" / ")}</td>
                  <td className="result">{q.is_correct ? "Correct" : error(q.error_class)}</td>
                  <td>{secs(q.time_ms)} s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </article>
      ))}
      <p>
        {r.mode === "trainer" ? (
          <Link to="/trainer">Back to the trainer</Link>
        ) : practice ? (
          <Link to="/practice">Back to practice</Link>
        ) : (
          <Link to="/mock">Back to mock exams</Link>
        )}
      </p>
      <p className="disclaimer">Bands are AI/heuristic estimates, not official IELTS results.</p>
    </>
  );
}
