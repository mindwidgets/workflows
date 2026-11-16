# Coding standards

Read at review time (`code-review`), not during implementation. Each source below is authoritative for its area; apply every rule in each. Skills are named, not linked: install them as described in `AGENTS.md` ("Working on workflows with an agent"). The sections below are this repo's additions, which win where they differ.

- **Production code**: the `code-quality` skill (`code-quality/SKILL.md`).
- **Tests**: the `test-quality` skill (`test-quality/SKILL.md`) and `test-quality/mocking-python.md`.
- **Comments and docstrings**: the `comments` skill (`comments/SKILL.md`) and `comments/python-docstrings.md`.
- **Terms**: `GLOSSARY.md`, once it exists. Use its canonical terms and flag the terms it says to avoid.
- **Design decisions**: `docs/adr/`, once it exists. Flag code that departs from an accepted ADR.

`bash scripts/check.sh` runs ruff, ruff format, mypy, actionlint and pytest, in pre-commit and CI. Skip what they enforce.

## Python

- Scripts are Python in this uv project, run with `uv run`. Add dependencies with `uv add` (or `uv add --dev`), so `pyproject.toml` and `uv.lock` change together.
- Scripts are fully typed: mypy runs in `strict` mode over every `.py` file. Tests are exempt from annotations, but their bodies are still checked. A `# type: ignore` names its error code.
- Tests use pytest, live in `tests/`, and test a script through its public entry points.

## Workflows

- **Pin third-party actions to a full commit SHA**, with the version in a trailing comment: `uses: actions/checkout@<sha> # v4.4.0`. Never a tag or branch, which can be moved under you. The same goes for consumers calling a workflow here.
- **Least-privilege `permissions` on every job.** Set `permissions: contents: read` (or narrower) at the top level, and grant each job only the scopes it uses. Check out with `persist-credentials: false` unless a later step pushes.
- **No `${{ }}` with untrusted event data inside `run:`.** Issue and PR titles, bodies, comments, branch names and similar are attacker-controlled; an expression in a script is pasted in before the shell parses it, so it can inject commands. Pass the value through `env:` and read it as a quoted shell variable (`"$ISSUE_TITLE"`). actionlint flags the common cases; the rule covers the ones it misses too.
- **No comments inside inputs an action re-parses as a command line** (such as `claude-code-action`'s `claude_args`). The action prepends its own flags, so a `#` there no longer starts a whole-line comment, and its parser can treat everything after it as a comment, silently dropping every later flag. Explain the flags in YAML comments above the key instead.
- **Each reusable workflow documents its interface**: its inputs, its required secrets and the permissions its caller must grant, in a comment block at the top of the file or a section of `README.md`.

## Judgement calls

- **Docs agree with the change.** When a diff changes behaviour, every prose description of that behaviour must still be true: `README.md`, `AGENTS.md`, `docs/agents/`, docstrings and `GLOSSARY.md`. Search the repo for the changed names and the behaviour's key words, and flag any sentence the diff makes false, including lines the diff never touched.
- **Nothing private.** The repo is public: flag any reference to a private repo or a path on a maintainer's machine.
