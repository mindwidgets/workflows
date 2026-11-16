# workflows

Shared, reusable GitHub Actions workflows. Each workflow lives in `.github/workflows/`, with its Python scripts and their tests beside it in `scripts/<name>/`.

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

See `AGENTS.md` for the issue tracker, labels and setup, and `CODING_STANDARDS.md` for the standards. `AGENTS.md` also gives the setup and the check command CI runs.
