import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { Page } from "../components/Layout";
import { ErrorBox, Loading } from "../components/States";
import { TimetableGrid } from "../components/TimetableGrid";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatDateTime, humanize } from "../lib/format";
import { useConfig, useStoredState } from "../lib/hooks";
import { entityOptions, entriesFor, type GridView } from "../lib/timetable";
import type { BlockedSlot, RunResult } from "../lib/types";

const VIEWS: GridView[] = ["group", "faculty", "room"];

/** Opens the server-rendered PDF in a new tab, where it can be printed. */
function openPdf(url: string) {
  window.open(url, "_blank", "noopener");
}

export function Timetable() {
  const { isStaff, user } = useAuth();
  const runs = useQuery({ queryKey: ["runs"], queryFn: () => api.runs() });
  // Faculty cannot read the constraint config; runs carry their blocked slots.
  const config = useConfig(isStaff);
  const [stored, setSelected] = useStoredState("selectedRun", "");
  const [params, setParams] = useSearchParams();
  const selected = params.get("run") ?? stored;
  const title = isStaff ? "Timetable" : "My timetable";

  const succeeded = (runs.data ?? []).filter((run) => run.status === "succeeded");
  const runId = succeeded.find((run) => run.id === selected)?.id ?? succeeded[0]?.id;

  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.run(runId!),
    enabled: Boolean(runId),
  });

  if (runs.error || config.error) {
    return (
      <Page title={title}>
        <ErrorBox error={runs.error ?? config.error} />
      </Page>
    );
  }
  if (runs.isLoading || (isStaff && config.isLoading)) {
    return (
      <Page title={title}>
        <Loading />
      </Page>
    );
  }

  if (!runId) {
    return (
      <Page title={title}>
        <div className="card empty">
          {isStaff ? (
            <>
              No timetable yet. <Link to="/generate">Generate one</Link> first.
            </>
          ) : (
            "No timetable has been published yet."
          )}
        </div>
      </Page>
    );
  }

  const result = run.data?.result;
  const blocked = result?.calendar.blocked_slots ?? config.data?.config.calendar.blocked_slots ?? [];

  return (
    <Page title={title}>
      {!isStaff && user.faculty && (
        <p className="muted no-print">
          Signed in as {user.faculty.name} ({user.faculty.designation_label}, {user.faculty.employee_id}).
        </p>
      )}
      <div className="card">
        <div className="toolbar">
          <label>
            {isStaff ? "Run" : "Version"}
            <select
              value={runId}
              onChange={(event) => {
                setSelected(event.target.value);
                setParams({});
              }}
            >
              {succeeded.map((item) => (
                <option key={item.id} value={item.id}>
                  {formatDateTime(item.started_at)}
                  {isStaff ? ` · ${item.total_weighted_penalty}` : ""}
                </option>
              ))}
            </select>
          </label>
          {run.error ? null : result ? (
            <GridSection key={runId} runId={runId} detail={result} blocked={blocked} facultyOnly={!isStaff} />
          ) : (
            <Loading />
          )}
        </div>
        {run.error && <ErrorBox error={run.error} />}
      </div>
    </Page>
  );
}

function GridSection({
  runId,
  detail,
  blocked,
  facultyOnly,
}: {
  runId: string;
  detail: RunResult;
  blocked: BlockedSlot[];
  facultyOnly: boolean;
}) {
  const [storedView, setView] = useStoredState<GridView>("ttBy", "group");
  const [storedEntity, setEntity] = useStoredState("ttEntity", "");
  const options = useMemo(() => entityOptions(detail.entries, detail.group_parents), [detail]);

  const view: GridView = facultyOnly ? "faculty" : VIEWS.includes(storedView) ? storedView : "group";
  const list = options[view];
  const values = list.map((option) => option.value);
  const entity = values.includes(storedEntity) ? storedEntity : (values[0] ?? "");
  const current = list.find((option) => option.value === entity);
  const shown = entity ? entriesFor(detail.entries, view, entity, detail.group_parents) : [];
  const periods = shown.reduce((sum, entry) => sum + entry.end_period - entry.start_period + 1, 0);
  const days = new Set(shown.map((entry) => entry.day)).size;

  const step = (delta: number) => {
    const index = values.indexOf(entity);
    setEntity(values[(index + delta + values.length) % values.length]);
  };

  return (
    <>
      {!facultyOnly && (
        <>
          <label>
            View by
            <select
              value={view}
              onChange={(event) => {
                setView(event.target.value as GridView);
                setEntity("");
              }}
            >
              {VIEWS.map((item) => (
                <option key={item} value={item}>
                  {humanize(item)}
                </option>
              ))}
            </select>
          </label>
          <select aria-label={humanize(view)} value={entity} onChange={(event) => setEntity(event.target.value)}>
            {list.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
          <button className="button small" onClick={() => step(-1)} aria-label="Previous">
            ‹
          </button>
          <button className="button small" onClick={() => step(1)} aria-label="Next">
            ›
          </button>
        </>
      )}
      <span className="spacer" />
      <span className="muted">
        {shown.length} sessions · {periods} periods{view === "faculty" ? ` over ${days} days` : ""}
      </span>
      <button
        className="button primary"
        disabled={!entity}
        onClick={() => openPdf(api.pdfUrl(runId, view, facultyOnly ? [] : [entity]))}
        title="Open a printable PDF of this timetable"
      >
        Print / PDF
      </button>
      {!facultyOnly && (
        <button
          className="button"
          onClick={() => openPdf(api.pdfUrl(runId, view))}
          title={`One page per ${view}`}
        >
          PDF of all {view === "faculty" ? "faculty" : `${view}s`}
        </button>
      )}

      <div style={{ flexBasis: "100%" }}>
        <h2>{current?.label ?? entity}</h2>
        {list.length ? (
          <TimetableGrid entries={shown} calendar={detail.calendar} view={view} blocked={blocked} />
        ) : (
          <div className="empty">{facultyOnly ? "You have no sessions in this timetable." : "Nothing to show."}</div>
        )}
        <div className="legend">
          <span>Hatched: blocked slot</span>
          <span>Striped column: lunch</span>
          {view === "group" && <span>Group view includes parent-group and batch sessions.</span>}
        </div>
      </div>
    </>
  );
}
