# PR summary

## Purpose

Turn a green run into a PR-ready summary grounded in the diff and the
evidence — not in memory of the conversation.

## Instructions

Read the artifacts below plus the current git diff, the latest
`review-<n>.md`, `fix-plan-<n>.md`, and the passing `test-output-<n>.pass.md`
in the run directory. Draft the summary from what actually changed and what
actually ran — every claim in "Testing" must correspond to a command in the
passing evidence.

Format:

```md
## Summary
- What changed, why, what behavior was preserved

## Testing
- The commands that ran, from the evidence file

## Notes
- Risk:
- Rollback:
```

## Inputs

- `plan`: intended approach, for the "why".
- `acceptance`: what done meant — note any items consciously deferred.
- `impl-notes`: files changed and decisions.

## Done means

`pr-summary.md` is paste-ready: summary, testing (matching the evidence),
risks and rollback. No claims the run's artifacts can't back.
