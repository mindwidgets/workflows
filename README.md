# workflows

Shared, reusable GitHub Actions workflows. Each workflow lives in `.github/workflows/`, with its Python scripts in `scripts/` and their tests in `tests/`.

## Calling a workflow

Call a workflow from a job in your repo, pinned to a commit SHA of this repo (never a branch or tag, which can move):

```yaml
jobs:
  example:
    uses: mindwidgets/workflows/.github/workflows/<name>.yml@<sha>
    secrets: inherit
```

Each workflow documents its own inputs, the secrets it needs and the `permissions` its calling job must grant. `secrets: inherit` passes your repo's secrets through; pass them individually under `secrets:` instead if you prefer.

## Contributing

See `AGENTS.md` for the issue tracker, labels and setup, and `CODING_STANDARDS.md` for the standards. Once per clone, run `uv sync` and `uv run pre-commit install`; `bash scripts/check.sh` runs every check CI does.
