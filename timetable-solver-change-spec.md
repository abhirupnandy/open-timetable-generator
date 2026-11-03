# Open Timetable Generator: Constraint & Solver Change Specification

Audience: the coding agent implementing these changes in `open-timetable-generator`.
Read this whole document before starting. Phases must be done in order; Phase A is a prerequisite for everything else.

## 0. Ground rules

- Keep the existing architecture: `app/domain` and `app/optimisation` must not import FastAPI.
- Schema changes go through Alembic migrations only. Never call `Base.metadata.create_all()` from app code.
- Every new constraint gets: a config entry, a CP-SAT builder, an independent post-solve calculator (pure Python, no solver variables), and unit tests.
- Keep the existing test suite (234 tests) green.
- Python 3.14, Ruff rules as in `pyproject.toml`.

### Current state (for reference)

- Seed data: 80 teaching assignments → 173 sessions → 40,182 (placement, room) candidates.
- Hard constraints H2/H3/H4/H5 are built with nested pairwise loops over all candidates (~800 million Python comparisons per family; ~2 million room clauses alone). The seeded integration test is OOM-killed on a 4 GB machine.
- `model.minimize(objective)` is commented out in `solver.py`, so all soft constraints are built but ignored.
- An independent audit of the last output found 0 hard violations but 102 student idle gaps, 21 same-day subject repeats and 7 two-period labs spanning lunch (P4→P5).

---

## Phase A: Solver foundation (prerequisite)

### A1. Replace pairwise hard constraints with per-slot occupancy

Build occupancy indexes once, in a single pass over candidates:

- `faculty_slot[(faculty_id, day, period)] -> [candidate vars]`
- `room_slot[(room_id, day, period)] -> [candidate vars]`
- `population_slot[(leaf_group_id, day, period)] -> [candidate vars]`

For student populations: compute the leaf groups (groups with no children). A session for group G is attached to every leaf group that is G or a descendant of G. This keeps parent/batch exclusion and lets sibling batches run in parallel, matching current behaviour.

Then add one `model.add_at_most_one(vars)` per key. Remove `_add_pairwise_candidate_conflict_constraints` and its three callers (faculty, group, room).

Create shared Boolean occupancy variables from the same indexes and expose them for objectives:

- `faculty_busy[f, d, p]`, `group_busy[leaf, d, p]`, `room_busy[r, d, p]` (each equals the sum of its covering candidate vars, which is ≤ 1).

### A2. Daily span (H3) without pairwise candidates

For each faculty and day, for each pair of periods (p, q) with `end_time(q) − start_time(p) > max_daily_span_minutes`, add `faculty_busy[f,d,p] + faculty_busy[f,d,q] <= 1`. This is exact because periods are contiguous time blocks. Only a handful of pairs exist per day.

### A3. Rewrite objective builders to use shared occupancy

`objectives._add_occupied_period_variable` and `build_subject_spreading_objective` currently rescan every candidate for every (group, day, period) / (subject, group, day). Replace with lookups into indexes built once.

### A4. Re-enable optimisation

- Restore `model.minimize(objective)`.
- Move `max_time_in_seconds`, `num_search_workers` and `log_search_progress` into config (defaults: 120 s, 8 workers, logging off).
- Remove debug `print` calls from `solve()`; return status, objective value, best bound and wall time in `SolverResult`.
- Optional: add a solution hint (warm start) from a greedy placement or a previous timetable.

### A5. Small performance fixes

- `candidates.candidate_placements` does a linear `next(...)` search per session. Pass the session object or use a dict.

### A6. Pre-solve diagnostics

Before building the model, check and report clearly (not just raise `EmptyCandidateDomainError(session_id)`):

- Session has no valid placement: say why (duration too long, availability, blocked slots, lunch rule).
- Session has no valid room: say why (no room of the required type, all rooms too small, group capacity missing).
- Faculty demand exceeds weekly cap.
- Group demand (periods/week incl. ancestors) exceeds available slots.
- Room-type demand exceeds room-type supply.

