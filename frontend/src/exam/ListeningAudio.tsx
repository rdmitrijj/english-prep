import { useCallback, useEffect, useRef, useState } from "react";
import type { Part } from "../api";

type Props = {
  parts: Part[];
  startedAt: string;
  offset: { current: number }; // server clock − client clock
  volume: number;
  onPart: (partNumber: number) => void;
  onDone: () => void;
};

/** The exam recording: plays once, no controls, no pause or seek (PLAN §2). Its position always comes from the
 * server clock, so after a refresh it resumes where the recording is now, never where you left it. */
export default function ListeningAudio({ parts, startedAt, offset, volume, onPart, onDone }: Props) {
  const audio = useRef<HTMLAudioElement>(null);
  const [blocked, setBlocked] = useState(false);
  const done = useRef(false);
  const starts = parts.reduce<number[]>((acc, p, i) => [...acc, i ? acc[i - 1] + parts[i - 1].audio!.duration_ms : 0], []);
  const total = starts.at(-1)! + parts.at(-1)!.audio!.duration_ms;

  const sync = useCallback(() => {
    const el = audio.current!;
    const elapsed = Date.now() + offset.current - Date.parse(startedAt);
    if (elapsed >= total) {
      done.current = true;
      el.pause();
      onDone();
      return;
    }
    const i = starts.findLastIndex((s) => s <= elapsed);
    const url = parts[i].audio!.url;
    if (!el.src.endsWith(url)) el.src = url;
    el.currentTime = (elapsed - starts[i]) / 1000;
    onPart(parts[i].number);
    // Browsers block sound until the page has had a click; after a refresh we ask for one.
    el.play().then(
      () => setBlocked(false),
      () => setBlocked(true),
    );
  }, [parts, starts, total, startedAt, offset, onPart, onDone]);

  useEffect(() => {
    sync();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- once on mount; later syncs come from audio events
  useEffect(() => {
    audio.current!.volume = volume;
  }, [volume]);

  return (
    <>
      <audio
        ref={audio}
        preload="auto"
        onEnded={sync}
        // No pausing in the exam (media keys, headset buttons): carry on from where the recording is now.
        onPause={(e) => !done.current && !e.currentTarget.ended && sync()}
      />
      {blocked && (
        <div className="cover">
          <p>The recording is playing. Click to continue listening.</p>
          <button className="primary" onClick={sync}>
            Continue
          </button>
        </div>
      )}
    </>
  );
}
