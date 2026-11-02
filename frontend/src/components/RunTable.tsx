import { formatDateTime, humanize } from "../lib/format";
import type { RunSummary } from "../lib/types";
import { Badge } from "./Badge";

interface RunTableProps {
  runs: RunSummary[];
  shownId?: string;
  onShow: (id: string) => void;
  onDelete?: (run: RunSummary) => void;
}

export function RunTable({ runs, shownId, onShow, onDelete }: RunTableProps) {
  if (!runs.length) return <p className="muted">No runs yet.</p>;
  return (
    <div className="table-wrap">
      <table className="data">
        <thead>
          <tr>
            <th>Started</th>
            <th>Status</th>
            <th>Solver</th>
            <th className="num">Time (s)</th>
            <th className="num">Penalty</th>
            <th>Reason / stage</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id} className={run.id === shownId ? "selected" : ""}>
              <td>{formatDateTime(run.started_at)}</td>
              <td>
                <Badge>{run.status}</Badge>
              </td>
              <td>{run.solver_status && <Badge>{run.solver_status}</Badge>}</td>
              <td className="num">{run.elapsed_seconds.toFixed(1)}</td>
              <td className="num">{run.total_weighted_penalty ?? ""}</td>
              <td className="reason">
                {run.status === "failed" ? (
                  <span className="bad-text" title={run.error ?? ""}>
                    {run.error}
                  </span>
                ) : run.status === "running" ? (
                  humanize(run.stage)
                ) : (
                  ""
                )}
              </td>
              <td className="actions">
                {run.id === shownId ? (
                  <span className="muted">shown</span>
                ) : (
                  <button className="button small" onClick={() => onShow(run.id)}>
                    Show
                  </button>
                )}{" "}
                {onDelete && run.status !== "running" && (
                  <button className="button small danger" onClick={() => onDelete(run)} aria-label={`Delete run ${run.id}`}>
                    Delete
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
