/** A 1–9 band ruler: the target zone in highlighter yellow, your band as a dot. */
export default function BandScale({ band, target, estimate }: { band?: number | null; target: number; estimate?: boolean }) {
  const pos = (b: number) => `${((Math.min(9, Math.max(1, b)) - 1) / 8) * 100}%`;
  const label =
    band == null ? `No band yet. Target ${target.toFixed(1)}.` : `Band ${band.toFixed(1)} of 9. Target ${target.toFixed(1)}.`;
  return (
    <div className="bandscale" role="img" aria-label={label}>
      <div className="track">
        <div className="goal" style={{ left: pos(target) }}>
          <span>target {target.toFixed(1)}</span>
        </div>
        {band != null && (
          <div className={`score${band >= target ? " met" : ""}`} style={{ left: pos(band) }}>
            <span>
              {band.toFixed(1)}
              {estimate && "*"}
            </span>
          </div>
        )}
      </div>
      <div className="ticks" aria-hidden>
        {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((b) => (
          <span key={b} style={{ left: pos(b) }}>
            {b}
          </span>
        ))}
      </div>
    </div>
  );
}
