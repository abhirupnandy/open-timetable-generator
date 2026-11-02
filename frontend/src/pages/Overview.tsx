import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { Badge } from "../components/Badge";
import { Page } from "../components/Layout";
import { ErrorBox, Loading } from "../components/States";
import { api } from "../lib/api";
import { formatDateTime } from "../lib/format";
import { useRefs } from "../lib/hooks";
import { RESOURCE_KEYS, RESOURCES } from "../lib/resources";

export function Overview() {
  const { refs, isLoading, error } = useRefs(RESOURCE_KEYS);
  const runs = useQuery({ queryKey: ["runs"], queryFn: api.runs });

  const actions = (
    <Link className="button primary" to="/generate">
      Generate timetable
    </Link>
  );

  if (error) return <Page title="Overview" actions={actions}><ErrorBox error={error} /></Page>;
  if (isLoading) return <Page title="Overview" actions={actions}><Loading /></Page>;

  const activeAssignments = (refs.assignments ?? []).filter((row) => row.is_active);
  const sessions = activeAssignments.reduce((sum, row) => sum + Number(row.sessions_per_week), 0);
  const latest = runs.data?.[0];

  return (
    <Page title="Overview" actions={actions}>
      <div className="tiles">
        {RESOURCE_KEYS.map((key) => (
          <Link key={key} className="tile" to={`/data/${key}`}>
            <div className="tile-label">{RESOURCES[key].label}</div>
            <div className="tile-value">{refs[key]?.length ?? 0}</div>
          </Link>
        ))}
      </div>
      <div className="grid-2">
        <div className="card">
          <h2>Weekly demand</h2>
          <p>
            <b>{sessions}</b> sessions per week from <b>{activeAssignments.length}</b> active assignments.
          </p>
        </div>
        <div className="card">
          <h2>Latest run</h2>
          {latest ? (
            <>
              <p>
                <Badge>{latest.status}</Badge> started {formatDateTime(latest.started_at)}, {latest.elapsed_seconds}s
                {latest.total_weighted_penalty !== null && (
                  <>
                    , weighted penalty <b>{latest.total_weighted_penalty}</b>
                  </>
                )}
              </p>
              <p>
                <Link to="/timetable">Open timetable</Link> · <Link to="/generate">Run details</Link>
              </p>
            </>
          ) : (
            <p className="muted">
              No timetable generated since the server started. <Link to="/generate">Generate one</Link>.
            </p>
          )}
        </div>
      </div>
    </Page>
  );
}
