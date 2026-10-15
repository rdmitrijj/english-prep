import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { api, type User } from "../api";

export default function Login() {
  const qc = useQueryClient();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const login = useMutation({
    mutationFn: () => api<User>("/auth/login", { method: "POST", body: { email, password } }),
    onSuccess: (user) => qc.setQueryData(["me"], user),
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    login.mutate();
  }

  return (
    <form className="login" onSubmit={submit}>
      <h1 className="wordmark">English-prep</h1>
      <p className="muted">Sign in to continue your preparation.</p>
      <label>
        Email
        <input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <label>
        Password
        <input
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      {login.error && <p className="error">{login.error.message}</p>}
      <button type="submit" className="button" disabled={login.isPending}>
        {login.isPending ? "Signing in…" : "Sign in"}
      </button>
    </form>
  );
}
