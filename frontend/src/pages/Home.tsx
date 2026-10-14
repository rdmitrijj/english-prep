import { Link } from "react-router";
import type { User } from "../api";

type Props = { user: User; sections: { path: string; label: string; milestone: string }[] };

export default function Home({ user, sections }: Props) {
  return (
    <>
      <h1>Hello, {user.display_name}</h1>
      <p>Target band: {user.target_band.toFixed(1)}</p>
      <ul className="cards">
        {sections.map((s) => (
          <li key={s.path}>
            <Link to={s.path}>{s.label}</Link>
            <small>coming in {s.milestone}</small>
          </li>
        ))}
      </ul>
      <p className="disclaimer">Bands shown in this app are AI/heuristic estimates, not official IELTS results.</p>
    </>
  );
}
