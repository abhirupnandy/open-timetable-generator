import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  config,
  configSchema,
  facultyUser,
  failedRun,
  rooms,
  runDetail,
  runSummary,
  schools,
} from "./test/fixtures";
import { json, mockApi, renderApp } from "./test/utils";

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
          return json({ detail: [{ loc: ["body", "capacity"], msg: "too small" }] }, 422);
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
    const started = { ...runSummary, id: "run2", status: "running" as const, stage: "solving" };
    let runs: (typeof started)[] = [];
    const calls = mockApi({
      "GET /timetable/config": config,
      "GET /timetable/runs": () => runs,
      "GET /data/summary": { teaching_assignments: 3 },
      "POST /timetable/runs": () => {
        runs = [started];
        return started;
      },
      "GET /timetable/runs/run2": { ...runDetail, id: "run2", status: "running", stage: "solving", result: null, elapsed_seconds: 5 },
    });
    renderApp("/generate");

    const input = await screen.findByLabelText("Time limit (seconds)");
    await userEvent.clear(input);
    await userEvent.type(input, "30");
    await userEvent.click(screen.getByRole("button", { name: "Generate timetable" }));

    await waitFor(() =>
      expect(calls.find((call) => call.method === "POST")?.body).toEqual({ max_time_seconds: 30 }),
    );
    expect(await screen.findByText(/Generating timetable/)).toBeInTheDocument();
    expect(screen.getByText("Solving", { selector: ".stages li" })).toHaveClass("current");
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

  it("shows designations and opens a PDF for printing", async () => {
    localStorage.setItem("ttBy", "faculty");
    localStorage.setItem("ttEntity", "F2");
    const open = vi.fn();
    vi.stubGlobal("open", open);
    const withDesignations = {
      ...runDetail,
      result: {
        ...runDetail.result!,
        entries: runDetail.result!.entries.map((entry) =>
          entry.faculty === "Dr A"
            ? { ...entry, faculty: "Ravi Kumar", faculty_code: "F2", faculty_designation: "PHD_SCHOLAR" }
            : { ...entry, faculty_code: "F1", faculty_designation: "ASSISTANT_PROFESSOR" },
        ),
      },
    };
    mockApi({
      "GET /timetable/config": config,
      "GET /timetable/runs": [runSummary],
      "GET /timetable/runs/run1": withDesignations,
    });
    renderApp("/timetable");

    expect(await screen.findByRole("heading", { name: "Ravi Kumar (PhD Scholar) · F2" })).toBeInTheDocument();
    const select = screen.getByLabelText("Faculty");
    expect(within(select).getByRole("option", { name: "Dr B (Asst. Prof.) · F1" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Print / PDF" }));
    expect(open).toHaveBeenCalledWith("/api/v1/timetable/runs/run1/pdf?by=faculty&entity=F2", "_blank", "noopener");
    await userEvent.click(screen.getByRole("button", { name: "PDF of all faculty" }));
    expect(open).toHaveBeenLastCalledWith("/api/v1/timetable/runs/run1/pdf?by=faculty", "_blank", "noopener");

    await userEvent.selectOptions(screen.getByLabelText("View by"), "group");
    expect(await screen.findAllByText(/Ravi Kumar \(PhD Scholar\)/)).not.toHaveLength(0);
  });

  it("asks for a run when there is none", async () => {
    mockApi({ "GET /timetable/config": config, "GET /timetable/runs": [] });
    renderApp("/timetable");
    expect(await screen.findByText(/No timetable yet/)).toBeInTheDocument();
  });
});

describe("constraints page", () => {
  const routes = () => ({
    "GET /timetable/config": config,
    "GET /timetable/config/schema": configSchema,
  });

  it("edits a constraint and saves the whole config", async () => {
    const calls = mockApi({ ...routes(), "PUT /timetable/config": (body: unknown) => ({ ...config, config: body }) });
    renderApp("/constraints");

    const card = (await screen.findByText("faculty_compact_days")).closest(".constraint") as HTMLElement;
    expect(card).toHaveClass("is-off");
    await userEvent.click(within(card).getByLabelText("faculty_compact_days enabled"));
    const weight = within(card).getByLabelText("Weight");
    await userEvent.clear(weight);
    await userEvent.type(weight, "7");

    expect(screen.getByText("Unsaved changes")).toBeInTheDocument();
    await userEvent.click(screen.getAllByRole("button", { name: "Save" })[0]);

    await waitFor(() => expect(calls.some((call) => call.method === "PUT")).toBe(true));
    const body = calls.find((call) => call.method === "PUT")!.body as typeof config.config;
    expect(body.soft.faculty_compact_days).toEqual({ enabled: true, weight: 7 });
    expect(body.calendar.days).toEqual(["MONDAY", "TUESDAY"]);
    await waitFor(() => expect(screen.queryByText("Unsaved changes")).not.toBeInTheDocument());
  });

  it("edits calendar lists and tables", async () => {
    const calls = mockApi({ ...routes(), "PUT /timetable/config": (body: unknown) => ({ ...config, config: body }) });
    renderApp("/constraints");
    await userEvent.click(await screen.findByRole("tab", { name: "Calendar" }));

    await userEvent.click(screen.getByLabelText("Wednesday"));
    await userEvent.click(screen.getByRole("button", { name: "Remove Blocked slots row 1" }));
    await userEvent.click(screen.getByRole("button", { name: "Add period" }));
    const lunch = screen.getByLabelText("Lunch after period");
    await userEvent.clear(lunch);

    await userEvent.click(screen.getAllByRole("button", { name: "Save" })[0]);
    await waitFor(() => expect(calls.some((call) => call.method === "PUT")).toBe(true));
    const body = calls.find((call) => call.method === "PUT")!.body as typeof config.config;
    expect(body.calendar.days).toEqual(["MONDAY", "TUESDAY", "WEDNESDAY"]);
    expect(body.calendar.blocked_slots).toEqual([]);
    expect(body.calendar.periods).toHaveLength(5);
    expect(body.calendar.periods[4]).toMatchObject({ number: 5 });
    expect(body.calendar.lunch_after_period).toBeNull();
  });

  it("shows validation errors next to the field and on the tab", async () => {
    mockApi({
      ...routes(),
      "PUT /timetable/config": json(
        { detail: [{ loc: ["body", "soft", "student_gaps", "weight"], msg: "Input should be greater than or equal to 0" }] },
        422,
      ),
    });
    renderApp("/constraints");
    const card = (await screen.findByText("student_gaps")).closest(".constraint") as HTMLElement;
    const weight = within(card).getByLabelText("Weight");
    await userEvent.clear(weight);
    await userEvent.type(weight, "-3");
    await userEvent.click(screen.getAllByRole("button", { name: "Save" })[0]);

    expect(await screen.findByText("Not saved: fix these problems")).toBeInTheDocument();
    expect(within(card).getByText("Input should be greater than or equal to 0")).toBeInTheDocument();
    expect(within(screen.getByRole("tab", { name: /Soft/ })).getByText("1")).toBeInTheDocument();
  });

  it("resets to defaults after confirmation", async () => {
    const calls = mockApi({ ...routes(), "POST /timetable/config/reset": config });
    renderApp("/constraints");
    await userEvent.click(await screen.findByRole("button", { name: "Reset to defaults" }));
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Reset" }));
    await waitFor(() => expect(calls.some((call) => call.path === "/timetable/config/reset")).toBe(true));
  });
});

describe("import page", () => {
  const xlsx = () => new File(["fake"], "data.xlsx", { type: "application/octet-stream" });

  it("uploads a workbook and reports counts", async () => {
    const calls = mockApi({
      "GET /data/summary": { teaching_assignments: 0, schools: 0 },
      "POST /data/import": { ok: true, counts: { Schools: 1, Assignments: 80 }, issues: [] },
    });
    renderApp("/import");

    expect(await screen.findByRole("link", { name: "Template with examples" })).toHaveAttribute(
      "href",
      "/api/v1/data/template",
    );
    expect(screen.getByRole("link", { name: "Blank template" })).toHaveAttribute(
      "href",
      "/api/v1/data/template?blank=true",
    );
    await userEvent.upload(screen.getByLabelText("Workbook file"), xlsx());
    await userEvent.click(screen.getByRole("button", { name: "Import" }));

    expect(await screen.findByText("Import complete")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Generate the timetable/ })).toHaveAttribute("href", "/generate");
    const post = calls.find((call) => call.method === "POST")!;
    expect(post.body).toBeInstanceOf(Blob);
  });

  it("lists every problem when the workbook is rejected", async () => {
    mockApi({
      "GET /data/summary": { teaching_assignments: 5 },
      "POST /data/import": {
        ok: false,
        counts: {},
        issues: [
          { sheet: "Faculty", row: 4, column: "designation", message: "must be one of PROFESSOR, ..." },
          { sheet: "Assignments", row: 9, column: "group_code", message: "'X' is not a code on the Groups sheet" },
        ],
      },
    });
    renderApp("/import");
    await userEvent.upload(await screen.findByLabelText("Workbook file"), xlsx());
    await userEvent.click(screen.getByRole("button", { name: "Import" }));

    expect(await screen.findByText("Import rejected: 2 problems found")).toBeInTheDocument();
    expect(screen.getByText("'X' is not a code on the Groups sheet")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Filter problems"), "faculty");
    expect(screen.queryByText("'X' is not a code on the Groups sheet")).not.toBeInTheDocument();
  });
});

