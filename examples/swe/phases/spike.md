# Specialist spike (no-edit)

## Purpose

A parallel second opinion on the plan before implementation starts — strongest
on Google/Gemini/Cloud, browser/runtime questions, and API pattern checks.
Exploration only: do not edit any files.

## Instructions

Read the context and plan below, then decide:

- If this task touches your specialty (Google Cloud, Firebase, BigQuery,
  Gemini API, Google auth, Android, browser runtime behavior) or the plan has
  an open question a quick spike can settle: explore, then report
  - the recommended approach and its risks,
  - files likely affected,
  - anything the current plan missed,
  - whether the plan is worth changing (be explicit: yes/no and why).
- Otherwise reply with exactly one line: `skipped: not applicable — <reason>`.

Do not edit files either way. Your reply is captured verbatim as the spike
artifact.

## Inputs

- `context`: goal, constraints, risks.
- `plan`: the approach to second-guess.

## Done means

`spike.md` contains either a concrete recommendation with a clear
change-the-plan verdict, or the explicit skip line — never silence.
