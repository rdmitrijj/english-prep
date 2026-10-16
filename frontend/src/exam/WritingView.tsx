import { useRef, useState } from "react";
import type { WritingTask } from "../api";

/** Counts like the CD test's counter: anything between spaces is a word. */
export const wordCount = (text: string) => text.split(/\s+/).filter(Boolean).length;

/** The task (instructions and visual) on the left, the answer box on the right, a draggable splitter between. */
export default function WritingView(props: { task: WritingTask; text: string; onChange: (text: string) => void }) {
  const { task, text } = props;
  const [left, setLeft] = useState(45);
  const box = useRef<HTMLDivElement>(null);
  return (
    <div className="split writing" ref={box} style={{ gridTemplateColumns: `${left}% 8px 1fr` }}>
      <article className="task">
        {task.prompt.split("\n\n").map((p, i) => (
          <p key={i}>{p}</p>
        ))}
        {task.visual_url && <img src={task.visual_url} alt="The chart, table or diagram for this task" />}
      </article>
      <div
        className="splitter"
        role="separator"
        aria-orientation="vertical"
        onPointerDown={(e) => e.currentTarget.setPointerCapture(e.pointerId)}
        onPointerMove={(e) => {
          if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
          const r = box.current!.getBoundingClientRect();
          setLeft(Math.min(75, Math.max(25, ((e.clientX - r.left) / r.width) * 100)));
        }}
      />
      <div className="answer">
        {/* No spellcheck or autocorrect, as in the real test; copy and paste stay allowed (RESEARCH §7). */}
        <textarea
          aria-label={`Your answer to Task ${task.task_number}`}
          value={text}
          onChange={(e) => props.onChange(e.target.value)}
          spellCheck={false}
          autoCorrect="off"
          autoCapitalize="off"
          autoComplete="off"
        />
        <p className="wordcount">Word count: {wordCount(text)}</p>
      </div>
    </div>
  );
}
