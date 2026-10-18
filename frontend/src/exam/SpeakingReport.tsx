import type { SpeakingReport } from "../api";
import BandScale from "../components/BandScale";
import { Feedback } from "./WritingReport";

const CRITERIA: [string, string][] = [
  ["fluency_coherence", "Fluency and Coherence"],
  ["lexical_resource", "Lexical Resource"],
  ["grammar", "Grammatical Range and Accuracy"],
  ["pronunciation", "Pronunciation (estimate)"],
];
const secs = (ms: number) => Math.round(ms / 1000);

/** The Speaking part of a report: band and examiner feedback once scored, fluency numbers, and every answer to replay. */
export default function SpeakingReportView({ s, attemptId, target }: { s: SpeakingReport; attemptId: number; target: number }) {
  const answers = s.parts.flatMap((p) => p.answers);
  return (
    <article className="report">
      <section className="hero">
        {s.band !== null ? (
          <>
            <h1>Speaking band {s.band.toFixed(1)}</h1>
            <p className="lead">
              Scored from transcripts of your recordings. Pronunciation can't be judged from text, so it is only an estimate.
            </p>
            <BandScale band={s.band} target={target} estimate />
          </>
        ) : (
          <>
            <h1>Your answers are saved</h1>
            <p className="lead">
              {answers.length} answers recorded. They're waiting to be transcribed and scored: open Claude Code in this project and say{" "}
              <b>score my speaking</b>; this page shows the band and feedback afterwards.
            </p>
          </>
        )}
        {s.submit_reason === "timeout" && <p className="muted">The time limit passed, so the test ended with the answers recorded so far.</p>}
      </section>

      {s.transcribed && answers.length > 0 && (
        <ul className="stats">
          <li>
            <b>{s.stats.wpm}</b> words per minute
          </li>
          <li>
            <b>{s.stats.long_pauses}</b> pauses of 2 s or more
          </li>
          <li>
            <b>{s.stats.fillers}</b> fillers (um, er…)
          </li>
          <li>
            <b>{s.stats.words}</b> words in all
          </li>
        </ul>
      )}

      {s.result && (
        <section className="essay">
          <h2 className="section-title">Examiner feedback</h2>
          <Feedback r={s.result} criteria={CRITERIA} example="One answer, about a band higher" />
        </section>
      )}

      {s.parts.map((p) => (
        <section key={p.number} className="essay">
          <h2 className="section-title">Part {p.number}</h2>
          {p.cue_card && (
            <p className="muted">
              Topic card: {p.cue_card.task} You should say: {p.cue_card.bullets.join("; ")}; {p.cue_card.final}
            </p>
          )}
          {p.answers.length === 0 && <p className="muted">No answers recorded in this part.</p>}
          {p.answers.map((a) => (
            <div key={a.id} className="spoken">
              <p>
                <b>{a.question}</b> <span className="muted">({secs(a.duration_ms)} s)</span>
              </p>
              <audio controls preload="none" src={`/api/attempts/${attemptId}/speaking/${a.id}/audio`} />
              {a.transcript !== null && <p className="essaytext">{a.transcript || "(nothing recognised)"}</p>}
            </div>
          ))}
        </section>
      ))}
    </article>
  );
}
