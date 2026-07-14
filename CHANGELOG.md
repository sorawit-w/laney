# Changelog

## 0.1.0 — 2026-07-13

Initial release: the engine, with no bundled workflows (by design).

- **Manifest contract 1** (`docs/workflow-contract.md`): `workflow.toml` with
  `[roles]` (modes `native` / `invoke`), ordered `[[phase]]` tables with
  `reads`/`writes` artifact dataflow, `[[artifact]]` declarations
  (templates, versioning), and a mechanical `[judge]` (commands, evidence,
  `max_fix_loops`, `on_fail`).
- **Stateless runs:** position inferred from artifact presence in
  `.laney/runs/<date>-<slug>/`; judge verdicts encoded in evidence filenames
  (`<stem>-<n>.pass/.fail<ext>`), whose ordinals are the loop counter.
- **Engine verbs:** `load`, `unload`, `status`, `next` (one phase per
  invocation), `workflows list|create` (interactive, continuously validated),
  `install` (vendor-file line + lock `.gitignore` hygiene; no hooks),
  `commands`/`help`.
- **Validator** (`resources/scripts/validate-workflow.py`, Python ≥ 3.11
  stdlib-only): error catalog W01–W15, folder confinement, whole-folder framed
  `--hash`, install-anchored `--origin builtin`; test matrix under
  `scripts/validate-workflow.test.sh`.
- **Zoning rule:** engine surfaces contain zero tool names; all bindings are
  workflow-owned data.
- Reserved for later contracts: `extends`, `[detect]`, `[[command]]`,
  `[identity]`, remote origins, TOFU trust prompts, intent manifest.
