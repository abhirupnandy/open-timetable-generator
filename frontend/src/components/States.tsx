export function Loading() {
  return <p className="muted">Loading…</p>;
}

export function ErrorBox({ error }: { error: unknown }) {
  const message = error instanceof Error ? error.message : String(error);
  return (
    <div className="card">
      <pre className="error">{message}</pre>
    </div>
  );
}