If CP-SAT returns INFEASIBLE, print these diagnostics plus the list of enabled optional hard constraints, so the user knows what to relax.

**Acceptance:** seeded solve completes on a 4 GB machine; peak memory and solve time logged; the integration test passes.

---

## Phase B: Configuration framework (makes everything optional)

### B1. Config file

Add `config/timetable.toml` (load with stdlib `tomllib`) and a Pydantic model in `app/core/timetable_config.py`. CLI flag `--config path` on `run_timetable.py`; default path if absent.

Every optional constraint uses one of these shapes:

- Hard-only optional: `enabled = true|false` plus params.
- Flexible: `mode = "off" | "soft" | "hard"` plus `weight` (used in soft mode) plus params.
- Soft-only: `enabled`, `weight`, params.

Non-negotiable hard constraints stay always on and are **not** configurable: each session placed exactly once, no faculty overlap, no student-population overlap, no room overlap, session fits in the day, room type match, room capacity, online/in-person room rules.

### B2. Calendar in config (remove hard-coded 8-period assumptions)

Move out of code: `PERIOD_TIMES` (`calendar.py`), `DEFAULT_DAYS`, `DEFAULT_PERIODS_PER_DAY` (`input_builder.py`), the Monday P6 block (`candidates.py`), and the S3 preference ranges (`solver.py`, which uses `range(1, 9)`). Derive `periods_per_day` from the period list.

### B3. Example config

```toml
[calendar]
days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]
lunch_after_period = 4          # lunch sits between P4 and P5

[[calendar.periods]]
number = 1
start = "08:20"
end = "09:20"
# ... P2-P8 ...

[[calendar.blocked_slots]]      # applies to everyone (replaces hard-coded TREP)
day = "MONDAY"
period = 6
label = "TREP"

[solver]
max_time_seconds = 120
workers = 8
log_progress = false

# ---------- Optional hard constraints ----------
[hard.faculty_daily_span]
enabled = true
max_minutes = 480

[hard.faculty_weekly_cap]
enabled = true
[hard.faculty_weekly_cap.hours]
PROFESSOR = 9
ASSOCIATE_PROFESSOR = 11
ASSISTANT_PROFESSOR = 13
PHD_SCHOLAR = 8

[hard.faculty_weekly_minimum]
enabled = false
[hard.faculty_weekly_minimum.hours]
PROFESSOR = 6

[hard.locked_sessions]
enabled = true

[hard.group_blocked_slots]
enabled = true

[hard.role_restrictions]
enabled = false
PHD_SCHOLAR = ["LAB", "TUTORIAL"]

# ---------- Flexible (off / soft / hard) ----------
[constraints.no_session_across_lunch]
mode = "soft"                   # off | soft | hard
weight = 60

[constraints.faculty_max_consecutive]
mode = "soft"
weight = 40
max_periods = 3

[constraints.student_max_consecutive]
mode = "off"
weight = 30
max_periods = 4

# ---------- Soft constraints ----------
[soft.student_gaps]             # existing S1
enabled = true
weight = 100

[soft.student_min_free_periods] # existing S14
enabled = true
weight = 90
min_free = 2

[soft.subject_spreading]        # existing S4
enabled = true
weight = 80

[soft.faculty_workload_balance] # existing S2
enabled = true
weight = 70

[soft.faculty_max_lectures_per_day] # existing S11
enabled = true
weight = 60
max_lectures = 2

[soft.faculty_time_preference]  # existing S3
enabled = true
weight = 50
[soft.faculty_time_preference.ranges]
MORNING = [1, 2, 3, 4]
AFTERNOON = [5, 6, 7, 8]
EVENING = [7, 8]

[soft.avoid_periods]            # NEW: P8 and similar
enabled = true
weight = 40
[[soft.avoid_periods.rules]]
period = 8
penalty = 2
[[soft.avoid_periods.rules]]
period = 1
penalty = 1
subject_types = ["LAB"]         # optional filter

[soft.faculty_gaps]             # NEW
enabled = true
weight = 75

[soft.room_stability]           # NEW
enabled = true
weight = 30

[soft.subject_day_spacing]      # NEW
enabled = true
weight = 35

[soft.group_daily_load_balance] # NEW
enabled = true
weight = 30

[soft.parallel_batch_labs]      # NEW
enabled = true
weight = 25

[soft.room_size_fit]            # NEW
enabled = true
weight = 10
waste_unit = 10                 # 1 penalty per 10 empty seats

[soft.faculty_compact_days]     # NEW
enabled = false
weight = 15

[soft.consistent_subject_time]  # NEW
enabled = false
weight = 10

[soft.faculty_daily_load]       # NEW
enabled = true
weight = 30
max_periods = 4

[soft.online_at_day_edges]      # NEW
enabled = true
weight = 20

[soft.faculty_preferred_day_off] # NEW, needs DB field
enabled = false
weight = 40

[soft.stability_vs_previous]    # NEW, needs previous timetable input
enabled = false
weight = 50
previous_timetable = "output/timetable_master.csv"
```

