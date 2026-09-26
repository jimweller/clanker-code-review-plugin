# clanker-code-review

Nine-perspective code review for Claude Code, Codex, OpenCode, and Hermes Agent.

## Skills

- `review-deep` — full engine: checkout, normalize, collate, window, merge, rank, verify with
  isolated judges, and report. The only copy of the scripted back half.
- `review-full` — dispatches the nine reviewer agents over the whole repo, then runs the same
  scripted back half as `review-deep`.
- `review-diff` — dispatches the nine reviewer agents over a diff against a base commit, then
  runs the same scripted back half.
- `review-tickets` — turns a `review-deep`, `review-full`, or `review-diff` run into filed
  tickets, reconciled and deduped against the run's findings.

Claude Code, Codex: full agent dispatch. OpenCode, Hermes Agent: `review-deep` only (no
subagent-dispatchable reviewer agents), see each skill's preflight for details.

## Agents

Nine Claude Code subagents in `agents/`, one per review perspective: architecture, correctness,
data, ops, performance, quality, security, SOLID, testing. Dispatched by `review-full` and
`review-diff`.

## Installing

Claude Code: install via the `jimweller` marketplace as the `clanker-code-review` plugin.

Codex, OpenCode, Hermes Agent: `npx skills add https://github.com/jimweller/clanker-code-review -a codex -a opencode -a hermes-agent`.

## Tests

```bash
cd evals && PYTHONDONTWRITEBYTECODE=1 uv run --with pytest pytest -q -p no:cacheprovider .
```
