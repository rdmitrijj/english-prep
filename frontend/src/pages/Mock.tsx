import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { api, type Attempt, type AttemptSummary, type MockTest, type Skill } from "../api";

const READY: Skill[] = ["reading"]; // ponytail: listening (M5) and writing (M6) join this list later

export default function Mock() {
  const navigate = useNavigate();
  const tests = useQuery({ queryKey: ["tests"], queryFn: () => api<MockTest[]>("/tests") });
  const attempts = useQuery({ queryKey: ["attempts"], queryFn: () => api<AttemptSummary[]>("/attempts") });
  const start = useMutation({
    mutationFn: (v: { test_id: number; skill: Skill }) =>
      api<Attempt>("/attempts", { method: "POST", body: { mode: "section_mock", ...v } }),
    onSuccess: (a) => navigate(`/exam/${a.id}`),
  });

  return (
    <>
      <h1>Mock exam</h1>
      <p>Section mocks run under real conditions: a server-side timer, and automatic submission when time is up.</p>
      {start.error && <p className="error">{start.error.message}</p>}
      <ul className="cards">
        {tests.data?.map((t) => (
          <li key={t.id}>
            <strong>{t.title}</strong>
            {t.sections
              .filter((s) => READY.includes(s.skill))
              .map((s) => (
                <button key={s.skill} disabled={start.isPending} onClick={() => start.mutate({ test_id: t.id, skill: s.skill })}>
                  Start {s.skill} ({Math.round((s.duration_s ?? 0) / 60)} min)
                </button>
              ))}
          </li>
        ))}
      </ul>
      {tests.data?.length === 0 && <p>No mock tests yet. Seed content first.</p>}

      <h2>Your attempts</h2>
      {attempts.data?.length === 0 && <p>None yet.</p>}
      <table className="grid">
        <tbody>
          {attempts.data?.map((a) => (
            <tr key={a.id}>
              <td>{new Date(a.started_at).toLocaleString()}</td>
              <td>
                {a.test_title} · {a.skills.join(", ")}
              </td>
              <td>{a.status === "completed" ? `Band ${a.bands.map((b) => b?.toFixed(1)).join(" / ")}` : "In progress"}</td>
              <td>{a.status === "completed" ? <Link to={`/report/${a.id}`}>Report</Link> : <Link to={`/exam/${a.id}`}>Resume</Link>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
