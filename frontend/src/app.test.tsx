import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { config, rooms, runDetail, runSummary, schools } from "./test/fixtures";
import { mockApi, renderApp } from "./test/utils";

afterEach(() => vi.unstubAllGlobals());

describe("resource pages", () => {
  it("lists rows with reference labels and filters them", async () => {
    mockApi({ "GET /rooms": rooms, "GET /schools": schools });
    renderApp("/data/rooms");

    expect(await screen.findByText("LH-1")).toBeInTheDocument();
    expect(screen.getByText("Computer lab")).toBeInTheDocument();
    expect(screen.getByText("2 of 2")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Filter"), "lab");
    expect(screen.queryByText("LH-1")).not.toBeInTheDocument();
    expect(screen.getByText("1 of 2")).toBeInTheDocument();
  });

  it("creates a record with typed values and shows server errors", async () => {
    let attempts = 0;
    const calls = mockApi({
      "GET /rooms": rooms,
      "GET /schools": schools,
      "POST /rooms": () => {
        attempts += 1;
        if (attempts === 1) {
          return new Response(JSON.stringify({ detail: [{ loc: ["body", "capacity"], msg: "too small" }] }), {
            status: 422,
          });
        }
        return { id: 9 };
      },
    });
    renderApp("/data/rooms");

    await userEvent.click(await screen.findByRole("button", { name: "Add room" }));
    const dialog = await screen.findByRole("dialog");

    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(within(dialog).getByRole("alert")).toHaveTextContent("Required: Code, Name, Room type, Capacity, School");

    await userEvent.type(within(dialog).getByLabelText("Code *"), "CR-9");
    await userEvent.type(within(dialog).getByLabelText("Name *"), "Classroom 9");
    await userEvent.selectOptions(within(dialog).getByLabelText("Room type *"), "CLASSROOM");
    await userEvent.type(within(dialog).getByLabelText("Capacity *"), "40");
    await userEvent.selectOptions(within(dialog).getByLabelText("School *"), "1");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));

    expect(await within(dialog).findByRole("alert")).toHaveTextContent("capacity: too small");

    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    const post = calls.filter((call) => call.method === "POST").at(-1);
    expect(post?.body).toEqual({
      code: "CR-9",
      name: "Classroom 9",
      room_type: "CLASSROOM",
      capacity: 40,
      school_id: 1,
      is_shared: false,
      is_active: true,
    });
  });

  it("deletes after confirmation", async () => {
    const calls = mockApi({
      "GET /schools": schools,
      "DELETE /schools/1": new Response(null, { status: 204 }),
    });
    renderApp("/data/schools");

    await userEvent.click(await screen.findByRole("button", { name: "Delete" }));
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(calls.some((call) => call.method === "DELETE")).toBe(true));
  });
});

describe("generate page", () => {
  it("shows the score report and flags mismatches", async () => {
    mockApi({
      "GET /timetable/config": config,
      "GET /timetable/runs": [runSummary],
      "GET /timetable/runs/run1": runDetail,
    });
    renderApp("/generate");

    expect(await screen.findByText("Run run1")).toBeInTheDocument();
    expect(screen.getByText("All hard constraints pass")).toBeInTheDocument();
    const row = screen.getByText("student_gaps", { selector: "td" }).closest("tr")!;
    expect(row).toHaveClass("mismatch");
    expect(within(row).getByText("mismatch")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Master CSV" })).toHaveAttribute(
      "href",
      "/api/v1/timetable/runs/run1/files/timetable_master.csv",
    );
  });

  it("starts a run with the chosen time limit", async () => {
    const calls = mockApi({
      "GET /timetable/config": config,
      "GET /timetable/runs": [],
      "POST /timetable/runs": { ...runSummary, id: "run2", status: "running" },
      "GET /timetable/runs/run2": { ...runDetail, id: "run2", status: "running", result: null, elapsed_seconds: 5 },
    });
    renderApp("/generate");

    const input = await screen.findByLabelText("Time limit (seconds)");
    await userEvent.clear(input);
    await userEvent.type(input, "30");
    await userEvent.click(screen.getByRole("button", { name: "Run solver" }));

    await waitFor(() =>
      expect(calls.find((call) => call.method === "POST")?.body).toEqual({ max_time_seconds: 30 }),
    );
  });
});

describe("timetable page", () => {
  it("renders the grid for a batch including parent sessions", async () => {
    localStorage.setItem("ttBy", "group");
    localStorage.setItem("ttEntity", "G1-B1");
    mockApi({
      "GET /timetable/config": config,
      "GET /timetable/runs": [runSummary],
      "GET /timetable/runs/run1": runDetail,
    });
    renderApp("/timetable");

    expect(await screen.findByRole("heading", { name: "G1-B1 · Batch 1" })).toBeInTheDocument();
    expect(screen.getByText("Maths")).toBeInTheDocument();
    expect(screen.getAllByText("Lab")).toHaveLength(2); // split by lunch
    expect(screen.queryByText("Physics")).not.toBeInTheDocument(); // sibling batch
    expect(screen.getByText("TREP")).toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("View by"), "faculty");
    expect(await screen.findByRole("heading", { name: "Dr A" })).toBeInTheDocument();
    expect(screen.getByText("Physics")).toBeInTheDocument();
  });

  it("asks for a run when there is none", async () => {
    mockApi({ "GET /timetable/config": config, "GET /timetable/runs": [] });
    renderApp("/timetable");
    expect(await screen.findByText(/No timetable yet/)).toBeInTheDocument();
  });
});

describe("constraints page", () => {
  it("shows hard, flexible and soft constraints", async () => {
    mockApi({ "GET /timetable/config": config });
    renderApp("/constraints");
    expect(await screen.findByText("faculty_daily_span")).toBeInTheDocument();
    expect(screen.getByText("no_session_across_lunch")).toBeInTheDocument();
    expect(screen.getByText("faculty_compact_days").closest("tr")).toHaveClass("off");
  });
});
