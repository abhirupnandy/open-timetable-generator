import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";

import { ErrorBox, Loading } from "../components/States";
import { api } from "../lib/api";

/** Sign-in page; on a fresh install it creates the first administrator instead. */
export function Login() {
  const queryClient = useQueryClient();
  const status = useQuery({ queryKey: ["authStatus"], queryFn: api.authStatus });
  const [username, setUsername] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [repeat, setRepeat] = useState("");
  const [error, setError] = useState("");

  const setup = status.data?.needs_setup ?? false;

  useEffect(() => {
    document.title = `${setup ? "Set up" : "Sign in"} · Timetable Generator`;
  }, [setup]);

  const submit = useMutation({
    mutationFn: () =>
      setup ? api.setup({ username, full_name: fullName, password }) : api.login(username, password),
    onSuccess: ({ user }) => {
      queryClient.setQueryData(["me"], user);
      queryClient.removeQueries({ queryKey: ["authStatus"] });
    },
    onError: (failure: Error) => setError(failure.message),
  });

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    setError("");
    if (setup && password !== repeat) {
      setError("The passwords do not match.");
      return;
    }
    submit.mutate();
  };

  return (
    <div className="login-page">
      <form className="card login-card" onSubmit={onSubmit}>
        <div className="brand login-brand">
          <span className="brand-mark" aria-hidden="true" />
          <span>Timetable Generator</span>
        </div>
        {status.error ? (
          <ErrorBox error={status.error} />
        ) : status.isLoading ? (
          <Loading />
        ) : (
          <>
            <h1>{setup ? "Create the administrator account" : "Sign in"}</h1>
            {setup && (
              <p className="muted small">
                No accounts exist yet. This first account can manage data, generate timetables and create accounts for
                coordinators and faculty.
              </p>
            )}
            <label className="field">
              <span>Username</span>
              <input autoFocus autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
            </label>
            {setup && (
              <label className="field">
                <span>Full name</span>
                <input autoComplete="name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
              </label>
            )}
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                autoComplete={setup ? "new-password" : "current-password"}
                minLength={setup ? 8 : undefined}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </label>
            {setup && (
              <label className="field">
                <span>Repeat password</span>
                <input type="password" autoComplete="new-password" value={repeat} onChange={(e) => setRepeat(e.target.value)} required />
              </label>
            )}
            {error && (
              <p className="field-error" role="alert">
                {error}
              </p>
            )}
            <button type="submit" className="button primary" disabled={submit.isPending}>
              {setup ? "Create account" : "Sign in"}
            </button>
            {!setup && (
              <p className="muted small">
                Faculty: your username is your employee ID. Ask the timetable coordinator if you have no password.
              </p>
            )}
          </>
        )}
      </form>
    </div>
  );
}
