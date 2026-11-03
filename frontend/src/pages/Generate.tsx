import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";

import { Page } from "../components/Layout";
import { RunPanel } from "../components/RunView";
import { RunTable } from "../components/RunTable";
import { ErrorBox, Loading } from "../components/States";
import { useToast } from "../components/Toasts";
import { api } from "../lib/api";
import { useConfig, useStoredState } from "../lib/hooks";
import type { TimetableConfig } from "../lib/types";

export function Generate() {
  const config = useConfig();
  const queryClient = useQueryClient();
  const toast = useToast();
  const [selected, setSelected] = useStoredState("selectedRun", "");
  const [storedLimit, setStoredLimit] = useStoredState("timeLimit", "");
  // What the user is typing; may be temporarily empty.
  const [draftLimit, setDraftLimit] = useState<string | null>(null);
  const summary = useQuery({ queryKey: ["data-summary"], queryFn: api.dataSummary });

  const runs = useQuery({
    queryKey: ["runs"],
    queryFn: () => api.runs(),
    refetchInterval: (query) => (query.state.data?.some((run) => run.status === "running") ? 2000 : false),
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
  const assignments = summary.data?.teaching_assignments;

  return (
    <Page title="Generate timetable">
      {assignments === 0 && (
        <div className="card warn-card">
          There are no teaching assignments yet. <Link to="/import">Import a data workbook</Link> first.
        </div>
      )}
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
              required
              value={limit}
              onChange={(event) => {
                setDraftLimit(event.target.value);
                if (event.target.value) setStoredLimit(event.target.value);
              }}
            />
          </label>
          <button type="submit" className="button primary" disabled={start.isPending || running}>
            {running ? "Solver running…" : "Generate timetable"}
          </button>
          <span className="muted">
            {settings.solver.workers} workers · <Link to="/constraints">constraints</Link>
            {assignments ? ` · ${assignments} assignments` : ""}
          </span>
        </form>
        <details style={{ marginTop: 14 }}>
          <summary className="muted">Active constraints</summary>
          <ConstraintChips config={settings} />
        </details>
      </div>

      {shownId && <RunPanel key={shownId} runId={shownId} />}

      <div className="card">
        <div className="card-head">
          <h2>Recent runs</h2>
          <Link to="/runs">All runs and failures →</Link>
        </div>
        <RunTable runs={(runs.data ?? []).slice(0, 5)} shownId={shownId} onShow={setSelected} />
      </div>
    </Page>
  );
}

function ConstraintChips({ config }: { config: TimetableConfig }) {
  const chips: { key: string; label: string; off: boolean }[] = [
    ...Object.entries(config.hard).map(([key, item]) => ({ key, label: item.enabled ? "hard" : "off", off: !item.enabled })),
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
