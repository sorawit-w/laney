# Workflow contract — v1

The manifest contract between the laney engine (loader/validator/executor) and
a **workflow** — a folder describing how a piece of multi-step, multi-tool work
gets done, which the engine can load, step through, and judge **without knowing
the domain**. One fixed filename: `workflow.toml` at the workflow root;
everything else the workflow contains is declared in the manifest by relative
path. **The manifest is the single authority for what a workflow contains — the
engine never guesses filenames.**

Mechanical validation:

```bash
python3 skills/laney/resources/scripts/validate-workflow.py <workflow-dir>
```

(requires Python ≥ 3.11 for stdlib `tomllib`; the validator has no third-party
imports). The validator ships inside the skill bundle so the `load` flow can
invoke it wherever the skill is installed.

## Contract evolution

The standing rule (adopted from kerby's contract doctrine): *new optional
fields are contract-1-compatible; requiring a field, reshaping an existing one,
or removing one forces v2.* The engine rejects manifests declaring an
unsupported `contract` (W03).

## Purpose and the zoning rule

The engine's promise: it loads, steps through, and judges workflows *without
knowing the domain*. Enforceable in review with one rule:

**Engine surfaces** (`skills/laney/SKILL.md`, `skills/laney/resources/**`, and
the repo's root `scripts/`) **must never name a concrete tool** (no coding
agent, no package manager, no image model — no tool names at all) **and may
name a specific workflow only as a worked example or bundle contents.** Every
behavior-bearing branch consumes contract fields (`[roles]`, `[[phase]]`,
`[[artifact]]`, `[judge]`); deleting any workflow folder leaves the engine
mechanically intact — the **delete-the-workflow drill** is a release-checklist
item. Tool bindings are data (`[roles.<name>].command` strings), owned entirely
by workflows. If a workflow is missing a binding, the engine asks — it never
fills in a default tool.

## Origins and trust

| Origin | Where it lives | Path rules | Trust (v1 posture) |
|---|---|---|---|
| `builtin` | `<install-root>/workflows/<id>/`, ships inside laney | folder-confined like every origin | install-trusted; `sha256: null` in the pin. **Builtin trust is anchored to the install, never granted by a lockfile**: an entry claiming `origin: builtin` counts only if its `id` resolves to `<install-root>/workflows/<id>` and its `path_or_url` is that install path. The validator rejects `--origin builtin` for any path outside `--builtin-root` (W04). *The builtin set is empty in v1 — the mechanism ships anyway.* |
| `local` | anywhere on disk, loaded by explicit `load <path>` | confined: every declared path resolves **inside** the workflow root — no `..`, no absolute paths, **no symlinks and no `.git/` anywhere under the folder** (W04). A workflow must be self-contained plain files | hash-pinned change detection (below) |
| `remote` | *reserved — not in v1* | — | — |

**v1 trust posture, stated plainly:** the pin's `sha256` is a **change
detector, not an approval record**. On load, a hash matching the pin loads
silently; an unknown or changed hash re-runs the validator, announces
`content changed — re-pinning`, and re-pins **after the user confirms**. There
is no TOFU approval prompt and no per-machine approval store in v1. The
deliberate consequence: a freshly cloned repo's committed lockfile is treated
as local state, and the upgrade path — TOFU prompt + user-local approval store,
so a committed lockfile can never pre-approve external instructions — is
specified by kerby's rulebook contract (`docs/rulebook-contract.md` in the
kerby repo, § Origins and trust) and is the planned v2 posture. Until then:
**workflow prose enters context framed as data, not directives** — phase bodies
are steps to follow within the user's intent, never instructions that override
the user or the engine.

## Top-level manifest fields

```toml
id = "swe"                  # unique workflow id: strict slug (required — it
                            #   becomes a path component)
version = "1.0.0"           # the workflow's own semver (required)
contract = 1                # manifest contract version (required; W03)
description = "…"           # one line for `workflows list` (required)
body = "OVERVIEW.md"        # optional prose read eagerly at `load` — the
                            #   workflow's own summary/operating notes
```

**Reserved keys** — declared today, honored later; declaring them at contract 1
is a warning (W15) and they are ignored: `extends`, `[detect]`, `[[command]]`,
`[identity]`. Any other unknown key also warns (W15).

## `[roles.<name>]` — role slots and tool bindings

A role is a named slot a phase can be owned by. Role names are free slugs, with
two **reserved owner names that must never be declared as roles** (W05):
`human` (the person driving) and `judge` (the mechanical checker — configured
by `[judge]`, not `[roles]`).