Weights shown are suggested defaults; tune after measuring.

### B4. Rules for the config loader

- Unknown keys are an error (catch typos).
- A constraint that is disabled must add zero variables to the model.
- Print a summary of enabled hard/soft constraints and weights at the start of every run.

**Naming note:** existing soft constraints use IDs S1, S2, S3, S4, S11, S14, so S5–S10, S12 and S13 are presumably defined in the design document. Use config keys as the primary identifier and map them to S-numbers from the design document rather than inventing new numbers.

---

## Phase C: Hard constraint changes

### HC-1. Session across lunch (flexible: off / soft / hard)

- Definition: a session occupying both `lunch_after_period` and `lunch_after_period + 1`.
- Hard mode: drop these placements during candidate generation (same mechanism as blocked slots).
- Soft mode: penalty 1 per such session (a per-candidate constant, no extra variables).
- Per-assignment override: new nullable column `teaching_assignments.allow_across_lunch` (bool). `true` exempts that assignment even in hard mode, for the cases where crossing lunch is intended.

### HC-2. Faculty weekly minimum (optional)

`sum(duration × var) >= min_hours[designation]` per faculty. Pre-solve check: if a faculty member's total assigned hours are below the minimum, report it rather than letting the model go infeasible.

### HC-3. Faculty and room availability from the database

The domain already supports `faculty_availability` and `room_availability` (`ResourceAvailability`), but nothing loads them. Add:

- Table `unavailability`: `resource_type` (FACULTY | ROOM), `resource_id`, `day`, `start_period`, `end_period`, `reason`. Storing unavailability is easier for users than availability windows; convert to windows in `db_input.py`.
- CRUD endpoints under `/api/v1/unavailability`.

### HC-4. Shared rooms

`Room.is_shared` is loaded into `SchedulingRoom` but never used. Shared rooms get their externally booked slots via HC-3 room unavailability. Optionally, a per-school cap on usage of shared rooms.

### HC-5. Group blocked slots

Table `group_blocked_slots` (`academic_group_id`, `day`, `period`, `label`), e.g. Year 1 sports on Wednesday P7–P8. Applies to the group and all descendants. Filter during candidate generation.

### HC-6. Locked / pinned sessions

Table `session_locks` (`teaching_assignment_id`, `session_number`, `day`, `start_period`, optional `room_id`). Restrict that session's candidate domain to matching candidates. Validate locks against other hard rules in pre-solve and report conflicts between locks.

### HC-7. Max consecutive teaching periods for faculty (flexible)

Using `faculty_busy`: for every window of `max_periods + 1` consecutive periods within a half-day (do not cross lunch), hard mode: `sum(window) <= max_periods`; soft mode: penalty var `>= sum(window) − max_periods`.

