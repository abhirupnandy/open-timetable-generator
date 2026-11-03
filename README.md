# Open Timetable Generator

Institutional timetable-generation backend: FastAPI/SQLAlchemy API and database, plus a CP-SAT timetable solver with configurable hard and soft constraints, an independent validator, a score report and CSV/Excel exports.

## Features

- Core domain entities: School, Course, Faculty, Room, Subject, AcademicGroup and TeachingAssignment, plus constraint inputs (unavailability, group blocked slots, session locks).
- FastAPI CRUD APIs under `/api/v1`, Pydantic v2 schemas, SQLAlchemy 2.x models, Alembic migrations, SQLite for development.
- CP-SAT solver (`app/optimisation`) built on per-slot occupancy, so model size grows linearly with the number of candidates.
- Every optional constraint is configured in `config/timetable.toml` (off / soft / hard, weights, parameters).
- Pre-solve diagnostics that explain infeasibility (empty domains, over-cap faculty, overloaded groups/room types, conflicting locks).
- Independent post-solve validator for every hard rule and independent calculators for every soft penalty, compared with the solver's own values in the score report.
- Exports: master CSV, master/day/faculty Excel workbooks (with a Summary sheet), printable days x periods grids per group/faculty/room, `score_report.json`.

## Technology stack

- Python 3.14
- uv
- FastAPI
- SQLAlchemy 2.x
- Alembic
- SQLite
- Pydantic v2
- pydantic-settings
- pytest
- pytest-asyncio
- httpx
- Ruff
- Node.js 20+ (frontend): React 19, TypeScript, Vite, TanStack Query, React Router, Vitest

## Project structure

```text
open-timetable-generator/
├── app/
│   ├── api/
│   │   ├── router.py
│   │   └── v1/
│   ├── core/              # settings, timetable_config.py (TOML config model)
│   ├── db/
│   │   └── models/
│   ├── domain/            # solver-independent scheduling model, diagnostics, validator
│   ├── export/            # CSV / Excel exporters
│   ├── optimisation/      # CP-SAT model, constraints, penalty calculators, score report
│   ├── schemas/
│   ├── frontend.py        # serves frontend/dist with SPA fallback
│   └── run_timetable.py   # command-line timetable generation
├── frontend/              # React + TypeScript web UI (Vite)
│   └── src/{pages,components,lib}
├── config/
│   └── timetable.toml     # calendar, solver and constraint configuration
├── tests/
│   ├── api/
│   ├── core/
│   ├── db/
│   ├── domain/
│   ├── export/
│   ├── integration/
│   └── optimisation/
├── data/
│   ├── input/
│   └── output/
├── scripts/
├── docs/
├── migrations/
│   └── versions/
├── alembic.ini
├── pyproject.toml
├── uv.lock
├── .python-version
├── README.md
└── README_DEV.md
```

## Setup

From the project directory:

```bash
uv sync
```

The project pins Python 3.14 in `.python-version` and requires `>=3.14,<3.15`.

## Database

The default development database is:

```text
data/open_timetable.db
```

Create/update the schema with Alembic:

```bash
uv run alembic upgrade head
```

Rollback one migration:

```bash
uv run alembic downgrade -1
```

Restore it:

```bash
uv run alembic upgrade head
```

The application does not call `Base.metadata.create_all()`; schema creation is migration-controlled.

## Run the API

```bash
uv run uvicorn app.main:app --reload
```

Then open:

- Web UI: http://127.0.0.1:8000/
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json
- Health: http://127.0.0.1:8000/health

## Tests

```bash
uv run pytest
```

Tests never touch `data/open_timetable.db`. API tests use a temporary SQLite database, and tests that need realistic data import `samples/sample_data.xlsx` into a temporary database. The seeded integration test solves with a 20-second limit. Frontend tests: `cd frontend && npm test`.

## Getting started (full workflow)

```bash
uv sync
uv run alembic upgrade head                        # create / update the database
cd frontend && npm install && npm run build && cd ..
uv run uvicorn app.main:app --reload               # from the repository root
```

Open http://127.0.0.1:8000/ and follow the checklist on the Overview page:

