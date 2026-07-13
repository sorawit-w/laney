# `workflows create` — the interactive authoring walkthrough

Follow this end-to-end when dispatching `laney workflows create`. The flow is
an interview: the user owns every decision; the engine supplies structure,
validation, and honest pushback. **The engine never suggests a tool name** —
binding strings come from the user, always.

Ground truth for every field: `docs/workflow-contract.md` in the laney repo.
The templates under `resources/templates/` are the skeletons to fill in.

## Step 1 — Interview

Ask, one at a time:

1. **What work does this workflow run?** (domain + purpose, a sentence or two)
2. **id** — a slug (validator-checked, W04). It becomes a folder and path
   component.
3. **description** — one line, shown in `workflows list`.
4. **Where should the folder go?** Default `./<id>/`; confirm before writing
   anything.

Then sketch the shape back to the user before descending into fields: "so the
loop is roughly: X drafts, Y checks, Z fixes — right?" A wrong shape caught
here saves the whole walkthrough.

## Step 2 — Roles

For each role slot the user names:

- **name** — a slug; `human` and `judge` are reserved and never declared
  (remind the user: human steps are phases with `owner = "human"`, the checker
  is `[judge]`).
- **mode** — `native` (the loaded AI session does the phase) or `invoke` (a
  CLI the engine runs).
- For `invoke`: the **command binding** — supplied by the user verbatim.
  Placeholders available: `{prompt_file}`, `{run_dir}` (nothing else, W12).
  Plus **capture** — `stdout` (engine captures output into the first written
  artifact) or `files` (the tool writes artifacts into `{run_dir}` itself) —
  and optional `timeout_seconds` (default 600).

## Step 3 — Artifacts

Walk the handoff files before the phases (phases reference them):

- **id** (slug) and **file** (bare filename — artifacts live in the run dir).
- **template** — optional; draft it *with* the user into `templates/` when
  they want a scaffold.
- **versioned** — explain the rule once: anything written inside the fix loop
  (and the judge's evidence) must be versioned; the ordinal suffix is the loop
  counter. The validator enforces it (W13), so declare honestly.

Keep artifacts small — invoke prompts inline their full contents.

## Step 4 — Phases

In execution order, for each phase:

- **id**, **owner** (a declared role, `human`, or `judge`), **reads**,
  **writes** (non-empty — even an approval phase writes an approval artifact;
  artifact presence is the engine's only state).
- **body** — draft it *with* the user into `phases/<id>.md` using
  `templates/phase-body.md.template` as the skeleton. A good body states:
  purpose, the instructions the owner follows, and what "done" looks like for
  each written artifact. The judge phase takes **no** body.

## Step 5 — Judge

If the workflow has a mechanical check (recommended whenever "done" is
verifiable):

- **commands** — script names/relative commands resolved against the consuming
  repo at run time. Warn the user these are *not* checked at authoring time —
  a missing script HELDs the run when the judge fires.
- **evidence** — which declared, versioned artifact receives the verdict.
  The judge phase's `writes` must include it.
- **max_fix_loops** — the cap (the source doc tradition: 2–3).
- **on_fail** — the phase the loop re-enters; must precede the judge.

## Step 6 — Validate continuously, emit, offer a test load

- Run the validator after **every** addition, not once at the end:
  `python3 <install-root>/resources/scripts/validate-workflow.py <dir>`.
  Surface W-codes fix-forward (they are written to be actionable). Show every
  W11 injection-lint hit to the user verbatim.
- Emit the folder: `workflow.toml`, `phases/`, `templates/` (as declared), and
  a short `README.md` (purpose, roles table, phase list, provenance).
- Offer a test load (`laney load ./<id>`) — creating a workflow is not
  loading it; the ordinary load flow (validation, hash, pin) still applies.

`create` writes only inside the new workflow folder. Nothing else on disk is
touched.
