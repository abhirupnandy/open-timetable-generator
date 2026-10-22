# S4 — Subject Spreading

## Status

Planned

## Priority

High

## Type

Soft constraint

## Purpose

Spread repeated sessions of the same subject for the same academic
group across different timetable days.

The objective is to avoid unnecessarily placing multiple weekly
sessions of the same subject on the same day.

## Scope

The constraint applies independently to:

- subject
- academic group

Lab batches are treated according to their own academic-group/session
identity.

Sibling batches are not combined for this calculation.

## Rule

For each subject and academic group:

- The first session placed on a particular day has no penalty.
- Each additional session of the same subject for the same academic
  group on that day incurs a penalty.

## Examples

### Preferred

Subject: Mathematics

Monday:
- Mathematics

Wednesday:
- Mathematics

Friday:
- Mathematics

Penalty: 0

### Penalised

Subject: Mathematics

Monday:
- Mathematics
- Mathematics

Thursday:
- Mathematics

Penalty: 1

### Maximum concentration

Subject: Mathematics

Monday:
- Mathematics
- Mathematics
- Mathematics

Penalty: 2

## Mathematical formulation

For each:

(subject, academic_group, day)

let:

    n(subject, group, day)

be the number of sessions of that subject for that group
scheduled on that day.

The penalty is:

    max(0, n(subject, group, day) - 1)

The total S4 penalty is:

    S4 = sum max(0, n(subject, group, day) - 1)

The solver minimises S4 as part of the weighted soft-constraint
objective.

## Hard-constraint interaction

S4 must never override a hard constraint.

A timetable with:

- zero S4 penalty

but a hard conflict

is invalid.

A timetable with:

- non-zero S4 penalty
- zero hard conflicts

is valid, but less desirable.

## Expected behaviour

The solver should prefer:

    Monday + Wednesday + Friday

over:

    Monday + Monday + Friday

when both schedules satisfy all hard constraints.

However, S4 may be violated when doing so is necessary to satisfy
higher-priority constraints or when avoiding the violation would
create a worse overall soft-constraint score.

## Weight

Initial weight:

    80

This is a calibration value and may be changed after observing
real generated timetables.

## Validation

The implementation must provide:

1. Unit tests for S4 penalty calculation.
2. A solver-level test showing that S4 influences the selected
   timetable when alternative feasible placements exist.
3. Regression confirmation that all existing hard constraints remain
   satisfied.
4. Comparison with the Phase-1 baseline.

## Baseline

Before S4:

- Sessions: 173
- Scheduled: 173/173
- Hard conflicts: 0
- S1: 0
- Solver runtime: approximately 192 seconds

After S4:

- Sessions: 173
- Scheduled: 173/173
- Hard conflicts: 0
- S1: measure
- S4: measure
- Solver runtime: measure

## Acceptance criteria

S4 is considered implemented when:

- all existing tests pass;
- S4 unit tests pass;
- the solver still schedules all 173 sessions;
- hard validation reports zero conflicts;
- S4 penalty is measurable;
- the generated timetable demonstrates that S4 is actually
  influencing scheduling rather than merely being calculated after
  the solve.