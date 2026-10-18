import type { EssayResult, WritingReport } from "../api";
import BandScale from "../components/BandScale";
import { sentence } from "../labels";

const half = (x: number) => Math.floor(x * 2 + 0.5) / 2; // same rounding as the server's bands
const mmss = (ms: number) => `${Math.floor(ms / 60000)}:${String(Math.round(ms / 1000) % 60).padStart(2, "0")}`;
const CRITERIA = [
  ["task", (n: number) => (n === 1 ? "Task Achievement" : "Task Response")],
  ["coherence_cohesion", () => "Coherence and Cohesion"],
  ["lexical_resource", () => "Lexical Resource"],
  ["grammar", () => "Grammatical Range and Accuracy"],
] as const;

/** The Writing part of a report: the band (once scored), then each essay with the examiners' feedback. */
export default function WritingReportView({ s, practice, target }: { s: WritingReport; practice: boolean; target: number }) {
  const waiting = s.tasks.some((t) => !t.result);
  return (
    <article className="report">
      <section className="hero">
        {s.band !== null ? (
          <>
            <h1>Writing band {s.band.toFixed(1)}</h1>
            <p className="lead">Task 2 counts twice as much as Task 1.</p>
            <BandScale band={s.band} target={target} estimate={false} />
          </>
        ) : waiting ? (
          <>
            <h1>{practice ? "Your essay is saved" : "Your writing is saved"}</h1>
            <p className="lead">
              It's waiting for the examiners. Open Claude Code in this project and say <b>score my essays</b>; this page shows the
              bands and feedback afterwards.
            </p>
          </>
        ) : (
          <h1>
            Task {s.tasks[0].task_number}: band {half(s.tasks[0].result!.task_band).toFixed(1)}
          </h1>
        )}
        {s.submit_reason === "timeout" && <p className="muted">Time ran out, so your saved text was submitted automatically.</p>}
      </section>

      {s.tasks.map((t) => (
        <section key={t.task_number} className="essay">
          <h2 className="section-title">
            Task {t.task_number}
            {t.result && <> · band {half(t.result.task_band).toFixed(1)}</>}
          </h2>
          <p className="muted">
            {t.word_count} words
            {t.word_count < t.min_words && ` (under the ${t.min_words} required)`} · {mmss(t.time_ms)} of active writing time
          </p>
          <details>
            <summary>The task</summary>
            {t.prompt.split("\n\n").map((p, i) => (
              <p key={i}>{p}</p>
            ))}
            {t.visual_url && <img className="visual" src={t.visual_url} alt="The task's chart, table or diagram" />}
          </details>
          <details open={!t.result}>
            <summary>Your answer</summary>
            <p className="essaytext">{t.text || "(no answer)"}</p>
          </details>
          {t.result && (
            <Feedback
              r={t.result}
              criteria={CRITERIA.map(([key, label]) => [key, label(t.task_number)])}
              example="One paragraph, about a band higher"
            />
          )}
        </section>
      ))}
    </article>
  );
}

/** Examiner feedback: per-criterion bands with quotes, next steps, errors and an improved example (Writing and Speaking). */
export function Feedback({ r, criteria, example }: { r: EssayResult; criteria: [string, string][]; example: string }) {
  return (
    <>
      {r.inconsistent && (
        <p className="muted">
          The first two examiners disagreed by more than a band, so a third one decided (the median counts).
        </p>
      )}
      {r.off_topic_flags.length > 0 && <p className="error">Off-topic: {r.off_topic_flags.join("; ")}</p>}
      <table className="grid criteria">
        <tbody>
          {criteria.map(([key, label]) => (
            <tr key={key}>
              <th>{label}</th>
              <td className="num">{r.criteria[key].band}</td>
              <td>
                {r.criteria[key].justification}
                {r.criteria[key].evidence.length > 0 && (
                  <span className="quotes">
                    {r.criteria[key].evidence.map((q) => (
                      <q key={q}>{q}</q>
                    ))}
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {r.to_reach_next_half_band.length > 0 && (
        <>
          <h3>To reach the next half band</h3>
          <ul>
            {r.to_reach_next_half_band.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </>
      )}
      {r.errors.length > 0 && (
        <>
          <h3>Errors to fix</h3>
          <table className="grid">
            <tbody>
              {r.errors.map((e, i) => (
                <tr key={i}>
                  <td>{sentence(e.category)}</td>
                  <td>
                    <s>{e.original}</s> → <b>{e.correction}</b>
                  </td>
                  <td className="muted">{e.explanation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      {r.improved_paragraph_example && (
        <>
          <h3>{example}</h3>
          <blockquote>{r.improved_paragraph_example}</blockquote>
        </>
      )}
    </>
  );
}
