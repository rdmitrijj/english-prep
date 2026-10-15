import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { api, type Answer, type Report, type User } from "../api";
import BandScale from "../components/BandScale";

const TARGET_S = 90; // Reading pace target per question (PLAN §4.4)
const secs = (ms: number) => Math.round(ms / 1000);
const mmss = (ms: number) => `${Math.floor(ms / 60000)}:${String(secs(ms) % 60).padStart(2, "0")}`;
const show = (a: Answer) => (Array.isArray(a) ? a.join(", ") : a) || "—";
const QTYPE: Record<string, string> = {
  tfng: "True / False / Not given",
  ynng: "Yes / No / Not given",
  mcq: "Multiple choice",
};
const CHOICE: Record<string, string> = { T: "TRUE", F: "FALSE", NG: "NOT GIVEN", Y: "YES", N: "NO" };
const qtype = (t: string) => QTYPE[t] ?? t[0].toUpperCase() + t.slice(1).replaceAll("_", " ");
/** "tfng:NG→T" → "NOT GIVEN read as TRUE"; "wrong_word" → "Wrong word". */
const error = (e: string | null) => {
  const m = e?.match(/^\w+:(\w+)→(\w+)$/);
  if (m) return `${CHOICE[m[1]]} read as ${CHOICE[m[2]]}`;
  return e ? e[0].toUpperCase() + e.slice(1).replaceAll("_", " ") : "Wrong";
};

export default function ReportPage() {
  const id = Number(useParams().attemptId);
  const report = useQuery({ queryKey: ["report", id], queryFn: () => api<Report>(`/attempts/${id}/report`) });
  const me = useQuery({ queryKey: ["me"], queryFn: () => api<User>("/auth/me") });

  if (report.isPending) return <p className="muted">Loading…</p>;
  if (report.error) return <p className="error">{report.error.message}</p>;
  const r = report.data;

  return (
    <>
      {r.report.sections.map((s) => (
        <article key={s.skill} className="report">
          <section className="hero">
            <p className="muted">
              {r.test_title}, {new Date(r.finished_at).toLocaleDateString(undefined, { day: "numeric", month: "long" })}
            </p>
            <h1>
              {s.skill[0].toUpperCase() + s.skill.slice(1)} band {s.band.toFixed(1)}
            </h1>
            <p className="lead">
              {s.raw} of {s.total} correct in {mmss(s.time_used_ms)}.
              {s.submit_reason === "timeout" && " Time ran out, so your saved answers were submitted automatically."}
            </p>
            <BandScale band={s.band} target={me.data?.target_band ?? 7} estimate={s.band_is_estimate} />
            {s.band_is_estimate && <p className="muted">* Below the official conversion table, so this band is an estimate.</p>}
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
              <h2 className="section-title">Pace by part</h2>
              <p className="muted">Target: {TARGET_S} s per question.</p>
              <table className="grid">
                <tbody>
                  {s.parts.map((p) => (
                    <tr key={p.number}>
                      <td>Part {p.number}</td>
                      <td>
                        {p.correct}/{p.total}
                      </td>
                      <td>{mmss(p.time_ms)}</td>
                      <td className={p.time_ms / p.total / 1000 > TARGET_S ? "slow" : undefined}>
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
        <Link to="/mock">Back to mock exams</Link>
      </p>
      <p className="disclaimer">Bands are AI/heuristic estimates, not official IELTS results.</p>
    </>
  );
}