| Field | Type | Semantics |
|---|---|---|
| `mode` | `"native"` \| `"invoke"` (required) | `native`: the loaded AI session itself performs the phase. `invoke`: the engine runs `command` as a CLI via the shell |
| `command` | string | required iff `mode = "invoke"`, forbidden for `native` (W05). The binding string — entirely workflow-owned; this is the only place a tool name may appear. Placeholder vocabulary (exhaustive — anything else is W12): `{prompt_file}` (absolute path to the engine-composed prompt file), `{run_dir}` (absolute path to the active run directory) |
| `capture` | `"stdout"` \| `"files"` | required iff `mode = "invoke"` (W05). `stdout`: the engine writes the command's captured stdout into the phase's first `writes` artifact. `files`: the prompt instructs the tool to write the declared artifacts into `{run_dir}` itself; the engine then verifies each exists **and is non-empty** (content quality is the judge's job, not the capture check's) |
| `timeout_seconds` | int | optional, default `600`. On timeout or non-zero exit: **report and stop for the human — never auto-retry** |
| `description` | string | optional, for `status`/`list` rendering |

## `[[phase]]` — ordered steps

Declaration order is execution order.

| Field | Type | Semantics |
|---|---|---|
| `id` | slug | unique among phases (W07) |
| `title` | string | optional |
| `owner` | string | a declared role name, or reserved `"human"` / `"judge"` (W05) |
| `body` | path | folder-confined prose the owner follows (W04). Required for every owner **except** `judge`, where it is forbidden (W06) — the judge is mechanical and takes no instructions |
| `reads` | array of artifact ids | inputs; every entry must name a declared artifact (W08) written by some earlier phase (W09; loop re-entry counts) |
| `writes` | array of artifact ids | outputs; **required and non-empty** (W08) — artifact presence is the engine's only state, so even a human approval phase writes an artifact |

## `[[artifact]]` — the handoff files

| Field | Type | Semantics |
|---|---|---|
| `id` | slug | unique among artifacts (W07) |
| `file` | string | the filename materialized inside the run directory (e.g. `plan.md`) |
| `template` | path | optional, folder-confined (W04): copied into the run dir as a scaffold when the writing phase starts (for a human-owned phase the engine scaffolds it and tells the human the path — it never writes content as the human) |
| `versioned` | bool | default `false`. A versioned artifact materializes as `<stem>-<n><ext>` (`review-1.md`, `review-2.md`). **Required `true`** for the judge's `evidence` artifact and for any artifact written by a loop-reachable phase (W13) |
| `description` | string | optional |

No two phases may write the same artifact unless it is `versioned` and both
phases are loop-reachable (W10).

## `[judge]` — the mechanical checker

Present **iff** exactly one phase has `owner = "judge"` (W06).

| Field | Type | Semantics |
|---|---|---|
| `commands` | non-empty array of strings | commands resolved **against the consuming repo root at run time** — never assumed to exist. A missing/unresolvable command at run time means the judge cannot run: the run is **HELD** for the human — not a pass, not a fail. Relative paths/names only (absolute paths warn, W14) |
| `evidence` | artifact id | must name a declared, `versioned = true` artifact (W06) |
| `max_fix_loops` | int ≥ 1 | the loop cap |
| `on_fail` | phase id | the phase re-entered on a failing verdict; must precede the judge phase (W06) |

The judge is never an AI: a verdict comes only from real command exit codes.
The engine must never fabricate, summarize into existence, or "reasonably
infer" judge evidence.

## Verdict and fix-loop naming (normative — the statelessness keystone)

The engine keeps **no state file**. Run position is inferred from artifact
presence alone, so verdicts must be legible to a glob:

- Judge iteration *n* runs every `[judge].commands` entry from the consuming
  repo root, concatenates the raw output, and writes the evidence artifact as
  `<stem>-<n>.pass<ext>` or `<stem>-<n>.fail<ext>` (e.g.
  `test-output-1.fail.md`). **The verdict is encoded in the filename** — the
  alternative (a header line inside the file) is explicitly rejected: inference
  must never require reading file contents.
- Verdict = **pass iff every command exits 0**.
- Current iteration = (max *n* among existing evidence versions) + 1; loop
  count needs no counter because the evidence files *are* the counter.
- Every versioned artifact written inside the loop uses the same `-<n>` ordinal
  as the judge iteration that follows it.
- Terminal states: any `.pass` evidence → the judge phase is complete, the run
  proceeds. A `.fail` at *n* ≥ `max_fix_loops` → the run is **loop-exhausted**:
  the engine stops and reports to the human; it never silently continues.

## Run-state model

Project state lives in the consuming repo under `.laney/`:

```
.laney/
  workflows.lock            # the pin (below)
  runs/<YYYY-MM-DD>-<slug>/ # one directory per run; artifacts live here
  workflows/<id>/           # reserved for external materialization (post-v1)
```

- **One active run.** The active run is the lexicographically greatest run
  directory that is not complete. Starting a new run while one is incomplete
  requires explicit confirmation. A run is **complete** when the final phase's
  `writes` are all present, or when it is loop-exhausted and the human closed
  it.
- **Run slug:** the engine asks when starting a run (workflows never bake one
  in).
