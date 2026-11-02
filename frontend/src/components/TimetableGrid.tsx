import { humanize, hue } from "../lib/format";
import { dayCells, type GridView } from "../lib/timetable";
import type { BlockedSlot, CalendarInfo, TimetableEntry } from "../lib/types";

function SessionCard({ entry, view }: { entry: TimetableEntry; view: GridView }) {
  const meta = [
    view !== "group" ? entry.group_code : null,
    view !== "faculty" ? entry.faculty : null,
    view !== "room" ? entry.room ?? "Online" : null,
  ].filter(Boolean);

  return (
    <div className="session" style={{ "--hue": hue(entry.subject) } as React.CSSProperties} title={entry.session_id}>
      <div className="s-title">{entry.subject}</div>
      <div className="s-meta">{meta.join(" · ")}</div>
    </div>
  );
}

interface GridProps {
  entries: TimetableEntry[];
  calendar: CalendarInfo;
  view: GridView;
  blocked: BlockedSlot[];
}

export function TimetableGrid({ entries, calendar, view, blocked }: GridProps) {
  const lunch = calendar.lunch_after_period;

  return (
    <div className="tt-wrap">
      <table className="tt">
        <thead>
          <tr>
            <th className="day" />
            {calendar.periods.map((period) => [
              <th key={period.number} scope="col">
                P{period.number}
                {period.start && (
                  <small>
                    {period.start}–{period.end}
                  </small>
                )}
              </th>,
              period.number === lunch ? <th key="lunch" className="lunch" title="Lunch" /> : null,
            ])}
          </tr>
        </thead>
        <tbody>
          {calendar.days.map((day) => (
            <tr key={day}>
              <th className="day" scope="row">
                {humanize(day)}
              </th>
              {dayCells(entries, day, calendar, blocked).map((cell) => {
                if (cell.kind === "lunch") return <td key="lunch" className="lunch" />;
                if (cell.kind === "blocked") {
                  return (
                    <td key={cell.period} className="blocked">
                      {cell.label}
                    </td>
                  );
                }
                return (
                  <td key={cell.period} colSpan={cell.span}>
                    {cell.entries.map((entry) => (
                      <SessionCard key={entry.session_id} entry={entry} view={view} />
                    ))}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
