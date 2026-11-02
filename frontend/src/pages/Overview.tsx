import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Badge } from "../components/Badge";
import { Page } from "../components/Layout";
import { ErrorBox, Loading } from "../components/States";
import { api } from "../lib/api";
import { formatDateTime, humanize } from "../lib/format";
import { useConfig } from "../lib/hooks";

export function Overview() {
  const summary = useQuery({ queryKey: ["data-summary"], queryFn: api.dataSummary });
  const runs = useQuery({ queryKey: ["runs"], queryFn: () => api.runs() });
  const config = useConfig();

  if (summary.error) return <Page title="Overview"><ErrorBox error={summary.error} /></Page>;
  if (!summary.data || !runs.data) return <Page title="Overview"><Loading /></Page>;

  const counts = summary.data;
  const hasData = (counts.teaching_assignments ?? 0) > 0;
  const latest = runs.data[0];
  const succeeded = runs.data.find((run) => run.status === "succeeded");
  const failures = runs.data.filter((run) => run.status === "failed").length;
  const softOn = config.data ? Object.values(config.data.config.soft).filter((item) => item.enabled).length : 0;

  const steps = [
    {
      done: hasData,
      title: "Import your data",
      text: hasData
        ? `${counts.teaching_assignments} assignments, ${counts.academic_groups} groups, ${counts.faculty} faculty, ${counts.rooms} rooms.`
        : "Download the Excel template, fill it in and upload it.",
      link: "/import",
      action: hasData ? "Re-import" : "Import data",
    },
    {
      done: hasData,
      title: "Review constraints",
      text: config.data ? `${softOn} soft constraints enabled. Edit weights, modes and the calendar.` : "",
      link: "/constraints",
      action: "Edit constraints",
    },
    {
      done: Boolean(succeeded),
      title: "Generate the timetable",
      text: latest
        ? `Latest run ${latest.status} ${formatDateTime(latest.started_at)}.`
        : "Run the CP-SAT solver on the imported data.",
      link: "/generate",
      action: "Generate",
    },
    {
      done: Boolean(succeeded),
      title: "View, print and download",
      text: succeeded ? `Weighted penalty ${succeeded.total_weighted_penalty}.` : "Available after a successful run.",
      link: "/timetable",
      action: "Open timetable",
    },
  ];

  return (
    <Page
      title="Overview"
      actions={
        <Link className="button primary" to={hasData ? "/generate" : "/import"}>
          {hasData ? "Generate timetable" : "Import data"}
        </Link>
      }
    >
      <ol className="checklist">
        {steps.map((step, index) => (
          <li key={step.title} className={`card ${step.done ? "done" : ""}`}>
            <span className="step-number">{step.done ? "✓" : index + 1}</span>
            <div className="checklist-body">
              <h2>{step.title}</h2>
              <p className="muted">{step.text}</p>
            </div>
            <Link className="button" to={step.link}>
              {step.action}
            </Link>
          </li>
        ))}
      </ol>

      <div className="grid-2">
        <div className="card">
          <h2>Data</h2>
          <div className="tiles compact">
            {Object.entries(counts).map(([table, count]) => (
              <div key={table} className="tile">
                <div className="tile-label">{humanize(table)}</div>
                <div className="tile-value">{count}</div>
              </div>
            ))}
          </div>
        </div>
        <div className="card">
          <h2>Runs</h2>
          {latest ? (
            <>
              <p>
                Latest: <Badge>{latest.status}</Badge> {formatDateTime(latest.started_at)}
                {latest.status === "failed" && <span className="bad-text"> — {latest.error}</span>}
              </p>
              <p>
                {runs.data.length} run(s) recorded{failures ? `, ${failures} failed` : ""}.{" "}
                <Link to={latest.status === "failed" ? `/runs/${latest.id}` : "/runs"}>View history</Link>
              </p>
            </>
          ) : (
            <p className="muted">No runs yet.</p>
          )}
        </div>
      </div>
    </Page>
  );
}
