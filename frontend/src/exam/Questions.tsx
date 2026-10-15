import { type ReactNode, useState } from "react";
import type { Answer, Group, Layout, Option, Question } from "../api";

type Props = {
  group: Group;
  answers: Record<number, Answer>;
  setAnswer: (ids: number[], value: Answer) => void;
  current: number; // question id
  focus: (qid: number) => void;
  locked?: boolean; // practice: the group was checked, answers can't change
  results?: Record<number, boolean>; // practice: question id → correct?
};

const TFNG = ["TRUE", "FALSE", "NOT GIVEN"];
const YNNG = ["YES", "NO", "NOT GIVEN"];
const GAP_MARK = /_{3,}|…/; // how a gap is written inside a question prompt

/** One question group: "Questions 1–6", the rubric, then the widget its type uses (CD style, PLAN §2). */
export default function QuestionGroup(props: Props) {
  const nums = props.group.questions.map((q) => q.number);
  return (
    <section className="qgroup">
      <h3>
        Questions {nums[0]}
        {nums.length > 1 && `–${nums.at(-1)}`}
      </h3>
      <p className="rubric">{props.group.instructions}</p>
      {/* a disabled fieldset disables every input, radio, checkbox and button inside it */}
      <fieldset className="qbody" disabled={props.locked}>
        <Body {...props} />
      </fieldset>
    </section>
  );
}

function Body(props: Props) {
  const { group: g, answers, setAnswer } = props;
  const text = (q: Question) => (answers[q.id] as string | null) ?? "";

  if (g.pick > 1) return <MultiChoice {...props} />;
  if (g.options) return <Matching {...props} />;
  if (g.max_words !== null) {
    const gap = (q: Question) => (
      <input
        id={`q-${q.number}`}
        className="gap"
        aria-label={`Question ${q.number}`}
        placeholder={String(q.number)}
        value={text(q)}
        onChange={(e) => setAnswer([q.id], e.target.value)}
        onFocus={() => props.focus(q.id)}
        spellCheck={false}
        autoComplete="off"
        autoCapitalize="off"
        autoCorrect="off"
      />
    );
    if (g.layout) return <LayoutView layout={g.layout} group={g} gap={gap} />;
    return g.questions.map((q) => {
      const [before, after] = GAP_MARK.test(q.prompt) ? q.prompt.split(GAP_MARK, 2) : [q.prompt + " ", ""];
      return (
        <Item key={q.id} q={q} {...props} anchor={false}>
          {before}
          {gap(q)}
          {after}
        </Item>
      );
    });
  }

  // TRUE/FALSE/NOT GIVEN, YES/NO/NOT GIVEN, and single-answer multiple choice: radio buttons.
  return g.questions.map((q) => {
    const choices: Option[] =
      g.qtype === "tfng" || g.qtype === "ynng"
        ? (g.qtype === "tfng" ? TFNG : YNNG).map((v) => ({ letter: v, text: "" }))
        : (q.options ?? []);
    return (
      <Item key={q.id} q={q} {...props}>
        {q.prompt}
        <div className="choices">
          {choices.map((o) => (
            <label key={o.letter}>
              <input
                type="radio"
                name={`q${q.id}`}
                checked={answers[q.id] === o.letter}
                onChange={() => setAnswer([q.id], o.letter)}
                onFocus={() => props.focus(q.id)}
              />
              <b>{o.letter}</b> {o.text}
            </label>
          ))}
        </div>
      </Item>
    );
  });
}

/** A numbered question row; clicking anywhere in it makes it the current question. */
function Item(props: Props & { q: Question; anchor?: boolean; children: ReactNode }) {
  const { q } = props;
  const result = props.results?.[q.id];
  return (
    <div
      id={props.anchor === false ? undefined : `q-${q.number}`}
      className={`q${props.current === q.id ? " current" : ""}${result === undefined ? "" : result ? " right" : " wrong"}`}
      onPointerDown={() => props.focus(q.id)}
    >
      <b className="qno">{q.number}</b>
      <div>{props.children}</div>
    </div>
  );
}

