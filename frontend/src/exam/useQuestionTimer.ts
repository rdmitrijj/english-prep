import { useEffect, useRef } from "react";

const IDLE_MS = 45_000;
const ACTIVITY = ["keydown", "pointerdown", "pointermove", "wheel", "scroll"] as const;

/** Adds elapsed time to the current question once a second (PLAN §4.3). Paused while the tab is hidden,
 * or after 45 s with no key, pointer, scroll or wheel event, so a coffee break doesn't count as reading. */
export function useQuestionTimer(currentId: () => number, add: (qid: number, ms: number) => void) {
  const lastActivity = useRef(Date.now());
  useEffect(() => {
    const active = () => {
      lastActivity.current = Date.now();
    };
    ACTIVITY.forEach((e) => window.addEventListener(e, active, { capture: true, passive: true }));
    let last = performance.now();
    const tick = setInterval(() => {
      const now = performance.now();
      const elapsed = Math.min(now - last, 2000); // a throttled background tab must not dump a big chunk
      last = now;
      if (!document.hidden && Date.now() - lastActivity.current < IDLE_MS) add(currentId(), Math.round(elapsed));
    }, 1000);
    return () => {
      clearInterval(tick);
      ACTIVITY.forEach((e) => window.removeEventListener(e, active, { capture: true }));
    };
  }, [currentId, add]);
}
