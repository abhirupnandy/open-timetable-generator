import { describe, expect, it } from "vitest";

import { runDetail } from "../test/fixtures";
import { blockedFor, dayCells, entityOptions, entriesFor, relatedGroups } from "./timetable";

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
    expect(options.group.map((option) => option.value)).toEqual(["G1", "G1-B1", "G1-B2"]);
    expect(options.group[1].label).toBe("G1-B1 · Batch 1");
    expect(options.room.map((option) => option.value)).toEqual(["LAB-1", "LH-1"]);
  });

  it("keys faculty by employee ID and labels them with designation", () => {
    const sameName = [
      { ...entries[0], faculty: "A Rao", faculty_code: "F1", faculty_designation: "PROFESSOR" },
      { ...entries[1], faculty: "A Rao", faculty_code: "P9", faculty_designation: "PHD_SCHOLAR" },
    ];
    expect(entityOptions(sameName, parents).faculty).toEqual([
      { value: "P9", label: "A Rao (PhD Scholar) · P9" },
      { value: "F1", label: "A Rao (Prof.) · F1" },
    ]);
    expect(entriesFor(sameName, "faculty", "P9", parents).map((entry) => entry.session_id)).toEqual(["a:2:s:1"]);
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

describe("blockedFor", () => {
  const global = [{ day: "MONDAY", period: 4, label: "TREP" }];
  const groupSlots = [
    { group_code: "G1", day: "TUESDAY", period: 1, label: "Sports" },
    { group_code: "G1-B2", day: "WEDNESDAY", period: 2, label: "Seminar" },
    { group_code: "G1-B1", day: "MONDAY", period: 4, label: "Clash" },
  ];

  it("adds blocks of overlapping groups in the group view", () => {
    expect(blockedFor("group", "G1-B1", parents, global, groupSlots)).toEqual([
      ...global,
      { day: "TUESDAY", period: 1, label: "Sports (G1)" },
    ]);
    expect(blockedFor("group", "G1", parents, global, groupSlots).map((slot) => slot.label)).toEqual([
      "TREP",
      "Sports",
      "Seminar (G1-B2)",
    ]);
  });

  it("ignores group blocks in faculty and room views", () => {
    expect(blockedFor("faculty", "Dr A", parents, global, groupSlots)).toEqual(global);
  });
});
