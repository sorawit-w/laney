# Architect reviews (adversarially)

## Purpose

Adversarial review of the real diff: attempt to refute the work against the
plan and acceptance criteria. A finding that survives your own check feeds
the fix phase; the mechanical checks come after. The stance is fixed — the
implementer's notes are claims, not evidence.

## Instructions

Review the current git diff together with the artifacts below. On loop
iteration 2 and later, also read the newest `test-output-<n>.fail.md` in the
run directory — the judge's failing evidence is the sharpest input you have.

Work three refutation lenses in order; each is a distinct way the work could
be wrong:

1. **Spec contradiction** — check the diff against `plan`, `acceptance`, and
   `context`'s must-not-change list. Hunt code bent to satisfy a check that
   contradicts the spec, and changes beyond the ask (drive-by refactors,
   reformat noise, new dependencies the notes never mention).
2. **Runtime / behavioral break** — look for an input, path, or edge the
   change breaks. Diff the test files specifically: assertions loosened,
   expected values changed to match new behavior, tests skipped or narrowed.
3. **Claim verification** — treat `impl-notes` as claims. Anything claimed
   done, verified, or untouched that the diff or run evidence cannot support
   is a finding, not a footnote.

Classify every finding that survives your own check:

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
- `impl-notes`: what the implementer says changed and deferred — claims to
  verify, not facts to trust.

## Done means

`review-<n>.md` opens with a verdict line (BLOCKED / GREEN WITH NITS / GREEN),
lists findings by class with why + suggested fix, checks off acceptance
criteria item by item, and names test gaps. GREEN with nothing to fix is a
valid, explicit outcome — it means the work survived refutation, not that
refutation was skipped.
