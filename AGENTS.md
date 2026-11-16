# AGENTS.md

This repo holds shared, reusable GitHub Actions workflows. Each workflow lives in `.github/workflows/<name>.yml`, keeps its Python scripts beside it in `scripts/<name>/` with their tests in `scripts/<name>/tests/`, and documents its own inputs and required secrets. Consumers call a workflow pinned by commit SHA (see `README.md`).

The repo is public: never commit references to private repos or local paths on a maintainer's machine.

## Agent skills

### Issue tracker

GitHub Issues in `mindwidgets/workflows` via the `gh` CLI. Before reading or creating issues, see `docs/agents/issue-tracker.md` for the `gh` conventions and gotchas.

### Triage labels

Default triage labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), plus `idea`/`spec`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: a root `GLOSSARY.md` holds the canonical terms and the words to avoid; add a term there the first time it needs pinning down. Record design decisions in `docs/adr/`, created when the first one is needed.

### Project facts for shared workflows

- **Check command**: `bash scripts/check.sh`. It syncs the uv environment, runs the pre-commit hooks on all files (ruff, ruff format, mypy, actionlint, check-dependabot; `no-commit-to-branch` is skipped, since it guards commits, not trees) and then the tests. CI runs it on every PR and push to `main`; run it before opening a PR.
- **Test suite**: `uv run pytest -q`.
- **Coding standards**: `CODING_STANDARDS.md`, read at review time.
- **Python**: run it through `uv` (`uv run python ...`, `uv run pytest`), never a bare `python`. The version is in `.python-version`.
- **Agent worktrees**: live under `.claude/worktrees/` and are git-ignored.

## Working on workflows with an agent

The agent skills these docs name (`tdd`, `code-review`, `code-quality`, `test-quality`, `comments`, `diagnosing-bugs` and others) are not committed here. Install them into your clone from their public sources (both locations are git-ignored):

```sh
npx skills add mattpocock/skills -a claude-code --copy -y
npx skills add aaronsilinskas/ai-skills -a claude-code --copy -y
```

Then, once per clone: `uv sync` and `uv run pre-commit install`. pre-commit blocks commits to `main` (`no-commit-to-branch`), so work on a branch.

To make a change: build it with the `tdd` skill, review it with `code-review` against `CODING_STANDARDS.md`, run `bash scripts/check.sh`, and open a PR. Propose larger features as an issue first.

## Maintainer workflows

The maintainer plans larger work as spec issues broken into ticket batches, with tooling that isn't part of this repo. If you're not the maintainer, use the flow above.
