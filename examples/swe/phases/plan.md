# Architect plans

## Purpose

Turn the context into an implementation plan and an acceptance checklist the
rest of the run is judged against. Plan only — no production code edits.

## Instructions

Read `context.md`, inspect the relevant code in the repo, then produce the
two artifacts. Rules:

- Prefer the smallest safe change.
- Identify the files likely to change and why.
- Include a test strategy using the repo's check commands from `context.md`.
- Call out unclear requirements instead of guessing — an open question in the
  plan is cheaper than a wrong implementation.

## Inputs

- `context`: goal, behaviors, constraints, risks, check commands.

## Done means

- `plan.md`: summary, numbered approach, files likely to change (with why),
  data/API contract changes (or "none"), UX changes (or "none"), risks with
  mitigations, and a test plan naming the repo's check commands.
- `acceptance.md`: a checkbox list defining done — target behaviors, existing
  behavior preserved, empty/loading/error states handled, tests added or
  updated, checks passing.
