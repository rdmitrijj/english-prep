import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { NavLink, Outlet, Route, Routes } from "react-router";
import { api, ApiError, type User } from "./api";
import ExamPage from "./exam/ExamShell";
import ReportPage from "./exam/ReportPage";
import Home from "./pages/Home";
import Login from "./pages/Login";
import Mock from "./pages/Mock";

const SECTIONS = [
  { path: "/mock", label: "Mock exam", blurb: "A full section under real exam conditions, timed and marked.", ready: true },
  { path: "/practice", label: "Practice", blurb: "Untimed question sets with instant feedback and the evidence in the text.", ready: false },
  { path: "/trainer", label: "Weakness trainer", blurb: "Short sessions built from the question types you miss most.", ready: false },
  { path: "/dashboard", label: "Progress", blurb: "Your bands over time, accuracy per question type, and pace.", ready: false },
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

  const layout = (
    <>
      <header className="topbar">
        <NavLink to="/" className="wordmark">
          English-prep
        </NavLink>
        <nav>
          {SECTIONS.map((s) => (
            <NavLink key={s.path} to={s.path}>
              {s.label}
            </NavLink>
          ))}
        </nav>
        <span className="who">
          {me.data.display_name}
          <button className="quiet" onClick={() => logout.mutate()}>
            Log out
          </button>
        </span>
      </header>
      <main>
        <Outlet />
      </main>
    </>
  );

  return (
    <Routes>
      {/* The exam is full-screen, like the real computer-delivered test: no app navigation. */}
      <Route path="/exam/:attemptId" element={<ExamPage user={me.data} />} />
      <Route element={layout}>
        <Route path="/" element={<Home user={me.data} sections={SECTIONS} />} />
        <Route path="/mock" element={<Mock />} />
        <Route path="/report/:attemptId" element={<ReportPage />} />
        {SECTIONS.slice(1).map((s) => (
          <Route key={s.path} path={s.path} element={<p className="lead">{s.label} is coming soon.</p>} />
        ))}
      </Route>
    </Routes>
  );
}
