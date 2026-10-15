import { Fragment, type MouseEvent, type ReactNode, useEffect, useRef, useState } from "react";
import type { Highlight, Part } from "../api";

type Props = { part: Part; highlights: Highlight[]; setHighlights: (h: Highlight[]) => void; children: ReactNode };
type Menu = { x: number; y: number; sel?: Omit<Highlight, "id">; hid?: string };

const elementOf = (n: Node) => (n instanceof Element ? n : n.parentElement);
const newId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

/** Passage on the left, questions on the right, a draggable splitter, and highlight/note support. */
export default function ReadingView({ part, highlights, setHighlights, children }: Props) {
  const [left, setLeft] = useState(50);
  const [menu, setMenu] = useState<Menu | null>(null);
  const [showNotes, setShowNotes] = useState(true);
  const box = useRef<HTMLDivElement>(null);
  const passage = part.passage!;
  const key = (label: string) => `${part.number}-${label}`; // paragraph labels repeat across passages

  useEffect(() => {
    const close = (e: globalThis.MouseEvent) => !(e.target as Element).closest(".ctxmenu") && setMenu(null);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  function onMouseUp(e: MouseEvent) {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed) return;
    const range = sel.getRangeAt(0);
    const para = elementOf(range.startContainer)?.closest<HTMLElement>("[data-p]");
    if (!para || para !== elementOf(range.endContainer)?.closest("[data-p]")) return; // one paragraph at a time
    const offset = (node: Node, off: number) => {
      const r = document.createRange();
      r.selectNodeContents(para);
      r.setEnd(node, off);
      return r.toString().length;
    };
    const start = offset(range.startContainer, range.startOffset);
    const end = offset(range.endContainer, range.endOffset);
    if (end > start) setMenu({ x: e.clientX, y: e.clientY, sel: { p: para.dataset.p!, start, end } });
  }

  function add(note?: string) {
    if (menu?.sel) setHighlights([...highlights, { id: newId(), ...menu.sel, ...(note ? { note } : {}) }]);
    window.getSelection()?.removeAllRanges();
    setMenu(null);
  }

  const textOf = (h: Highlight) => {
    const p = passage.paragraphs.find((p) => key(p.label) === h.p);
    return p?.text.slice(h.start, h.end) ?? "";
  };
  const notes = highlights.filter((h) => h.note && h.p.startsWith(`${part.number}-`));

  return (
    <div
      className="split"
      ref={box}
      style={{ gridTemplateColumns: `${left}% 8px 1fr${showNotes && notes.length ? " 220px" : ""}` }}
    >
      <article className="passage" onMouseUp={onMouseUp}>
        <h2>{passage.title}</h2>
        {passage.paragraphs.map((p) => (
          <div className="para" key={p.label}>
            <b>{p.label}</b>
            <Paragraph
              pkey={key(p.label)}
              text={p.text}
              highlights={highlights}
              onMark={(hid, e) => setMenu({ x: e.clientX, y: e.clientY, hid })}
            />
          </div>
        ))}
        {Object.keys(passage.glossary).length > 0 && (
          <p className="glossary">
            {Object.entries(passage.glossary).map(([term, def]) => (
              <span key={term}>
                <sup>*</sup>
                <b>{term}</b>: {def}{" "}
              </span>
            ))}
          </p>
        )}
        {notes.length > 0 && (
          <button className="link" onClick={() => setShowNotes(!showNotes)}>
            {showNotes ? "Hide notes" : `Show notes (${notes.length})`}
          </button>
        )}
      </article>

      <div
        className="splitter"
        role="separator"
        aria-orientation="vertical"
        onPointerDown={(e) => e.currentTarget.setPointerCapture(e.pointerId)}
        onPointerMove={(e) => {
          if (!e.currentTarget.hasPointerCapture(e.pointerId)) return;
          const r = box.current!.getBoundingClientRect();
          setLeft(Math.min(80, Math.max(20, ((e.clientX - r.left) / r.width) * 100)));
        }}
      />

      <div className="questions">{children}</div>

      {showNotes && notes.length > 0 && (
        <aside className="notes">
          <h3>Notes</h3>
          {notes.map((h) => (
            <div key={h.id} className="note">
              <q>{textOf(h)}</q>
              <p>{h.note}</p>
              <button className="link" onClick={() => setHighlights(highlights.filter((x) => x.id !== h.id))}>
                Delete
              </button>
            </div>
          ))}
        </aside>
      )}

      {menu && (
        <div className="ctxmenu" style={{ left: menu.x, top: menu.y }}>
          {menu.sel && (
            <>
              <button onClick={() => add()}>Highlight</button>
              <button onClick={() => add(window.prompt("Note") || undefined)}>Note</button>
            </>
          )}
          {menu.hid && (
            <button
              onClick={() => {
                setHighlights(highlights.filter((h) => h.id !== menu.hid));
                setMenu(null);
              }}
            >
              Clear
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function Paragraph(props: {
  pkey: string;
  text: string;
  highlights: Highlight[];
  onMark: (hid: string, e: MouseEvent) => void;
}) {
  const { pkey, text } = props;
  const hs = props.highlights.filter((h) => h.p === pkey);
  // Cut the text at every highlight boundary, then mark each piece that a highlight covers.
  const cuts = [...new Set([0, text.length, ...hs.flatMap((h) => [h.start, h.end])])]
    .filter((c) => c >= 0 && c <= text.length)
    .sort((a, b) => a - b);
  return (
    <p data-p={pkey}>
      {cuts.slice(0, -1).map((start, i) => {
        const end = cuts[i + 1];
        const h = hs.findLast((h) => h.start <= start && h.end >= end);
        const piece = text.slice(start, end);
        return h ? (
          <mark
            key={start}
            className={h.note ? "noted" : undefined}
            title={h.note}
            onClick={(e) => window.getSelection()?.isCollapsed && props.onMark(h.id, e)}
          >
            {piece}
          </mark>
        ) : (
          <Fragment key={start}>{piece}</Fragment>
        );
      })}
    </p>
  );
}
