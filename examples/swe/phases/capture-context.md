# Context capture

## Purpose

Create the smallest useful task context before any model plans. You are the
product owner — this file is the one place your intent enters the run.

## Instructions

Fill in `context.md` in the run directory (scaffolded from the template).
Keep it short and concrete:

1. State the goal in one paragraph — feature, bug, or refactor.
2. Describe current behavior and desired behavior separately.
3. List constraints: stack, files likely involved, what must not change,
   compatibility and UX requirements.
4. Name the known risks.
5. Confirm the check commands are real for this repo — the judge will run
   them verbatim and a missing script holds the run.

## Done means

`context.md` answers: what are we building, what does done look like, what
must not break, and which commands prove it.