### HC-8. Student max consecutive periods (flexible)

Same as HC-7 using `group_busy` per leaf population.

### HC-9. Role restrictions (optional)

E.g. PhD scholars only LAB/TUTORIAL. Enforce at assignment creation (API returns 422) and in pre-solve checks. No solver variables needed.

---

## Phase D: Soft constraints

### D0. Fix existing soft constraints

- **S1 student gaps:** compute per leaf population using `group_busy` (which includes parent-group sessions). Today a parent group's gaps ignore its batches' labs and batches ignore the parent's lectures.
- **S14 free periods:** same leaf-population fix. Make `min_free` configurable.
- **S3 time preferences:** read ranges from config; validate periods exist.
- **S2 workload balance:** pairwise absolute differences grow O(n²) per designation. Fine at 28 faculty; if faculty count grows, switch to `max − min` utilisation per designation.
- **S4 spreading:** add its score to the run report (currently calculated nowhere in `run_timetable.py`).

### D1. New soft constraints

Each must have a CP-SAT builder and an independent calculator. Penalty definitions:

| Config key | Definition | Penalty | Model notes |
|---|---|---|---|
| `avoid_periods` (P8) | Sessions in undesirable periods | `rule.penalty` per occupied period matching a rule; optional `subject_types` filter | Per-candidate constant cost; no new variables |
| `faculty_gaps` | Idle periods between a faculty member's first and last class of the day | 1 per idle period. Lunch is not a period, so P4→P5 is not a gap | Same prefix/suffix pattern as S1, on `faculty_busy` |
| `room_stability` | Group changes rooms during the day | per group/day: `distinct rooms used − 1` (0 if no in-person classes) | `room_used[g,d,r] = max(candidates)`; `day_used[g,d]`; penalty = `sum(room_used) − day_used` |
| `subject_day_spacing` | Same subject for a group on adjacent days (Mon+Tue is worse than Mon+Thu) | 1 per adjacent day pair both used | Reuse S4's `day_used[subject, group, day]`; `pen >= a + b − 1` |
| `group_daily_load_balance` | Uneven daily load for a group | per leaf group: `max(day load) − min(day load)` over configured days | `add_max_equality` / `add_min_equality` on per-day sums of `group_busy` |
| `parallel_batch_labs` | One batch busy while its sibling is idle, leaving the parent group fragmented | per parent/day/period: `any_batch_busy − all_batches_busy` | `max_equality` / `min_equality` over sibling `group_busy` |
| `room_size_fit` | Oversized room for the group | `floor((room capacity − group size) / waste_unit)` per session | Per-candidate constant cost |
| `faculty_compact_days` | Faculty spread over many days | per faculty: number of days with any class | `day_used[f,d]`; note this pulls against S11 and `faculty_daily_load`, so keep weight low |
| `consistent_subject_time` | Subject starts at different periods across the week | per subject/group: `distinct start periods − 1` | `start_used[s,g,p] = max(candidates)` |
| `faculty_daily_load` | Too many teaching periods in one day (all subject types; S11 covers lectures only) | per faculty/day: `max(0, periods − max_periods)` | On `faculty_busy` sums |
| `online_at_day_edges` | An online session sandwiched between in-person classes | 1 per online session with in-person class before and after it that day | Prefix/suffix of in-person occupancy for the group |
| `faculty_preferred_day_off` | Classes on a faculty member's preferred day off | 1 per occupied period on that day | New nullable column `faculty.preferred_day_off`; per-candidate constant |
| `stability_vs_previous` | Re-solve moves sessions that were already placed | 1 per session whose (day, start period) differs from the previous timetable; optional extra if the room differs | Per-candidate constant; also feed the previous timetable as a CP-SAT solution hint |

### D2. Objective assembly

