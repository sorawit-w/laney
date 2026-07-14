# Architect reviews

## Purpose

Strict, scoped review of the real diff against the plan and acceptance
criteria. Findings feed the fix phase; the mechanical checks come after.

## Instructions

Review the current git diff together with the artifacts below. On loop
iteration 2 and later, also read the newest `test-output-<n>.fail.md` in the
run directory — the judge's failing evidence is the sharpest input you have.

Classify every finding:

- **BLOCKER** — fix before merge.
- **SHOULD FIX** — important, not necessarily blocking.
- **NIT** — optional cleanup.

Focus on correctness, missed acceptance criteria, regressions, bad
abstractions, type safety, UX edge cases, and test gaps. For UI-heavy work,
check that an E2E or smoke pass is planned or done — the judge does not run
E2E. Stay scoped: do not ask for broad rewrites unless a real flaw demands it.

## Inputs

- `context`: constraints and must-not-change list.
- `plan`: what was supposed to happen.
- `acceptance`: the definition of done — check each item explicitly.
- `impl-notes`: what the implementer says changed and deferred.

## Done means

`review-<n>.md` opens with a verdict line (BLOCKED / GREEN WITH NITS / GREEN),
lists findings by class with why + suggested fix, checks off acceptance
criteria item by item, and names test gaps. GREEN with nothing to fix is a
valid, explicit outcome.
