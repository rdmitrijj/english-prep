import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router";
import { api, type Attempt, type AttemptSummary, type Dashboard, type SkillStats, type TagStat } from "../api";
import BandTrend from "../components/BandTrend";
import { criterionLabel, errorLabel, sentence, tagLabel } from "../labels";

const pct = (x: number) => `${Math.round(x * 100)}%`;
const KINDS = [
  ["qtype", "Question type"],
  ["topic", "Topic"],
  ["sub_skill", "Skill"],
] as const;

/** Start a trainer session aimed at one weak tag ("Train this"), or at your top weaknesses when no tag is given. */
export function useTrain() {
  const navigate = useNavigate();
  return useMutation({
    mutationFn: (body: { skill: string; kind?: string; key?: string }) => api<Attempt>("/trainer/sessions", { method: "POST", body }),
    onSuccess: (a) => navigate(`/practice/${a.id}`),
  });
}

export default function DashboardPage() {
  const dash = useQuery({ queryKey: ["dashboard"], queryFn: () => api<Dashboard>("/dashboard") });
  const attempts = useQuery({ queryKey: ["attempts"], queryFn: () => api<AttemptSummary[]>("/attempts") });
  const train = useTrain();

  if (dash.isPending) return <p className="muted">Loading…</p>;
  if (dash.error) return <p className="error">{dash.error.message}</p>;
  const d = dash.data;
  const skills = Object.entries(d.skills) as [string, SkillStats][];
  const empty = !d.bands.length && !skills.length && !d.writing.criteria.length;

  return (
    <>
      <section className="hero">
        <h1>Progress</h1>
        <p className="lead">
          Target band {d.target_band.toFixed(1)}.{" "}
          {d.reviews_due > 0 ? (
            <>
              {d.reviews_due} question{d.reviews_due > 1 ? "s" : ""} you missed {d.reviews_due > 1 ? "are" : "is"} due for review in the{" "}
              <Link to="/trainer">trainer</Link>.
            </>
          ) : (
            "No reviews due today."
          )}
        </p>
      </section>
      {empty && <p className="lead">Take a mock or practise a few question sets, and your progress will show here.</p>}

      {d.bands.length > 0 && (
        <section>
          <h2 className="section-title">Mock bands</h2>
          <BandTrend bands={d.bands} target={d.target_band} />
        </section>
      )}

      <section>
        <h2 className="section-title">Your weaknesses</h2>
        {d.weaknesses.length === 0 ? (
          <p className="muted">
            Nothing stands out yet. A question type, topic or skill becomes a weakness after at least 8 answers, when your accuracy is
            below what band {d.target_band.toFixed(1)} needs or you are too slow on it.
          </p>
        ) : (
          <ul className="weak">
            {d.weaknesses.map((t) => (
              <li key={`${t.skill}-${t.kind}-${t.key}`}>
                <div>
                  <strong>{tagLabel(t)}</strong>{" "}
                  <span className="muted">
                    {sentence(t.skill)} · {KINDS.find(([k]) => k === t.kind)![1].toLowerCase()}
                  </span>
                  <p className="muted">{why(t, d.skills[t.skill]!)}</p>
                </div>
                <button className="button" disabled={train.isPending} onClick={() => train.mutate({ skill: t.skill, kind: t.kind, key: t.key })}>
                  Train this
                </button>
              </li>
            ))}
          </ul>
        )}
        {train.error && <p className="error">{train.error.message}</p>}
      </section>

      {skills.map(([skill, s]) => (
        <section key={skill}>
          <h2 className="section-title">
            {sentence(skill)}: {pct(s.accuracy)} correct recently <span className="muted">(band {d.target_band.toFixed(1)} needs about {pct(s.goal)})</span>
          </h2>
          <div className="panels">
            {KINDS.map(([kind, title]) => (
              <TagTable key={kind} title={title} tags={s.tags.filter((t) => t.kind === kind)} target={s.target_s} />
            ))}
            {s.errors.length > 0 && (
              <section>
                <h3>Most common mistakes</h3>
                <ul className="plain">
                  {s.errors.map((e) => (
                    <li key={e.error_class}>
                      {errorLabel(e.error_class)} <span className="muted">× {e.count}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        </section>
      ))}

      {d.writing.criteria.length > 0 && (
        <section>
          <h2 className="section-title">Writing</h2>
          <div className="panels">
            <section>
              <h3>Average band per criterion</h3>
              <table className="grid">
                <tbody>
                  {d.writing.criteria.map((c) => (
                    <tr key={c.key} className={c.weak ? "slow" : undefined}>
                      <td>{criterionLabel(c.key)}</td>
                      <td className="num">{c.average.toFixed(1)}</td>
                      <td className="muted">{c.n} essays</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <section>
              <h3>Recurring errors</h3>
              <table className="grid">
                <tbody>
                  {d.writing.errors.map((e) => (
                    <tr key={e.category} className={e.weak ? "slow" : undefined}>
                      <td>{sentence(e.category)}</td>
                      <td className="num">{e.count}</td>
                      <td className="muted">in {e.essays} essays</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="muted">
                <Link to="/practice">Practise writing</Link> to work on these.
              </p>
            </section>
          </div>
        </section>
      )}

      <section>
        <h2 className="section-title">History</h2>
        <ul className="attempts">
          {(attempts.data ?? [])
            .filter((a) => a.status === "completed")
            .map((a) => (
              <li key={a.id}>
                <span className="when">{new Date(a.started_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })}</span>
                <span className="what">
                  {a.mode === "section_mock" ? a.test_title : sentence(a.mode)}, {a.skills.join(", ")}
                </span>
                {a.bands.some((b) => b !== null) && <span className="chip">Band {a.bands.map((b) => b?.toFixed(1) ?? "–").join(" / ")}</span>}
                <Link to={`/report/${a.id}`}>Report</Link>
              </li>
            ))}
        </ul>
      </section>
    </>
  );
}

function why(t: TagStat, s: SkillStats) {
  const parts = [`${pct(t.accuracy)} correct over ${t.n} answers (needs ${pct(s.goal)})`];
  if (t.pace && t.pace > 1 && t.median_s) parts.push(`${Math.round(t.median_s)} s per question, target ${s.target_s} s`);
  return parts.join("; ");
}

function TagTable({ title, tags, target }: { title: string; tags: TagStat[]; target: number | null }) {
  if (!tags.length) return null;
  return (
    <section>
      <h3>{title}</h3>
      <table className="grid">
        <thead>
          <tr>
            <th></th>
            <th>Correct</th>
            <th>Answers</th>
            {target && <th>Time</th>}
          </tr>
        </thead>
        <tbody>
          {tags.map((t) => (
            <tr key={t.key} className={t.weak ? "slow" : undefined}>
              <td>{tagLabel(t)}</td>
              <td className="num" title={`${pct(t.raw_accuracy)} before smoothing`}>
                {pct(t.accuracy)}
              </td>
              <td className="num">{t.n}</td>
              {target && <td className="num">{t.median_s ? `${Math.round(t.median_s)} s` : "–"}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