- Objective = Σ (weight × penalty) over enabled soft constraints and flexible constraints in soft mode.
- Keep each penalty as a named IntVar so its value can be reported.
- Optional later: lexicographic mode (solve for top priority, fix its value as a bound, then solve the next).

---

## Phase E: Validation, reporting, exports

### E1. Independent validator covers every hard rule

Extend `validator.py` / `hard_constraints.py` to check, without using solver variables:

- faculty overlap, student-population overlap (**pass the parent map**; `run_timetable.py` currently calls `validate_timetable(result.timetable)` without it), room overlap
- room type, capacity, online/in-person rules
- blocked slots (global and group), locks
- weekly cap / minimum, daily span
- enabled optional hard constraints (lunch in hard mode, max consecutive in hard mode, role restrictions)

The validator's pairwise loop is fine at this size, but grouping by (resource, day) is cheap to do now.

### E2. Score report

After solving, print a table: constraint key, mode, weight, raw penalty from the independent calculator, weighted penalty, and penalty from the solver variable. Flag any mismatch between solver and calculator (this catches modelling bugs). Also write `output/score_report.json` and add a "Summary" sheet to the master workbook.

### E3. Export fixes

- `export_faculty_workbook` crashes with "At least one sheet must be visible" when there are no entries. If the workbook would have no sheets, create one "No sessions" sheet. Apply the same guard to every exporter.
- Add a grid-style export (days × periods per group, per faculty, per room), since that's the format people print.

---

## Phase F: Structural changes (separate phase, plan before coding)

- **Combined classes / electives:** association table `assignment_groups` so one assignment has several academic groups. Session conflict keys become the union of their leaf populations; room capacity uses the sum of group sizes.
- **Multiple faculty per session:** association table `assignment_faculty`; faculty conflict keys become the union.
- **Open-elective blocks:** a set of assignments that must run in the same slot.

---

## Phase G: Cleanup

- Remove dead `_calculate_faculty_workloads` in `run_timetable.py`; replace the `type("FacultyWorkload", ...)` hack with a small dataclass.
- Merge `app/db/seed.py` and `scripts/seed_sample_data.py` into one seed (keep the 80-assignment version that the integration test expects).
- Update README and README_DEV (they still say optimisation is not implemented).
- Delete stale `output.txt`; add `output/` to `.gitignore`.
- Distribute the project without `.venv` (it made the zip about 300 MB).

---

## Testing and acceptance criteria

1. **Per constraint:** a tiny instance where enabling the constraint changes the chosen timetable, and a test that the independent calculator matches the solver's penalty variable.
2. **Toggles:** with every optional hard and soft constraint disabled, the seeded problem is still feasible. With a constraint disabled, the model contains none of its variables.
3. **Flexible modes:** for lunch and max-consecutive, test off / soft / hard on a small instance that forces a difference.
4. **Config:** invalid keys, unknown periods and negative weights produce clear errors.
5. **Validator:** a deliberately broken timetable triggers each hard-rule failure type.
6. **Performance:** seeded solve runs on a 4 GB machine; report peak memory and time.
7. **Before/after report on seed data:** student gaps (baseline 102), same-day subject repeats (baseline 21), sessions across lunch (baseline 7), sessions in P8, faculty gaps, room changes per group-day.

## Suggested implementation order

1. Phase A (all of it), then confirm the seeded solve works with `minimize` enabled.
2. Phase B config framework, moving existing constraints into it with unchanged behaviour.
3. HC-1 lunch, `avoid_periods` (P8), D0 fixes, E1 validator, E3 export fix.
4. Remaining Phase D soft constraints, highest value first: `faculty_gaps`, `room_stability`, `parallel_batch_labs`, `subject_day_spacing`, `group_daily_load_balance`, then the rest.
5. HC-3, HC-5, HC-6 (database-backed: availability, group blocks, locks), then HC-2, HC-7, HC-8, HC-9.
6. E2 score report, Phase G cleanup.
7. Phase F as a separately planned piece of work.