describe("run history", () => {
  it("shows why a run failed with details and log", async () => {
    mockApi({
      "GET /timetable/runs": [{ ...failedRun }, runSummary],
      "GET /timetable/runs/run0": failedRun,
    });
    renderApp("/runs/run0");

    expect(await screen.findByText("Run run0 failed")).toBeInTheDocument();
    expect(screen.getAllByText(/Pre-solve checks found 1 problem/).length).toBeGreaterThan(0);
    expect(screen.getByText(/FACULTY_OVER_CAP/)).toBeInTheDocument();
    expect(screen.getByText(/FAILED: Pre-solve/)).toBeInTheDocument();
  });

  it("filters to failed runs and deletes a run", async () => {
    const calls = mockApi({
      "GET /timetable/runs": [failedRun, runSummary],
      "GET /timetable/runs?status_filter=failed": [failedRun],
      "DELETE /timetable/runs/run0": new Response(null, { status: 204 }),
    });
    renderApp("/runs");

    await userEvent.click(await screen.findByRole("button", { name: "Failed" }));
    await waitFor(() => expect(calls.some((call) => call.path.includes("status_filter=failed"))).toBe(true));
    await userEvent.click(await screen.findByRole("button", { name: "Delete run run0" }));
    await userEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: "Delete" }));
    await waitFor(() => expect(calls.some((call) => call.method === "DELETE")).toBe(true));
  });
});

