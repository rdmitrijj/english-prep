import type { Answer, Feedback } from "../api";
import { errorLabel } from "../labels";

const show = (a: Answer) => (Array.isArray(a) ? a.join(", ") : a) || "no answer";

/** Scroll to a question's evidence in the passage and pulse it. */
function showEvidence(qid: number) {
  const mark = document.querySelector(`mark[data-ev~="${qid}"]`);
  if (!mark) return;
  mark.scrollIntoView({ block: "center", behavior: "smooth" });
  mark.classList.add("pulse");
  setTimeout(() => mark.classList.remove("pulse"), 2500);
}

export default function FeedbackPanel({ results }: { results: Feedback[] }) {
  const sorted = [...results].sort((a, b) => a.number - b.number);
  const correct = sorted.filter((f) => f.is_correct).length;
  return (
    <div className="feedback">
      <p className="fbscore">
        {correct} of {sorted.length} correct
      </p>
      {sorted.map((f) => (
        <div key={f.question_id} className={`fb ${f.is_correct ? "right" : "wrong"}`}>
          <p>
            <b>{f.number}</b>{" "}
            {f.is_correct ? (
              <>
                Correct: <b>{show(f.answer)}</b>
              </>
            ) : (
              <>
                You wrote <s>{show(f.answer)}</s>. Answer: <b>{f.accepted.join(" / ")}</b> <span className="why">({errorLabel(f.error_class)})</span>
              </>
            )}
          </p>
          <p>{f.explanation.correct}</p>
          {f.explanation.distractors.length > 0 && (
            <ul>
              {f.explanation.distractors.map((d) => (
                <li key={d.option}>
                  <b>{d.option}</b>: {d.why_wrong}
                </li>
              ))}
            </ul>
          )}
          <button className="link" onClick={() => showEvidence(f.question_id)}>
            Show in passage
          </button>
        </div>
      ))}
    </div>
  );
}
