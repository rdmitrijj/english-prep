import { type ReactNode, useRef } from "react";
import type { Highlight, Part } from "../api";
import { Paragraph } from "../exam/ReadingView";

type Props = {
  part: Part;
  evidence: { qid: number; paragraph: string; quote: string }[]; // paragraph = transcript line index
  showTranscript: boolean;
  setShowTranscript: (v: boolean) => void;
  children: ReactNode;
};

const name = (speaker: string) => speaker[0].toUpperCase() + speaker.slice(1);

/** Practice Listening: a normal player (pause, replay, seek) and a transcript you can reveal,
 * with the evidence for checked questions marked in it. */
export default function ListeningPracticeView({ part, evidence, showTranscript, setShowTranscript, children }: Props) {
  const audio = useRef<HTMLAudioElement>(null);
  const playFrom = (ms: number) => {
    audio.current!.currentTime = ms / 1000;
    audio.current!.play();
  };
  const marks = (i: number, text: string): Highlight[] =>
    evidence.flatMap((e) => {
      const start = e.paragraph === String(i) ? text.indexOf(e.quote) : -1;
      return start < 0 ? [] : [{ id: `ev${e.qid}`, p: `line-${i}`, start, end: start + e.quote.length, ev: e.qid }];
    });

  return (
    <div className="split" style={{ gridTemplateColumns: "minmax(300px, 42%) 8px 1fr" }}>
      <article className="passage listen">
        <h2>Recording</h2>
        <audio ref={audio} controls preload="auto" src={part.audio!.url} />
        <p>
          <button className="link" onClick={() => setShowTranscript(!showTranscript)}>
            {showTranscript ? "Hide transcript" : "Show transcript"}
          </button>
        </p>
        {showTranscript &&
          part.transcript!.map((seg, i) => (
            <div key={i} className="seg">
              <button className="play" aria-label={`Play from here: ${name(seg.speaker)}`} onClick={() => playFrom(seg.start_ms)}>
                ▶
              </button>
              <div>
                <b>{name(seg.speaker)}</b>
                <Paragraph pkey={`line-${i}`} text={seg.text} highlights={marks(i, seg.text)} onMark={() => {}} />
              </div>
            </div>
          ))}
      </article>
      <div className="splitter" />
      <div className="questions">{children}</div>
    </div>
  );
}
