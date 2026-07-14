# laney — skill bundle

This folder is the installable laney skill: the **engine only**.

- `SKILL.md` — the engine: `load`, `unload`, `status`, `next`, `workflows list|create`, `install`, `commands`.
- `resources/scripts/validate-workflow.py` — the workflow validator (Python ≥ 3.11, stdlib only). Ships here so `load` can invoke it wherever the skill is installed.
- `resources/references/` — the execution model for `next` and the `workflows create` walkthrough, read on demand.
- `resources/templates/` — skeletons `workflows create` starts from.
- `workflows/` — bundled workflows. **Empty in v1 by design**: the engine has no opinions; workflows carry all domain content and every tool name.

Authoring documentation (`workflow-contract.md`, `AUTHORING-WORKFLOWS.md`) lives in the repo's `docs/`, not in this bundle: <https://github.com/sorawit-w/laney/tree/main/docs>.
