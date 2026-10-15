import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router";
import { api, type Answer, type Report } from "../api";

const TARGET_S = 90; // Reading pace target per question (PLAN §4.4)
const secs = (ms: number) => Math.round(ms / 1000);
const mmss = (ms: number) => `${Math.floor(ms / 60000)}:${String(secs(ms) % 60).padStart(2, "0")}`;
const show = (a: Answer) => (Array.isArray(a) ? a.join(", ") : a) || "—";

export default function ReportPage() {
  const id = Number(useParams().attemptId);
  const report = useQuery({ queryKey: ["report", id], queryFn: () => api<Report>(`/attempts/${id}/report`) });

  if (report.isPending) return <p>Loading…</p>;
  if (report.error) return <p className="error">{report.error.message}</p>;
  const r = report.data;

  return (
    <>
      <h1>{r.test_title}: report</h1>
      {r.report.sections.map((s) => (
        <section key={s.skill} className="report">
          <h2>
            {s.skill[0].toUpperCase() + s.skill.slice(1)}: band {s.band.toFixed(1)}
            {s.band_is_estimate && " (estimate: below the official table)"}
          </h2>
          <p>
            {s.raw} / {s.total} correct · time used {mmss(s.time_used_ms)}
            {s.submit_reason === "timeout" && " · submitted automatically when time ran out"}
          </p>

          <div className="cols">
            <table className="grid">
              <caption>Accuracy by question type</caption>
              <tbody>
                {s.by_type.map((t) => (
                  <tr key={t.qtype}>
                    <td>{t.qtype.replaceAll("_", " ")}</td>
                    <td>
                      {t.correct} / {t.total}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <table className="grid">
              <caption>Time by part (target {TARGET_S} s per question)</caption>
              <tbody>
                {s.parts.map((p) => (
                  <tr key={p.number}>
                    <td>Part {p.number}</td>
                    <td>
                      {p.correct} / {p.total}
                    </td>
                    <td>{mmss(p.time_ms)}</td>
                    <td className={p.time_ms / p.total / 1000 > TARGET_S ? "slow" : undefined}>
                      {secs(p.time_ms / p.total)} s/question
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <table className="grid">
              <caption>Slowest questions</caption>
              <tbody>
                {s.slowest.map((q) => (
                  <tr key={q.number}>
                    <td>Q{q.number}</td>
                    <td>{secs(q.time_ms)} s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

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
                    {q.flagged && " ○"}
                  </td>
                  <td>{q.qtype.replaceAll("_", " ")}</td>
                  <td>{show(q.answer)}</td>
                  <td>{q.accepted.join(" / ")}</td>
                  <td>{q.is_correct ? "✓" : `✗ ${q.error_class?.replaceAll("_", " ")}`}</td>
                  <td>{secs(q.time_ms)} s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
      <p>
        <Link to="/mock">Back to mock exams</Link>
      </p>
      <p className="disclaimer">Bands are AI/heuristic estimates, not official IELTS results.</p>
    </>
  );
}
