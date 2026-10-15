import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { api, type AttemptSummary, type User } from "../api";
import BandScale from "../components/BandScale";

type Props = { user: User; sections: { path: string; label: string; blurb: string; ready: boolean }[] };

export default function Home({ user, sections }: Props) {
  const attempts = useQuery({ queryKey: ["attempts"], queryFn: () => api<AttemptSummary[]>("/attempts") });
  const latest = attempts.data?.find((a) => a.mode !== "practice" && a.status === "completed" && a.skills[0] === "reading");

  return (
    <>
      <section className="hero">
        <h1>Hello, {user.display_name}</h1>
        <p className="lead">
          {latest
            ? `Your latest Reading mock: band ${latest.bands[0]?.toFixed(1)}. Your target is ${user.target_band.toFixed(1)}.`
            : `Your target is band ${user.target_band.toFixed(1)}. Take a Reading mock to see where you stand.`}
        </p>
        <BandScale band={latest?.bands[0]} target={user.target_band} />
      </section>

      <ul className="modes">
        {sections.map((s) => (
          <li key={s.path} className={s.ready ? undefined : "soon"}>
            <div>
              <h2>{s.label}</h2>
              <p>{s.blurb}</p>
            </div>
            {s.ready ? (
              <Link className="button" to={s.path}>
                Open
              </Link>
            ) : (
              <span className="tag">Coming soon</span>
            )}
          </li>
        ))}
      </ul>
      <p className="disclaimer">Bands shown in this app are AI/heuristic estimates, not official IELTS results.</p>
    </>
  );
}
