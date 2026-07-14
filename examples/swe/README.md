# swe — the worked-example workflow

The software feature loop from the source doc ("Claude plans and reviews,
Codex implements, Bun-based checks judge, Antigravity is the specialist
lane"), expressed as a laney workflow. This folder is **workflow-owned data**:
every tool name and binding lives here, none in the engine — deleting this
folder leaves laney mechanically intact.

Load it from any consuming repo:

```bash
# in the consuming project
laney load /path/to/laney/examples/swe
laney next    # steps one phase per invocation
```

## Roles

| Role | Mode | Binding |
|---|---|---|
| `architect` | native | the loaded AI session (Claude) — plans, reviews, PR summary |
| `implementer` | invoke | `codex exec -s workspace-write --skip-git-repo-check - < {prompt_file}` (capture: files, 30 min) |
| `specialist` | invoke | `agy -p "$(cat {prompt_file})" --mode plan` (capture: stdout, 10 min) |
| `human` | reserved | product owner: context capture, final decisions |
| `judge` | reserved | mechanical: `bun run typecheck / lint / test / build` |

## Phases

1. **capture-context** (human) → `context.md`
2. **plan** (architect) → `plan.md`, `acceptance.md`
3. **spike** (specialist, no-edit) → `spike.md` — writes `skipped: not
   applicable` for non-Google/browser tasks
4. **implement** (implementer) → `implementation-notes.md` + the repo diff
5. **review** (architect) → `review-<n>.md` ┐
6. **fix** (implementer) → `fix-plan-<n>.md` │ fix loop, max 3 —
7. **judge** (bun checks) → `test-output-<n>.pass|fail.md` ┘ on fail, re-enter review
8. **pr** (architect) → `pr-summary.md`

One deliberate rotation from the source doc: contract 1 requires the judge's
`on_fail` target to precede the judge, so each iteration runs review → fix →
checks (the doc writes it checks → review → fix). Iteration 1's review is a
pre-judge code review; from iteration 2 the review also reads the failing
evidence. `bun run e2e` is not a judge command — a repo without that script
would hold every run — E2E for UI-heavy work is a review checklist item.

## Provenance

Authored 2026-07-13 via `laney workflows create` from
`~/Downloads/agentic-dev-workflow.md`; bindings confirmed against the locally
installed `codex` 0.144.1 and `agy` CLIs. The image-generation lane from the
source doc is out of scope here — it is its own workflow when needed.