1. **Import data.** Download the blank Excel template (or the filled-in example), fill in one sheet per kind of record and upload it. The whole workbook is validated before anything is written. Every problem is listed with its sheet, row and column, and nothing changes until the file is clean. A successful import replaces all scheduling data.
2. **Review constraints.** Edit the calendar, solver limits and every hard, flexible and soft constraint on the Constraints page. Changes are saved to `config/timetable.toml` and validated (unknown keys, bad periods and negative weights are rejected with a message on the field).
3. **Generate.** Start a run with a time limit and watch it move through loading, solving, validating and exporting.
4. **View.** Browse the grids, print them, and download the CSV/Excel exports and the score report.

Every record can be edited afterwards on the Edit data pages. "Current data" on the Import page exports the database in the template format, so you can edit it in Excel and re-import it.

### Data workbook

Sheets: Schools, Courses, Faculty, Rooms, Subjects, Groups, Assignments, plus optional Unavailability, GroupBlockedSlots and SessionLocks. Records refer to each other by code (school code, course code, group code, faculty employee ID, room code), never by database ID. The Instructions sheet documents every column, and enum and boolean columns have dropdowns. `samples/sample_data.xlsx` is a complete example: 16 programme-year groups with two lab batches each, 28 faculty, 16 rooms, 64 subjects and 80 assignments (173 weekly sessions).

The same operations are available from the command line:

```bash
uv run python -m app.data_io template my_template.xlsx
uv run python -m app.data_io import filled_in.xlsx
uv run python -m app.data_io export current.xlsx
```

### Runs, failures and logs

Every run is stored in the `timetable_runs` table with its status, stage, progress log and results, so history survives restarts. A failed run records a short reason and the full detail. Examples:

- No data: "There are no active teaching assignments to schedule".
- Pre-solve problems: each problem is listed, such as faculty over their weekly cap, groups or room types over capacity, empty candidate domains, or conflicting locks.
- CP-SAT proved the problem infeasible: the enabled optional hard constraints are listed as candidates to relax.
- Time limit reached without a solution.
- Unexpected errors: the traceback is kept.

The Run history page lists all runs and can filter to failures. Runs interrupted by a server restart are marked failed. Server-side logs go to the console and `output/logs/app.log`.

## Web UI

The frontend is a React + TypeScript app in `frontend/`, built with Vite. It uses React Router for pages and TanStack Query for data fetching and polling. FastAPI serves the production build, so one server hosts both the API and the UI.

```bash
cd frontend
npm install
npm run build          # writes frontend/dist, served by FastAPI at /
cd ..                  # back to the repository root
uv run uvicorn app.main:app --reload
```

Start uvicorn from the repository root. From `frontend/` Python can't import the project's `app` package (`ModuleNotFoundError: No module named 'app'`). Don't fix that error by installing a package named `app`: unrelated PyPI packages (for example `myapplication`) provide a top-level `app` module that shadows this project.

For frontend development with hot reload, run FastAPI on :8000 and the Vite dev server alongside it. Vite proxies `/api` to FastAPI:

```bash
cd frontend && npm run dev      # http://localhost:5173
```

Other scripts: `npm test` (Vitest + Testing Library) and `npm run typecheck`. If `frontend/dist` doesn't exist, `/` shows how to build it. Client-side routes such as `/timetable` fall back to `index.html`.

Pages:

- **Overview**: setup checklist (import, constraints, generate, view), data counts and the latest run.
- **Import data**: template, example and current-data downloads, and upload with row-level validation errors.
- **Edit data**: list, filter, sort, add, edit and delete every resource, including unavailability, group blocked slots and session locks.
- **Generate**: start a solve with a time limit, watch its stages, then see the headline metrics, the score report (independent calculator vs solver) and download links for every export.
- **Run history**: every run with status and failure reason. Filter to failures, inspect the error details and log, or delete a run.
- **Timetable**: days x periods grid per group (including parent and batch sessions), faculty member or room, with lunch and blocked slots marked. The grid is print-friendly.
- **Constraints**: edit `config/timetable.toml` (calendar, solver, optional hard, flexible and soft constraints). The form is generated from the config's JSON schema, and you can save, discard or reset to defaults.

Solving runs in a background thread through `POST /api/v1/timetable/runs`, and the UI polls `GET /api/v1/timetable/runs/{id}`. Only one run can be active at a time. Runs are stored in the database, and their export files go to `output/runs/<id>/`.

