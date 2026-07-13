# laney

**laney runs step-by-step AI workflows from a written playbook.**

You describe how a piece of work should flow — who plans, who builds, who
checks, where a person decides — and laney keeps its finger on the current
step: it runs each phase with whatever tool the playbook names, saves every
step's output as plain files, verifies "done" with real commands, and stops to
ask a human at exactly the points you said it should.

Think of it as a game console and cartridges: **laney is the console** — it
ships empty and has no opinion about your work or your tools. **A workflow is
the cartridge** — a small folder that says what the steps are, which tool (or
person) owns each one, and what proves the work is actually done.

## What it looks like

```
you>  laney next

laney> Phase `implement` (owner: builder) ran.
       Wrote: .laney/runs/2026-07-13-login-fix/implementation-notes.md
       Next up: `check` (judge) — run `laney next` to judge.

you>  laney next

laney> Judge iteration 1: 2 commands run, 1 failed.
       Wrote: test-output-1.fail.md
       The loop re-enters `implement` (fix 1 of 3). Run `laney next`.
```

Every step reads and writes files in a **run folder** — no chat memory, no
hidden state. If you looked away for a week, `laney status` tells you exactly
which phase the run is on, because the files *are* the state.

## What's in a workflow

A workflow is a folder with a manifest (`workflow.toml`) declaring four
things:

| Piece | What it is |
|---|---|
| **Roles** | Named slots — "planner", "builder" — each bound to a tool: either the AI session you're in (`native`) or any CLI you name (`invoke`). The binding string is yours; laney never picks a tool for you. |
| **Phases** | The ordered steps. Each says who owns it and which files it reads and writes. A phase can also be owned by `human` (you) — laney sets up the file and waits. |
| **Artifacts** | The handoff files each phase produces — the ground truth that travels between tools. |
| **Judge** | Real commands that decide pass/fail. If they fail, the flow loops back to a fix phase — at most N times, then it's your call. An AI saying "looks good" is never the green light. |

## What laney does

- Loads a workflow and pins it to your project, so every session agrees on
  the playbook.
- Tells you what's next, one phase per step — you stay in the driver's seat.
- Runs each phase with the tool the workflow names, handing it exactly the
  files it should see.
- Keeps every output in `.laney/runs/<date>-<name>/` — a durable, inspectable
  record of how the work went.
- Judges with real commands and stops after too many failed fix loops.

## What laney doesn't do

- **Ship workflows** — v1 includes none. You write your own (there's an
  interactive builder: `laney workflows create`) or load one from a folder.
- **Choose your tools** — the engine never names one. If a workflow is missing
  a binding, laney asks you.
- **Guard your code** — laney sequences work; it doesn't police it. For rules,
  gates, and guardrails, see its sibling [kerby](https://github.com/sorawit-w/kerby).
  The two compose: a workflow's judge can run whatever checks kerby (or
  anything else) provides.
- **Run in the background** — no hooks, no automation. laney acts only when
  you invoke it.

## When to use it

**Good fit:** work with a real sequence, more than one tool or person, and a
checkable outcome — a feature that flows plan → build → test → review → fix,
a document that flows draft → fact-check → edit → approve, an asset pipeline
that flows brief → generate → pick → integrate.

**Skip it for:** one-shot tasks, or work where nothing can be run to say
pass/fail — a workflow without a real check is just a fancy checklist.

## How a run works

```
.laney/runs/2026-07-13-login-fix/
├── context.md              ← you wrote this (human phase)
├── plan.md                 ← the planner role wrote this
├── implementation-notes.md ← the builder role wrote this
├── test-output-1.fail.md   ← the judge: first check failed…
├── test-output-2.pass.md   ← …second check passed after one fix loop
└── approval.md             ← you again — the run is complete
```

The judge's verdict is in the **filename**, and numbered files count the fix
loops. When the final phase's files exist, the run is complete. Start the next
run and the folder sticks around as the record.

## Commands

| Command | What it does |
|---|---|
| `laney load <path>` | Load a workflow from a folder and pin it to the project. |
| `laney next` | Run the current phase of the active run (or start a run). |
| `laney status` | Show what's loaded and exactly where the active run stands. |
| `laney workflows list` | List the workflows this install can see. |
| `laney workflows create` | Interactive builder: author a new workflow, validated as you go. |
| `laney unload <id>` | Remove a workflow from the project's selection. |
| `laney install` | Add a session-start line to your project's agent file (asks per file). |
| `laney commands` | This table. |

## Install

As a Claude Code plugin:

```
/plugin marketplace add sorawit-w/laney
/plugin install laney@laney
```

Or copy the skill folder directly: `skills/laney/` → `~/.claude/skills/laney`
(global) or `<project>/.claude/skills/laney`. Then, inside a project,
`laney install` offers the session-start line and the `.gitignore` entry for
laney's machine-local pin file.

Requires Python ≥ 3.11 on the machine (the workflow validator is a single
stdlib-only script; no packages to install).

## Writing your own workflow

The fast path is `laney workflows create` — an interview that asks about your
roles, steps, files, and checks, validates after every answer, and emits the
folder. The full references:

- [docs/AUTHORING-WORKFLOWS.md](docs/AUTHORING-WORKFLOWS.md) — the narrative guide.
- [docs/workflow-contract.md](docs/workflow-contract.md) — the normative schema.

## Status

**v0.1.0 — alpha.** Engine only, manifest contract 1. Deliberately not in v1:
bundled workflows, remote workflow fetching, trust prompts for shared
workflows (the pin detects changes; a first-trust approval flow is planned),
and lifecycle hooks. The contract doc marks what's reserved.

## License

MIT.
