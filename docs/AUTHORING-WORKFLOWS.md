# Authoring laney workflows

How to write a workflow the laney engine can load, step, and judge. The
normative schema lives in [workflow-contract.md](workflow-contract.md) — this
guide is the narrative version. The fastest path is interactive:
`laney workflows create` walks you through everything below and validates as
you go.

## When a workflow makes sense

Write one when the work is:

- **Multi-step** — it has a real sequence (draft → check → fix → approve), not
  a single prompt.
- **Multi-tool or multi-party** — different steps belong to different AIs,
  CLIs, or people, and they can't share chat memory.
- **Verifiable** — some command can actually say pass/fail, so "done" isn't a
  feeling.
- **Repeated** — you'll run the same shape again next week and don't want to
  re-explain it.

One-shot tasks don't need a workflow. Neither does work with no checkable
outcome — laney's judge is its spine; a workflow without one is just a
checklist.

## Folder structure

```
my-workflow/
├── workflow.toml        # the manifest — the single authority for what exists
├── OVERVIEW.md          # optional `body`: read into context at load
├── phases/              # one prose file per phase (except the judge)
│   ├── plan.md
│   └── review.md
└── templates/           # optional artifact scaffolds
    └── plan.md
```

Everything is declared in `workflow.toml` by relative path, confined to the
folder: no absolute paths, no `..`, no symlinks, no `.git/` (W04). A workflow
is self-contained plain files.

## The manifest, walked through

Start from `resources/templates/workflow.toml.template` in the skill bundle.

### Top level

```toml
id = "my-workflow"     # slug; becomes a folder/path component
version = "0.1.0"
contract = 1
description = "One line for `workflows list`."
body = "OVERVIEW.md"   # optional; read eagerly at load
```

### Roles — who does the work

A role is a slot, and the binding is yours:

```toml
[roles.planner]
mode = "native"        # the loaded AI session performs these phases

[roles.builder]
mode = "invoke"        # the engine runs a CLI
command = "your-tool --file {prompt_file}"
capture = "files"      # the tool writes artifacts into {run_dir} itself
timeout_seconds = 900
```

- `native` — no binding needed; the session that loaded laney does the phase.
- `invoke` — `command` is run via the shell. The engine substitutes exactly
  two placeholders: `{prompt_file}` (the composed prompt: phase body + full
  contents of every input artifact + the writes contract) and `{run_dir}`.
  `capture = "stdout"` writes the command's output into the phase's first
  artifact; `capture = "files"` expects the tool to write the artifacts
  itself, and the engine verifies each exists and is non-empty.
- Two owner names are reserved and never declared as roles: **`human`** (a
  person does the phase — the engine scaffolds and stops) and **`judge`** (the
  mechanical checker, configured by `[judge]`).

**Choosing a mode:** if the tool has a CLI, prefer `invoke` — the handoff is
reproducible and the prompt file is a durable record. Use `native` for work
the loaded session is genuinely best at (or when there's no CLI). If a step
needs judgment only a person should exercise (approvals, selections), that's
not a role — it's a `human` phase.

### Artifacts — the handoff files

```toml
[[artifact]]
id = "plan"
file = "plan.md"
template = "templates/plan.md"   # optional scaffold

[[artifact]]
id = "test-output"
file = "test-output.md"
versioned = true                 # REQUIRED for loop-written artifacts + evidence
```

Artifacts are the *only* state: the engine infers the current phase from which
files exist in the run directory. That drives two rules:

- Every phase **writes at least one artifact** — even a human approval phase
  writes an `approval.md`; otherwise the engine can't see it happened.
- Anything written inside the fix loop is **versioned**: it materializes as
  `plan-1.md`, `plan-2.md`, … and the ordinals are the loop counter. The
  validator enforces this (W13) because an unversioned loop artifact would
  overwrite itself and make the loop count unrecoverable.

Keep artifacts small — an invoke phase's prompt inlines the full contents of
everything it reads.

### Phases — the ordered steps

```toml
[[phase]]
id = "plan"
owner = "planner"
body = "phases/plan.md"
reads = []
writes = ["plan"]

[[phase]]
id = "check"
owner = "judge"        # no body — the judge is mechanical
reads = ["plan"]
writes = ["test-output"]
```

Declaration order is execution order. A phase runs when its `reads` all exist
and its `writes` don't yet. Write each body (`phases/<id>.md`) for its owner:
a native body instructs the AI session; an invoke body ends up inside a CLI's
prompt; a human body is read by a person. The skeleton in
`resources/templates/phase-body.md.template` (purpose / instructions / inputs /
done-means) keeps bodies honest.

### The judge — mechanical, never an AI

```toml
[judge]
commands = ["scripts/run-checks.sh"]
evidence = "test-output"
max_fix_loops = 3
on_fail = "plan"
```

- `commands` resolve against the **consuming repo** at run time — the
  validator can't check they exist; a missing command HELDs the run.
- The verdict is pass iff every command exits 0, and it's written **into the
  evidence filename**: `test-output-1.fail.md`, `test-output-2.pass.md`. No
  file needs to be opened to know where the run stands.
- On fail, the run re-enters `on_fail` — at most `max_fix_loops` times, then
  the engine stops and hands the decision to a person. Pick a small cap (2–3):
  repeated failure usually means unclear requirements, not a fixable slip.

## Design advice

- **Design the loop first.** Which phase gets re-entered on failure, and what
  does the fixer get to see? (Usually: the failing evidence — have the re-run
  phase `read` the evidence artifact.)
- **One primary implementer per loop.** Two tools fighting over the same
  artifact produce churn, not quality.
- **Make "done" a command, not an opinion.** If nothing can be run to check
  the work, the judge degrades into theater; reshape the work until something
  is runnable, even if it only checks shape (file exists, has N sections,
  compiles).
- **Human phases are cheap — use them at real decision points** (approvals,
  selections between candidates), not as vibes-checkpoints between every step.

## Validate and ship

```bash
python3 <install-root>/resources/scripts/validate-workflow.py ./my-workflow
python3 <install-root>/resources/scripts/validate-workflow.py ./my-workflow --hash
```

Pre-ship checklist:

- [ ] Validator exits 0; every warning read and either fixed or accepted.
- [ ] Every phase body says what "done" looks like for each artifact it writes.
- [ ] Judge commands actually exist in the repos this workflow will run in.
- [ ] Loop-written artifacts are versioned; the cap is small.
- [ ] A test load (`laney load ./my-workflow`) announces the right id/version
      and phase count.
