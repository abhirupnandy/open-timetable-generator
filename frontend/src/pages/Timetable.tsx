import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link } from "react-router-dom";

import { Page } from "../components/Layout";
import { ErrorBox, Loading } from "../components/States";
import { TimetableGrid } from "../components/TimetableGrid";
import { api } from "../lib/api";
import { formatDateTime, humanize } from "../lib/format";
import { useConfig, useStoredState } from "../lib/hooks";
import { entityOptions, entriesFor, type GridView } from "../lib/timetable";

const VIEWS: GridView[] = ["group", "faculty", "room"];

export function Timetable() {
  const runs = useQuery({ queryKey: ["runs"], queryFn: api.runs });
  const config = useConfig();
  const [selected, setSelected] = useStoredState("selectedRun", "");

  const succeeded = (runs.data ?? []).filter((run) => run.status === "succeeded");
  const runId = succeeded.find((run) => run.id === selected)?.id ?? succeeded[0]?.id;

  const run = useQuery({
    queryKey: ["run", runId],
    queryFn: () => api.run(runId!),
    enabled: Boolean(runId),
  });

  const printButton = (
    <button className="button" onClick={() => window.print()}>
      Print
    </button>
  );

  if (runs.error || config.error) {
    return <Page title="Timetable"><ErrorBox error={runs.error ?? config.error} /></Page>;
  }
  if (runs.isLoading || config.isLoading) return <Page title="Timetable"><Loading /></Page>;

  if (!runId) {
    return (
      <Page title="Timetable">
        <div className="card empty">
          No timetable yet. <Link to="/generate">Generate one</Link> first.
        </div>
      </Page>
    );
  }

  return (
    <Page title="Timetable" actions={printButton}>
      <div className="card">
        <div className="toolbar">
          <label>
            Run
            <select value={runId} onChange={(event) => setSelected(event.target.value)}>
              {succeeded.map((item) => (
                <option key={item.id} value={item.id}>
                  {formatDateTime(item.started_at)} · {item.total_weighted_penalty}
                </option>
              ))}
            </select>
          </label>
          {run.error ? null : run.data?.result ? (
            <GridSection
              key={runId}
              detail={run.data.result}
              blocked={config.data?.config.calendar.blocked_slots ?? []}
            />
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
  detail,
  blocked,
}: {
  detail: NonNullable<Awaited<ReturnType<typeof api.run>>["result"]>;
  blocked: { day: string; period: number; label: string }[];
}) {
  const [view, setView] = useStoredState<GridView>("ttBy", "group");
  const [storedEntity, setEntity] = useStoredState("ttEntity", "");
  const options = useMemo(() => entityOptions(detail.entries, detail.group_parents), [detail]);

  const list = options[VIEWS.includes(view) ? view : "group"];
  const entity = list.includes(storedEntity) ? storedEntity : (list[0] ?? "");
  const shown = entriesFor(detail.entries, view, entity, detail.group_parents);
  const periods = shown.reduce((sum, entry) => sum + entry.end_period - entry.start_period + 1, 0);
  const groupName = view === "group" ? detail.entries.find((entry) => entry.group_code === entity)?.group_name : "";

  const step = (delta: number) => {
    const index = list.indexOf(entity);
    setEntity(list[(index + delta + list.length) % list.length]);
  };

  return (
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
        {list.map((item) => (
          <option key={item}>{item}</option>
        ))}
      </select>
      <button className="button small" onClick={() => step(-1)} aria-label="Previous">
        ‹
      </button>
      <button className="button small" onClick={() => step(1)} aria-label="Next">
        ›
      </button>
      <span className="spacer" />
      <span className="muted">
        {shown.length} sessions · {periods} periods
      </span>

      <div style={{ flexBasis: "100%" }}>
        <h2>{groupName ? `${entity} · ${groupName}` : entity}</h2>
        {list.length ? (
          <TimetableGrid entries={shown} calendar={detail.calendar} view={view} blocked={blocked} />
        ) : (
          <div className="empty">Nothing to show.</div>
        )}
        <div className="legend">
          <span>Hatched: blocked slot</span>
          <span>Striped column: lunch</span>
          <span>Group view includes parent-group and batch sessions.</span>
        </div>
      </div>
    </>
  );
}