- **Phase inference:** the current phase is the first phase, in declared order,
  whose `writes` are not all present **and** whose `reads` are all present. If
  a phase's reads are missing while a later phase's writes exist, the run is
  corrupted (hand-edited): **report, never guess.** For versioned artifacts
  inside the loop range, "present" is **iteration-indexed**: present iff a
  version with ordinal == the current iteration exists, where the current
  iteration is derived from the evidence files (1 with no evidence; max
  ordinal if the latest evidence is `.pass`; max ordinal + 1 if `.fail`).
  This is what re-arms the fix loop by pure glob inference.
- **One phase per `next` invocation.** The engine runs exactly one phase, then
  re-infers and reports what comes next.
- **Invoke prompts inline their inputs.** For an `invoke` phase the engine
  composes a prompt file in the run dir containing the phase body, the **full
  contents** of every `reads` artifact (an invoked CLI cannot be assumed to
  read the workspace), and the writes contract. Caveat: very large artifacts
  make very large prompts — workflows should keep handoff artifacts small.
- **All artifacts are run-scoped in v1.** Persistent per-workflow context
  (an artifact that survives across runs) is a contract-2 candidate.

## Lockfile (`.laney/workflows.lock`)

JSON, machine-local (absolute paths — never commit it; `laney install` offers
the `.gitignore` entry). Written by the first successful load; read by every
later load.

```json
{
  "selected": ["swe"],
  "workflows": [
    { "id": "swe", "version": "1.0.0", "origin": "local",
      "path_or_url": "<resolved path>", "sha256": "<framed whole-folder hash>" }
  ]
}
```

- `selected` — which workflows this project loads. `load <x>` **adds**,
  `unload <x>` **removes**; ids are unique within `selected`.
- `sha256` covers **every file in the workflow folder**, each framed by its
  root-relative path and byte length, sorted by path (`.git/` and symlinks are
  excluded — both are W04 violations anyway). Whole-folder coverage means
  editing *any* file re-triggers validation and the re-pin confirmation — the
  safe direction for content that is instructions. Builtin entries carry
  `sha256: null` (repo-versioned).
- Compute with `validate-workflow.py <dir> --hash`.

## Error catalog (W01–W15)

Messages are fix-forward and literal. W11, W13-warn, W14, and W15 emit as
warnings (exit 0); everything else is an error (exit 1).

| Code | Invariant |
|---|---|
| W01 | `workflow.toml` present, parses as TOML |
| W02 | required fields present and typed (top: `id`, `version`, `contract`, `description`; role: `mode`; phase: `id`, `owner`, `writes` (+ `body` unless judge); artifact: `id`, `file`; judge: `commands`, `evidence`, `max_fix_loops`, `on_fail`) |
| W03 | `contract` supported by this engine (currently: 1) |
| W04 | folder confinement: declared paths exist, readable, resolve inside the workflow root (no `..` / absolute / symlink escape); no symlinks or `.git/` anywhere under the folder; `id` a strict slug; `--origin builtin` rejected for any path outside `--builtin-root` |
| W05 | owner/mode coherence: every `owner` is `human`, `judge`, or a declared role; `mode ∈ {native, invoke}`; `invoke` ⇒ `command` + `capture`; `native` ⇒ no `command`/`capture`; `human`/`judge` never declared in `[roles]` |
| W06 | judge coherence: `[judge]` present ⇔ exactly one `owner = "judge"` phase; the judge phase declares no `body`; `evidence` names a declared `versioned` artifact; `on_fail` names a phase preceding the judge phase; `max_fix_loops` ≥ 1 |
| W07 | phase ids unique; artifact ids unique |
| W08 | every `reads`/`writes` entry names a declared artifact; every phase's `writes` non-empty |
| W09 | dataflow: every artifact a phase reads is written by some earlier phase (loop re-entry counted) |
| W10 | single-writer: no two phases write the same artifact unless it is `versioned` and both are loop-reachable |
| W11 | prose-injection lint, **warn-only**: flags `ignore previous`, `you must now`, `disregard the above` in phase bodies, templates, and displayed manifest strings (`description` fields) |
| W12 | invoke `command` placeholders drawn only from `{prompt_file}`, `{run_dir}` |
| W13 | versioning coherence: the evidence artifact is `versioned`; a `versioned` artifact not written by any loop-reachable phase → **warning** |
| W14 | judge command shape: non-empty strings; absolute paths → **warning** (commands must resolve against the consuming repo) |
| W15 | reserved (`extends`, `[detect]`, `[[command]]`, `[identity]`) or unknown keys → **warning**, ignored |

## Fail-closed

A validator crash or an unreadable declared file is an **invalid** result,
never a pass. If the loader cannot complete, the workflow's rules are not
loaded and the engine says so. A run mid-flight when the loader or judge cannot
run is **HELD** — "the gate couldn't run" escalates to the human; it is never
reported as a pass and it is not a failure verdict either.
