# Open Timetable Generator

Phase 1 of the institutional timetable-generation backend: **sample API + database foundation**.

This is a fresh FastAPI/SQLAlchemy project. The current phase deliberately stops at the domain/API layer. Timetable optimisation is not implemented yet.

## Current phase

Implemented in Phase 1:

- Seven core domain entities: School, Course, Faculty, Room, Subject, AcademicGroup and TeachingAssignment.
- Pydantic v2 request/response schemas.
- SQLAlchemy 2.x typed declarative models.
- SQLite development database.
- Alembic migrations.
- FastAPI CRUD APIs under `/api/v1`.
- Foreign-key validation and conflict handling.
- Simple list filters for school, course, faculty and group relationships.
- Sample seed data.
- Automated API tests.

The future optimisation architecture follows the design document: CP-SAT as the core solver, greedy warm starts, staged solving/decomposition and LNS at scale, with independent deterministic validation and Excel exports. Those components are intentionally outside Phase 1. The design document describes the later pipeline and outputs on pages 5–10. 

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

## Project structure

```text
open-timetable-generator/
├── app/
│   ├── api/
│   │   ├── router.py
│   │   └── v1/
│   ├── core/
│   ├── db/
│   │   └── models/
│   └── schemas/
├── tests/
│   ├── api/
│   ├── db/
│   └── integration/
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

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- OpenAPI JSON: http://127.0.0.1:8000/openapi.json
- Health: http://127.0.0.1:8000/health

## Tests

```bash
uv run pytest
```

Tests use a separate temporary SQLite database and do not modify `data/open_timetable.db`.

## Seed sample data

After running the migration:

```bash
uv run python scripts/seed_sample_data.py
```

The seed contains one School of AI, B.Tech AI and BCA courses, four faculty members, four rooms, four subjects, two lecture groups, two batches, and four teaching assignments. It is only for exercising the CRUD API; it does not generate a timetable.

## API endpoints

All CRUD endpoints are under `/api/v1`:

- `/schools`
- `/courses`
- `/faculty`
- `/rooms`
- `/subjects`
- `/groups`
- `/assignments`

Each provides GET list, POST create, GET by ID, PATCH by ID and DELETE by ID.

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

The following are deliberately deferred:

- CP-SAT timetable generation
- greedy warm start
- LNS
- large-school staged room solving
- conflict-graph optimisation
- pre-analysis engine
- independent timetable validator
- versioned timetable sessions
- Excel exports
- LLM integration
- authentication/authorisation
- Redis/Celery/background jobs
- production deployment

The design document's implementation roadmap places the integrated hard-constraint model and deterministic validator in the next implementation phase, followed by soft constraints and Excel exports. 