If a page stays on "Loading" or shows "returned text/html instead of JSON" in dev mode, the Vite dev server isn't proxying `/api`. Make sure FastAPI is running on :8000 and restart `npm run dev`.

## Generate a timetable

```bash
uv run python -m app.run_timetable                      # uses config/timetable.toml
uv run python -m app.run_timetable --config my.toml --output-dir output
```

The run prints the configuration summary, solver status, objective, best bound, build/solve time and peak memory, validates the result against every hard rule, prints the score report and writes to `output/`:

- `timetable_master.csv`, `timetable_master.xlsx` (with a Summary sheet), `timetable_by_day.xlsx`, `timetable_by_faculty.xlsx`
- `grid_by_group.xlsx`, `grid_by_faculty.xlsx`, `grid_by_room.xlsx` (days x periods, printable)
- `score_report.json`

On the sample data the model has about 40k candidates and 58k variables, builds in under a second and peaks at about 2 GB RSS with 8 workers.

If the problem is infeasible, the run stops with the pre-solve diagnostics and the list of enabled optional hard constraints that could be relaxed.

## Constraint configuration

`config/timetable.toml` holds the calendar (days, period times, lunch position, global blocked slots such as Monday P6 TREP), solver settings and every optional constraint. Unknown keys are rejected.

- Always on (not configurable): each session placed exactly once; no faculty, student-population or room overlap; session fits in the day; room type, room capacity and online/in-person rules.
- Optional hard: `faculty_daily_span`, `faculty_weekly_cap`, `faculty_weekly_minimum`, `locked_sessions`, `group_blocked_slots`, `role_restrictions`.
- Flexible (`mode = "off" | "soft" | "hard"`): `no_session_across_lunch`, `faculty_max_consecutive`, `student_max_consecutive`.
- Soft (`enabled`, `weight`): `student_gaps` (S1), `student_min_free_periods` (S14), `subject_spreading` (S4), `faculty_workload_balance` (S2), `faculty_max_lectures_per_day` (S11), `faculty_time_preference` (S3), `avoid_periods`, `faculty_gaps`, `room_stability`, `subject_day_spacing`, `group_daily_load_balance`, `parallel_batch_labs`, `room_size_fit`, `faculty_compact_days`, `consistent_subject_time`, `faculty_daily_load`, `online_at_day_edges`, `faculty_preferred_day_off`, `stability_vs_previous`.

Student populations follow the group hierarchy: a session for a group is attended by all of its leaf groups (batches). A parent group conflicts with its batches; sibling batches may run in parallel.

## API endpoints

All CRUD endpoints are under `/api/v1`:

- `/schools`
- `/courses`
- `/faculty`
- `/rooms`
- `/subjects`
- `/groups`
- `/assignments`
- `/unavailability` (faculty/room unavailable period ranges; shared rooms record external bookings here)
- `/group-blocked-slots` (e.g. Year 1 sports, applies to the group and its batches)
- `/session-locks` (pin a session to a day/start period and optionally a room)
- `/data/template`, `/data/sample`, `/data/export`, `/data/import` (raw .xlsx body), `/data/summary`, `/data/clear`
- `/timetable/config` (GET/PUT), `/timetable/config/schema`, `/timetable/config/reset`
- `/timetable/runs` (`?status_filter=failed`), `/timetable/runs/{id}` (GET/DELETE), `/timetable/runs/{id}/files/{name}`

Each CRUD resource provides GET list, POST create, GET by ID, PATCH by ID and DELETE by ID.

## Configuration

Environment variables supported by `pydantic-settings`:

```text
APP_NAME=Open Timetable Generator
APP_VERSION=0.1.0
DEBUG=true
DATABASE_URL=sqlite:///./data/open_timetable.db
```

Use `.env` for local overrides. Environment files are ignored by Git.

## Scope boundary

Not implemented yet:

- combined classes / electives (one assignment, several groups), multiple faculty per session, open-elective blocks
- greedy warm start (a previous timetable can be used as a CP-SAT hint via `stability_vs_previous`)
- LNS and staged solving for large schools
- per-school caps on shared-room usage
- versioned timetable sessions
- LLM integration
- authentication/authorisation
- Redis/Celery/background jobs
- production deployment
