import type { Dashboard, Skill } from "../api";

// Colour follows the skill, never its rank (validated: colour-blind safe as adjacent pairs; direct labels relieve contrast).
const COLOUR: Record<Skill, string> = { listening: "#eb6834", reading: "#2a78d6", writing: "#1baf7a", speaking: "#eda100" };
const W = 640;
const H = 220;
const PAD = { left: 32, right: 84, top: 12, bottom: 24 };
const day = (d: string) => new Date(d).toLocaleDateString(undefined, { day: "numeric", month: "short" });
const name = (s: string) => s[0].toUpperCase() + s.slice(1);

/** Mock bands over time, one line per section, with the target as a dashed line. */
export default function BandTrend({ bands, target }: { bands: Dashboard["bands"]; target: number }) {
  const skills = [...new Set(bands.map((b) => b.skill))];
  const lo = Math.max(0, Math.floor(Math.min(target, ...bands.map((b) => b.band)) - 0.5));
  const x = (i: number) => PAD.left + (bands.length > 1 ? (i / (bands.length - 1)) * (W - PAD.left - PAD.right) : (W - PAD.right) / 2);
  const y = (band: number) => PAD.top + ((9 - band) / (9 - lo)) * (H - PAD.top - PAD.bottom);
  const ticks = Array.from({ length: 9 - lo + 1 }, (_, i) => lo + i);

  return (
    <figure className="trend">
      <ul className="legend" aria-label="Sections">
        {skills.map((s) => (
          <li key={s}>
            <span className="swatch" style={{ background: COLOUR[s] }} /> {name(s)}
          </li>
        ))}
        <li>
          <span className="swatch dashed" /> Target {target.toFixed(1)}
        </li>
      </ul>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Mock bands over time">
        {ticks.map((t) => (
          <g key={t}>
            <line className="grid" x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} />
            <text className="tick" x={PAD.left - 8} y={y(t)} dy="0.35em" textAnchor="end">
              {t}
            </text>
          </g>
        ))}
        <line className="target" x1={PAD.left} x2={W - PAD.right} y1={y(target)} y2={y(target)} />
        {skills.map((s) => {
          const pts = bands.map((b, i) => ({ ...b, i })).filter((b) => b.skill === s);
          const last = pts.at(-1)!;
          return (
            <g key={s}>
              <polyline fill="none" stroke={COLOUR[s]} strokeWidth={2} points={pts.map((p) => `${x(p.i)},${y(p.band)}`).join(" ")} />
              {pts.map((p) => (
                <g key={p.attempt_id}>
                  <circle cx={x(p.i)} cy={y(p.band)} r={4} fill={COLOUR[s]} stroke="var(--paper)" strokeWidth={2} />
                  <circle className="hit" cx={x(p.i)} cy={y(p.band)} r={12}>
                    <title>
                      {name(s)} {p.band.toFixed(1)}, {day(p.date)}
                    </title>
                  </circle>
                </g>
              ))}
              <text className="direct" x={x(last.i) + 10} y={y(last.band)} dy="0.35em">
                {name(s)} {last.band.toFixed(1)}
              </text>
            </g>
          );
        })}
      </svg>
    </figure>
  );
}
