import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { api, type AttemptSummary, type Dashboard } from "../api";
import { sentence, tagLabel } from "../labels";
import { useTrain } from "./Dashboard";

export default function Trainer() {
  const dash = useQuery({ queryKey: ["dashboard"], queryFn: () => api<Dashboard>("/dashboard") });
  const attempts = useQuery({ queryKey: ["attempts"], queryFn: () => api<AttemptSummary[]>("/attempts") });
  const train = useTrain();
  const d = dash.data;
  const sessions = attempts.data?.filter((a) => a.mode === "trainer") ?? [];

  return (
    <>
      <section className="hero">
        <h1>Weakness trainer</h1>
        <p className="lead">
          About 20 questions: questions you missed that are due again (they come back after 1, 3, 7, 16 and 35 days until you get them
          right each time), new questions from your weakest areas, and your slowest question type.
        </p>
      </section>
      {dash.error && <p className="error">{dash.error.message}</p>}
      {d && (
        <ul className="modes">
          {(["reading", "listening"] as const).map((skill) => {
            const weak = d.weaknesses.filter((t) => t.skill === skill).slice(0, 3);
            return (
              <li key={skill}>
                <div>
                  <h2>{sentence(skill)}</h2>
                  <p>{weak.length ? `Focus: ${weak.map(tagLabel).join(", ")}.` : "No weaknesses yet: new questions across all types."}</p>
                </div>
                <button className="button" disabled={train.isPending} onClick={() => train.mutate({ skill })}>
                  Start
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {d && <p className="muted">{d.reviews_due ? `${d.reviews_due} reviews due now.` : "No reviews due right now."}</p>}
      {train.error && <p className="error">{train.error.message}</p>}

      <h2 className="section-title">Recent sessions</h2>
      {sessions.length === 0 && <p className="muted">Sessions you start will appear here.</p>}
      <ul className="attempts">
        {sessions.map((a) => (
          <li key={a.id}>
            <span className="when">{new Date(a.started_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}</span>
            <span className="what">{sentence(a.skills[0])} trainer</span>
            {a.status === "completed" ? (
              <Link to={`/report/${a.id}`}>View summary</Link>
            ) : (
              <>
                <span className="chip live">In progress</span>
                <Link to={`/practice/${a.id}`}>Resume</Link>
              </>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
