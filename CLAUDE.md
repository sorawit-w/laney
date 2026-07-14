At session start, invoke the `kerby` skill (args: load) to load kerby guardrails into context.

## Project map

This repo is **laney** — a pluggable workflow engine for AI-assisted work
(kerby's sibling: kerby judges how work is done, laney sequences who does it).

- `skills/laney/SKILL.md` — the engine (load/status/next/workflows/install).
- `docs/workflow-contract.md` — the normative manifest schema (contract 1,
  error catalog W01–W15). Change the contract → change the validator and its
  tests in the same commit.
- `skills/laney/resources/scripts/validate-workflow.py` — the validator
  (stdlib-only, Python ≥ 3.11); test matrix: `bash scripts/validate-workflow.test.sh`.
- `skills/laney/workflows/` — bundled workflows: **empty in v1 by design**.
- **Zoning rule:** engine surfaces (`SKILL.md`, `resources/**`) never name a
  concrete tool; verify with `grep -riE 'codex|bun|antigravity|agy' skills/ docs/ README.md`.
- This repo authors an agent skill, so kerby's `skill-authoring` gate applies:
  no change to `skills/laney/SKILL.md` (or prose it loads) ships as verified
  without a fresh skill-evaluator pass on the final text, verdict recorded.