/** Notes / summary / table / flow-chart with gaps written as {number}. */
function LayoutView({ layout, group, gap }: { layout: Layout; group: Group; gap: (q: Question) => ReactNode }) {
  const byNumber = new Map(group.questions.map((q) => [String(q.number), q]));
  const fill = (s: string) =>
    s.split(/\{(\d+)\}/).map((piece, i) => {
      const q = i % 2 ? byNumber.get(piece) : undefined;
      return q ? <span key={i}>{gap(q)}</span> : <span key={i}>{i % 2 ? `{${piece}}` : piece}</span>;
    });
  return (
    <div className="layout">
      {layout.title && <h4>{layout.title}</h4>}
      {layout.template && layout.template.split("\n").map((line, i) => <p key={i}>{fill(line)}</p>)}
      {layout.table && (
        <table className="grid">
          <thead>
            <tr>
              {layout.table.columns.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {layout.table.rows.map((row, i) => (
              <tr key={i}>
                {row.map((cell, j) => (
                  <td key={j}>{fill(cell)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {layout.steps && (
        <div className="flow">
          {layout.steps.map((step, i) => (
            <div key={i}>
              {i > 0 && <div className="arrow">↓</div>}
              <div className="step">{fill(step)}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Headings, features, sentence endings, information, summary-from-a-list: drag an option onto a gap,
 * or click an option and then the gap (keyboard and touch friendly). Clicking a filled gap empties it. */
function Matching(props: Props) {
  const { group: g, answers, setAnswer } = props;
  const [selected, setSelected] = useState<string | null>(null);
  const label = (letter: string) => {
    const o = g.options!.find((o) => o.letter === letter);
    return !o || o.text === `Paragraph ${letter}` ? letter : `${letter}  ${o.text}`;
  };

  const zone = (q: Question) => {
    const value = answers[q.id] as string | null;
    const place = () => {
      if (props.locked) return;
      setAnswer([q.id], selected ?? null);
      setSelected(null);
      props.focus(q.id);
    };
    return (
      <span
        id={`q-${q.number}`}
        className={`drop${value ? " filled" : ""}`}
        role="button"
        tabIndex={0}
        aria-label={`Question ${q.number}: ${value ? label(value) : "empty"}`}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (props.locked) return;
          setAnswer([q.id], e.dataTransfer.getData("text/plain"));
          props.focus(q.id);
        }}
        onClick={place}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), place())}
      >
        {value ? label(value) : q.number}
      </span>
    );
  };

  return (
    <>
      <div className="options" aria-label="Options">
        {g.options!.map((o) => (
          <button
            key={o.letter}
            draggable
            className={`opt${selected === o.letter ? " selected" : ""}`}
            onDragStart={(e) => e.dataTransfer.setData("text/plain", o.letter)}
            onClick={() => setSelected(selected === o.letter ? null : o.letter)}
          >
            {label(o.letter)}
          </button>
        ))}
      </div>
      {g.layout?.template || g.layout?.table || g.layout?.steps ? (
        <LayoutView layout={g.layout} group={g} gap={zone} />
      ) : (
        <>
          {g.layout?.title && <p className="stem">{g.layout.title}</p>}
          {g.questions.map((q) => (
          <Item key={q.id} q={q} {...props} anchor={false}>
            {q.prompt} {zone(q)}
          </Item>
          ))}
        </>
      )}
    </>
  );
}

/** "Choose TWO letters": one checkbox list; the same selection is saved under each question number. */
function MultiChoice(props: Props) {
  const { group: g, answers, setAnswer } = props;
  const ids = g.questions.map((q) => q.id);
  const chosen = (answers[ids[0]] as string[] | null) ?? [];
  const toggle = (letter: string) => {
    const next = chosen.includes(letter) ? chosen.filter((l) => l !== letter) : [...chosen, letter];
    if (next.length <= g.pick) setAnswer(ids, next.sort());
  };
  return (
    <Item q={g.questions[0]} {...props}>
      {g.questions.slice(1).map((q) => (
        <span key={q.id} id={`q-${q.number}`} />
      ))}
      {g.questions[0].prompt}
      <div className="choices">
        {g.options!.map((o) => (
          <label key={o.letter}>
            <input type="checkbox" checked={chosen.includes(o.letter)} onChange={() => toggle(o.letter)} />
            <b>{o.letter}</b> {o.text}
          </label>
        ))}
      </div>
    </Item>
  );
}
