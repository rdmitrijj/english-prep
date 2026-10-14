import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { NavLink, Route, Routes } from "react-router";
import { api, ApiError, type User } from "./api";
import Home from "./pages/Home";
import Login from "./pages/Login";

const SECTIONS = [
  { path: "/mock", label: "Mock exam", milestone: "M3 / M8" },
  { path: "/practice", label: "Practice", milestone: "M4" },
  { path: "/trainer", label: "Weakness Trainer", milestone: "M7" },
  { path: "/dashboard", label: "Dashboard", milestone: "M7" },
];

export default function App() {
  const qc = useQueryClient();
  const me = useQuery({ queryKey: ["me"], queryFn: () => api<User>("/auth/me") });
  const logout = useMutation({
    mutationFn: () => api("/auth/logout", { method: "POST" }),
    onSuccess: () => qc.setQueryData(["me"], null),
  });

  if (me.isPending) return <p className="center">Loading…</p>;
  if (me.error && !(me.error instanceof ApiError && me.error.status === 401)) {
    return <p className="center">Server unavailable: {me.error.message}</p>;
  }
  if (!me.data) return <Login />;

  return (
    <>
      <header className="topbar">
        <strong>English-prep</strong>
        <nav>
          <NavLink to="/">Home</NavLink>
          {SECTIONS.map((s) => (
            <NavLink key={s.path} to={s.path}>
              {s.label}
            </NavLink>
          ))}
        </nav>
        <span>
          {me.data.display_name} · <button onClick={() => logout.mutate()}>Log out</button>
        </span>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<Home user={me.data} sections={SECTIONS} />} />
          {SECTIONS.map((s) => (
            <Route key={s.path} path={s.path} element={<p>{s.label} arrives in {s.milestone}.</p>} />
          ))}
        </Routes>
      </main>
    </>
  );
}