describe("overview", () => {
  it("guides the user to import data first", async () => {
    mockApi({
      "GET /data/summary": { teaching_assignments: 0, academic_groups: 0, faculty: 0, rooms: 0 },
      "GET /timetable/runs": [],
      "GET /timetable/config": config,
    });
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Import your data" })).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Import data" })[0]).toHaveAttribute("href", "/import");
  });
});

describe("api errors", () => {
  it("explains a non-JSON response instead of hanging", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("<!doctype html>", { status: 200, headers: { "Content-Type": "text/html" } })),
    );
    renderApp("/generate");
    expect(await screen.findByText(/instead of JSON/)).toBeInTheDocument();
  });
});

describe("authentication", () => {
  it("shows the sign-in page and signs in", async () => {
    let signedIn = false;
    const calls = mockApi({
      "GET /auth/me": () => (signedIn ? facultyUser : json({ detail: "Sign in to continue" }, 401)),
      "POST /auth/login": () => {
        signedIn = true;
        return json({ user: facultyUser });
      },
      "GET /timetable/runs": [],
    });
    renderApp("/");

    await userEvent.type(await screen.findByLabelText("Username"), "F2");
    await userEvent.type(screen.getByLabelText("Password"), "secret");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByRole("heading", { name: "My timetable" })).toBeInTheDocument();
    expect(calls.find((call) => call.method === "POST")?.body).toEqual({ username: "F2", password: "secret" });
  });

  it("offers first-time setup when there are no accounts", async () => {
    mockApi({
      "GET /auth/me": json({ detail: "Sign in to continue" }, 401),
      "GET /auth/status": { needs_setup: true },
    });
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Create the administrator account" })).toBeInTheDocument();
  });

  it("limits faculty to their own timetable", async () => {
    const calls = mockApi({
      "GET /auth/me": facultyUser,
      "GET /timetable/runs": [runSummary],
      "GET /timetable/runs/run1": {
        ...runDetail,
        log: "",
        files: [],
        result: {
          scope: "faculty",
          calendar: runDetail.result!.calendar,
          group_parents: {},
          entries: [{ ...runDetail.result!.entries[0], faculty: "Ravi Kumar", faculty_code: "F2" }],
        },
      },
    });
    renderApp("/data/rooms");

    expect(await screen.findByRole("heading", { name: "My timetable" })).toBeInTheDocument();
    expect(await screen.findByText("Maths")).toBeInTheDocument();
    expect(screen.getByText(/Signed in as Ravi Kumar \(PhD Scholar, F2\)/)).toBeInTheDocument();
    expect(screen.queryByLabelText("View by")).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Import data" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "User accounts" })).not.toBeInTheDocument();
    expect(calls.some((call) => call.path.startsWith("/timetable/config"))).toBe(false);
  });

  it("shows user accounts to administrators", async () => {
    mockApi({
      "GET /users": [
        { id: 1, username: "admin", full_name: "Admin User", role: "ADMIN", faculty_employee_id: null, faculty: null,
          is_active: true, last_login_at: null },
        { ...facultyUser },
      ],
      "GET /faculty": [],
    });
    renderApp("/users");
    expect(await screen.findByRole("heading", { name: "User accounts" })).toBeInTheDocument();
    expect(await screen.findByText("Ravi Kumar (PhD Scholar)")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "User accounts" })).toBeInTheDocument();
  });
});
