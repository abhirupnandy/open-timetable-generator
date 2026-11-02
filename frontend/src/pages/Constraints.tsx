import { Badge } from "../components/Badge";
import { Page } from "../components/Layout";
import { ErrorBox, Loading } from "../components/States";
import { humanize } from "../lib/format";
import { useConfig } from "../lib/hooks";

function Params({ item, skip }: { item: Record<string, unknown>; skip: string[] }) {
  const entries = Object.entries(item).filter(([key]) => !skip.includes(key));
  if (!entries.length) return <span className="muted">—</span>;
  return (
    <>
      {entries.map(([key, value]) => (
        <div key={key} className="mono">
          {key}={typeof value === "object" ? JSON.stringify(value) : String(value)}
        </div>
      ))}
    </>
  );
}

export function Constraints() {
  const config = useConfig();

  if (config.error) return <Page title="Constraints"><ErrorBox error={config.error} /></Page>;
  if (!config.data) return <Page title="Constraints"><Loading /></Page>;

  const { calendar, solver, hard, constraints, soft } = config.data.config;

  return (
    <Page title="Constraints">
      <div className="card">
        <p className="muted" style={{ margin: 0 }}>
          Read-only. Edit <span className="mono">config/timetable.toml</span> and restart the server to change
          constraints. Always on: each session placed once; no faculty, student or room overlap; session fits in the
          day; room type, capacity and online/in-person rules.
        </p>
      </div>
      <div className="grid-2">
        <div className="card">
          <h2>Calendar</h2>
          <p>{calendar.days.map(humanize).join(", ")}</p>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Period</th>
                  <th>Start</th>
                  <th>End</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {calendar.periods.map((period) => (
                  <tr key={period.number}>
                    <td>P{period.number}</td>
                    <td>{period.start}</td>
                    <td>{period.end}</td>
                    <td>{period.number === calendar.lunch_after_period && <Badge kind="">lunch after</Badge>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted">
            Blocked for everyone:{" "}
            {calendar.blocked_slots.length
              ? calendar.blocked_slots
                  .map((slot) => `${humanize(slot.day)} P${slot.period}${slot.label ? ` (${slot.label})` : ""}`)
                  .join(", ")
              : "none"}
          </p>
        </div>
        <div className="card">
          <h2>Solver</h2>
          <p>
            Time limit {solver.max_time_seconds}s · {solver.workers} workers
          </p>
          <h2 style={{ marginTop: 20 }}>Optional hard constraints</h2>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Key</th>
                  <th>State</th>
                  <th>Parameters</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(hard).map(([key, item]) => (
                  <tr key={key} className={item.enabled ? "" : "off"}>
                    <td>{key}</td>
                    <td>{item.enabled ? <Badge>on</Badge> : "off"}</td>
                    <td>
                      <Params item={item} skip={["enabled"]} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
      <div className="card">
        <h2>Flexible constraints</h2>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Key</th>
                <th>Mode</th>
                <th className="num">Weight</th>
                <th>Parameters</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(constraints).map(([key, item]) => (
                <tr key={key} className={item.mode === "off" ? "off" : ""}>
                  <td>{key}</td>
                  <td>{item.mode}</td>
                  <td className="num">{item.weight}</td>
                  <td>
                    <Params item={item} skip={["mode", "weight"]} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <div className="card">
        <h2>Soft constraints</h2>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Key</th>
                <th>State</th>
                <th className="num">Weight</th>
                <th>Parameters</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(soft).map(([key, item]) => (
                <tr key={key} className={item.enabled ? "" : "off"}>
                  <td>{key}</td>
                  <td>{item.enabled ? <Badge>on</Badge> : "off"}</td>
                  <td className="num">{item.weight}</td>
                  <td>
                    <Params item={item} skip={["enabled", "weight"]} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Page>
  );
}
