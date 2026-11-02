import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { Link } from "react-router-dom";

import { ApiError, api } from "../lib/api";
import { formatDateTime, humanize } from "../lib/format";
import type { RunDetail } from "../lib/types";
import { Badge } from "./Badge";
import { ErrorBox, Loading } from "./States";

const STAGES = ["queued", "loading", "solving", "validating", "exporting", "done"];

/** Live view of one run: progress while running, then results or failure details. */
export function RunPanel({ runId }: { runId: string }) {
  const queryClient = useQueryClient();
  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.run(runId),
    refetchInterval: (query) => (query.state.data?.status === "running" ? 1000 : false),
    retry: (count, error) => !(error instanceof ApiError && error.status === 404) && count < 2,
  });

  const status = run.data?.status;
  useEffect(() => {
    if (status && status !== "running") queryClient.invalidateQueries({ queryKey: ["runs"] });
  }, [status, queryClient]);

  if (run.error) {
    if (run.error instanceof ApiError && run.error.status === 404) {
      return <div className="card empty">Run {runId} no longer exists.</div>;
    }
    return <ErrorBox error={run.error} />;
  }
  if (!run.data) return <Loading />;

  const detail = run.data;
  if (detail.status === "running") return <RunProgress run={detail} />;
  if (detail.status === "failed") return <RunFailure run={detail} />;
  return <RunResultView run={detail} />;
}

function RunProgress({ run }: { run: RunDetail }) {
  const percent = Math.min(100, (run.elapsed_seconds / run.max_time_seconds) * 100);
  const current = STAGES.indexOf(run.stage);
  return (
    <div className="card">
      <div className="card-head">
        <h2>Generating timetable{run.session_count ? ` for ${run.session_count} sessions` : ""}…</h2>
        <Badge>running</Badge>
      </div>
      <ol className="stages">
        {STAGES.slice(1, -1).map((stage, index) => (
          <li key={stage} className={index + 1 < current ? "done" : index + 1 === current ? "current" : ""}>
            {humanize(stage)}
          </li>
        ))}
      </ol>
      <p className="muted">
        {run.elapsed_seconds.toFixed(0)}s elapsed, time limit {run.max_time_seconds}s. CP-SAT keeps improving the
        timetable until the limit.
      </p>
      <div className="progress" role="progressbar" aria-valuenow={Math.round(percent)} aria-valuemin={0} aria-valuemax={100}>
        <div style={{ width: `${percent}%` }} />
      </div>
      <RunLog log={run.log} />
    </div>
  );
}

function RunLog({ log, open }: { log: string; open?: boolean }) {
  if (!log) return null;
  return (
    <details className="log" open={open}>
      <summary>Run log</summary>
      <pre className="log-text">{log}</pre>
    </details>
  );
}

function RunFailure({ run }: { run: RunDetail }) {
  return (
    <>
      <div className="card error-card">
        <div className="card-head">
          <h2>Run {run.id} failed</h2>
          <Badge>failed</Badge>
        </div>
        <p className="muted">
          Started {formatDateTime(run.started_at)} · failed during <b>{humanize(run.stage)}</b> after{" "}
          {run.elapsed_seconds.toFixed(1)}s
        </p>
        <p className="failure-reason">{run.error}</p>
        {run.error_detail && (
          <details open>
            <summary>Details</summary>
            <pre className="error">{run.error_detail}</pre>
          </details>
        )}
        <RunLog log={run.log} open />
        <div className="toolbar" style={{ marginTop: 12 }}>
          <Link className="button" to="/import">
            Import data
          </Link>
          <Link className="button" to="/constraints">
            Edit constraints
          </Link>
          <Link className="button primary" to="/generate">
            Try again
          </Link>
        </div>
      </div>
      {run.result && <RunResultView run={run} />}
    </>
  );
}

export function RunResultView({ run }: { run: RunDetail }) {
  const result = run.result!;
  const report = result.score_report;
  const validation = result.validation;

  return (
    <>
      <div className="card">
        <div className="card-head">
          <h2>Run {run.id}</h2>
          <div>
            <Badge>{report.status}</Badge>{" "}
            {validation.is_valid ? (
              <Badge kind="ok">All hard constraints pass</Badge>
            ) : (
              <Badge kind="bad">{`${validation.conflicts} conflicts, ${validation.violations.length} violations`}</Badge>
            )}
          </div>
        </div>
        <p className="muted">
          {formatDateTime(run.started_at)} · objective {report.objective_value ?? "—"} · best bound{" "}
          {report.best_bound ?? "—"} · solve {report.wall_time_seconds}s · build {report.build_time_seconds}s ·{" "}
          {report.model_stats.candidates} candidates, {report.model_stats.variables} variables
        </p>
        <div className="tiles">
          {Object.entries(report.metrics).map(([key, value]) => (
            <div key={key} className="tile">
              <div className="tile-label">{humanize(key)}</div>
              <div className="tile-value">{value}</div>
            </div>
          ))}
        </div>
        <div className="toolbar">
          <Link className="button primary" to={`/timetable?run=${run.id}`}>
            View timetable
          </Link>
          {run.files.map((file) => (
            <a key={file.name} className="button" href={api.fileUrl(run.id, file.name)} download>
              {file.label}
            </a>
          ))}
        </div>
        {result.diagnostics.length > 0 && (
          <ul className="muted">
            {result.diagnostics.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )}
        {validation.violations.length > 0 && (
          <ul>
            {validation.violations.map((item, index) => (
              <li key={index}>
                <b>{item.reason}</b>: {item.message}
              </li>
            ))}
          </ul>
        )}
        <RunLog log={run.log} />
      </div>

      <div className="card">
        <h2>Score report</h2>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Constraint</th>
                <th>Mode</th>
                <th className="num">Weight</th>
                <th className="num">Raw</th>
                <th className="num">Weighted</th>
                <th className="num">Solver</th>
                <th>Check</th>
              </tr>
            </thead>
            <tbody>
              {report.constraints.map((row) => (
                <tr key={row.key} className={`${row.mismatch ? "mismatch" : ""} ${row.mode === "off" ? "off" : ""}`}>
                  <td>
                    {row.key} {row.constraint_id && <Badge>{row.constraint_id}</Badge>}
                  </td>
                  <td>{row.mode}</td>
                  <td className="num">{row.weight}</td>
                  <td className="num">{row.raw_penalty}</td>
                  <td className="num">{row.weighted_penalty}</td>
                  <td className="num">{row.solver_penalty ?? "—"}</td>
                  <td>
                    {row.mismatch ? <Badge>mismatch</Badge> : row.solver_penalty !== null ? <Badge>ok</Badge> : null}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={4}>
                  <b>Total weighted penalty</b>
                </td>
                <td className="num">
                  <b>{report.total_weighted_penalty}</b>
                </td>
                <td colSpan={2} />
              </tr>
            </tfoot>
          </table>
        </div>
        <p className="muted">
          “Raw” is computed independently from the finished timetable; “Solver” is the CP-SAT penalty variable. They
          must match.
        </p>
      </div>
    </>
  );
}
