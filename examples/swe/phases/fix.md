# Implementer fixes

## Purpose

Resolve the review's findings — and only those. The mechanical checks run
right after this phase.

## Instructions

- Fix the BLOCKER and SHOULD FIX items from the review below. Leave NITs
  unless trivial.
- Do not rewrite unrelated code. Preserve the original plan unless the review
  proves it wrong.
- Update tests if behavior changes.
- If the review verdict is GREEN with nothing actionable, make no code
  changes and record that.
- Write `fix-plan.md` into the run directory: what was fixed, what was
  deliberately not fixed and why.

## Inputs

- `review`: this iteration's findings (the engine hands you the current one).
- `acceptance`: the definition of done, for context.

## Done means

`fix-plan-<n>.md` accounts for every BLOCKER and SHOULD FIX item — fixed, or
explicitly declined with a reason. "No changes needed — review was GREEN" is
a valid entry.
