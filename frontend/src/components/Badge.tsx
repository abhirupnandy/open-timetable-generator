const KINDS: Record<string, string> = {
  succeeded: "ok",
  OPTIMAL: "ok",
  ok: "ok",
  on: "ok",
  FEASIBLE: "info",
  running: "info",
  infeasible: "warn",
  failed: "bad",
  mismatch: "bad",
};

export function Badge({ children, kind }: { children: string; kind?: string }) {
  return <span className={`badge ${kind ?? KINDS[children] ?? ""}`}>{children}</span>;
}
