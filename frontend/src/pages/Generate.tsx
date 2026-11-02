import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { Badge } from "../components/Badge";
import { Page } from "../components/Layout";
import { ErrorBox, Loading } from "../components/States";
import { useToast } from "../components/Toasts";
import { ApiError, api } from "../lib/api";
import { formatDateTime, humanize } from "../lib/format";
import { useConfig, useStoredState } from "../lib/hooks";
import type { RunDetail, RunSummary, TimetableConfig } from "../lib/types";

export function Generate() {
  const config = useConfig();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [selected, setSelected] = useStoredState("selectedRun", "");
  const [storedLimit, setStoredLimit] = useStoredState("timeLimit", "");
  // What the user is typing; may be temporarily empty.
  const [draftLimit, setDraftLimit] = useState<string | null>(null);

  const runs = useQuery({
    queryKey: ["runs"],
    queryFn: api.runs,
    refetchInterval: (query) =>
      query.state.data?.some((run) => run.status === "running") ? 2000 : false,
  });

  const shownId = runs.data?.some((run) => run.id === selected) ? selected : runs.data?.[0]?.id;

  const start = useMutation({
    mutationFn: (seconds: number) => api.startRun(seconds),
    onSuccess: (run) => {
      setSelected(run.id);
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      toast("Solver started");
    },
    onError: (err: Error) => toast(err.message, "bad"),
  });

  if (config.error) return <Page title="Generate timetable"><ErrorBox error={config.error} /></Page>;
  if (!config.data) return <Page title="Generate timetable"><Loading /></Page>;

  const settings = config.data.config;
  const limit = draftLimit ?? (storedLimit || String(settings.solver.max_time_seconds));
  const running = runs.data?.some((run) => run.status === "running") ?? false;

  return (
    <Page title="Generate timetable">
      <div className="card">
        <form
          className="run-bar"
          onSubmit={(event) => {
            event.preventDefault();
            start.mutate(Number(limit));
          }}
        >
          <label className="field">
            <span>Time limit (seconds)</span>
            <input
              type="number"
              min={1}
              max={3600}
              value={limit}
              required
              onChange={(event) => {
                setDraftLimit(event.target.value);
                if (event.target.value) setStoredLimit(event.target.value);
              }}
            />
          </label>
          <button type="submit" className="button primary" disabled={start.isPending || running}>
            {running ? "Solver running…" : "Run solver"}
          </button>
          <span className="muted">
            {settings.solver.workers} workers · constraints from <span className="mono">config/timetable.toml</span>
          </span>
        </form>
        <details style={{ marginTop: 14 }}>
          <summary className="muted">Active constraints</summary>
          <ConstraintChips config={settings} />
        </details>
      </div>

      {shownId && <RunPanel key={shownId} runId={shownId} />}

      <div className="card">
        <h2>Runs</h2>
        <RunList runs={runs.data ?? []} shownId={shownId} onShow={setSelected} />
      </div>
    </Page>
  );
}

function ConstraintChips({ config }: { config: TimetableConfig }) {
  const chips: { key: string; label: string; off: boolean }[] = [
    ...Object.entries(config.hard).map(([key, item]) => ({
      key,
      label: item.enabled ? "hard" : "off",
      off: !item.enabled,
    })),
    ...Object.entries(config.constraints).map(([key, item]) => ({
      key,
      label: item.mode === "soft" ? `soft ×${item.weight}` : item.mode,
      off: item.mode === "off",
    })),
    ...Object.entries(config.soft).map(([key, item]) => ({
      key,
      label: item.enabled ? `×${item.weight}` : "off",
      off: !item.enabled,
    })),
  ];
  return (
    <div className="chips" style={{ marginTop: 10 }}>
      {chips.map((chip) => (
        <span key={chip.key} className={`chip ${chip.off ? "off" : ""}`}>
          <b>{chip.key}</b> {chip.label}
        </span>
      ))}
    </div>
  );
}

function RunList({ runs, shownId, onShow }: { runs: RunSummary[]; shownId?: string; onShow: (id: string) => void }) {
  if (!runs.length) {
    return <p className="muted">No runs yet. Runs are kept in memory until the server restarts.</p>;
  }
  return (
    <div className="table-wrap">
      <table className="data">
        <thead>
          <tr>
            <th>Started</th>
            <th>Status</th>
            <th>Solver</th>
            <th className="num">Time (s)</th>
            <th className="num">Weighted penalty</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <tr key={run.id}>
              <td>{formatDateTime(run.started_at)}</td>
              <td>
                <Badge>{run.status}</Badge>
              </td>
              <td>{run.solver_status && <Badge>{run.solver_status}</Badge>}</td>
              <td className="num">{run.elapsed_seconds}</td>
              <td className="num">{run.total_weighted_penalty ?? ""}</td>
              <td className="actions">
                {run.id === shownId ? (
                  <span className="muted">shown</span>
                ) : (
                  <button className="button small" onClick={() => onShow(run.id)}>
                    Show
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

function RunPanel({ runId }: { runId: string }) {
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
    if (run.error instanceof ApiError && run.error.status === 404) return null;
    return <ErrorBox error={run.error} />;
  }
  if (!run.data) return <Loading />;

  const detail = run.data;

  if (detail.status === "running") {
    const percent = Math.min(100, (detail.elapsed_seconds / detail.max_time_seconds) * 100);
    return (
      <div className="card">
        <div className="card-head">
          <h2>Solving {detail.session_count} sessions…</h2>
          <Badge>running</Badge>
        </div>
        <p className="muted">
          {detail.elapsed_seconds.toFixed(0)}s of up to {detail.max_time_seconds}s. CP-SAT keeps improving until the
          time limit.
        </p>
        <div className="progress" role="progressbar" aria-valuenow={Math.round(percent)} aria-valuemin={0} aria-valuemax={100}>
          <div style={{ width: `${percent}%` }} />
        </div>
      </div>
    );
  }

  if (detail.status !== "succeeded" || !detail.result) {
    return (
      <div className="card">
        <div className="card-head">
          <h2>Run {detail.id}</h2>
          <Badge>{detail.status}</Badge>
        </div>
        <pre className="error">{detail.error}</pre>
      </div>
    );
  }

  return <RunResultView run={detail} />;
}

function RunResultView({ run }: { run: RunDetail }) {
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
          Objective {report.objective_value ?? "—"} · best bound {report.best_bound ?? "—"} · solve{" "}
          {report.wall_time_seconds}s · build {report.build_time_seconds}s · {report.model_stats.candidates} candidates,{" "}
          {report.model_stats.variables} variables
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
          <Link className="button primary" to="/timetable">
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
