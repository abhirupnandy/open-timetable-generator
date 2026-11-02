import { describe, expect, it } from "vitest";

import { runDetail } from "../test/fixtures";
import { dayCells, entityOptions, entriesFor, relatedGroups } from "./timetable";

const { entries, calendar, group_parents: parents } = runDetail.result!;

describe("relatedGroups", () => {
  it("includes ancestors and descendants but not siblings", () => {
    expect([...relatedGroups("G1-B1", parents)].sort()).toEqual(["G1", "G1-B1"]);
    expect([...relatedGroups("G1", parents)].sort()).toEqual(["G1", "G1-B1", "G1-B2"]);
  });
});

describe("entriesFor", () => {
  it("shows parent sessions in a batch view", () => {
    const ids = entriesFor(entries, "group", "G1-B1", parents).map((entry) => entry.session_id);
    expect(ids).toEqual(["a:1:s:1", "a:2:s:1"]);
  });

  it("filters by faculty and room", () => {
    expect(entriesFor(entries, "faculty", "Dr A", parents)).toHaveLength(2);
    expect(entriesFor(entries, "room", "LAB-1", parents)).toHaveLength(1);
  });

  it("lists entity options", () => {
    const options = entityOptions(entries, parents);
    expect(options.group).toEqual(["G1", "G1-B1", "G1-B2"]);
    expect(options.room).toEqual(["LAB-1", "LH-1"]);
  });
});

describe("dayCells", () => {
  const blocked = [{ day: "MONDAY", period: 4, label: "TREP" }];

  it("splits sessions at lunch and marks blocked slots", () => {
    const cells = dayCells(entries, "MONDAY", calendar, blocked);
    expect(cells.map((cell) => cell.kind)).toEqual(["sessions", "sessions", "lunch", "sessions", "blocked"]);
    // The P2-P3 lab is split by lunch rather than merged across it.
    expect(cells[1]).toMatchObject({ period: 2, span: 1 });
    expect(cells[3]).toMatchObject({ period: 3, span: 1 });
    expect(cells[4]).toMatchObject({ label: "TREP" });
  });

  it("merges consecutive periods of the same session", () => {
    const cells = dayCells(entries, "TUESDAY", calendar, blocked);
    expect(cells.map((cell) => (cell.kind === "sessions" ? cell.span : cell.kind))).toEqual([1, 1, "lunch", 2]);
  });
});
