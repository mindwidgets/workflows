# workflows

Shared, reusable GitHub Actions workflows. Each workflow lives in `.github/workflows/`, with its Python scripts and their tests beside it in `scripts/<name>/`.

A **consumer** is a repository that calls one of these workflows; its **caller workflow** is the file holding the `uses:` job that makes the call. Terms are defined in `GLOSSARY.md`.

## Calling a workflow

Call a workflow from a job in your caller workflow, pinned to the full commit SHA of a release tag, with the tag in a trailing comment (never the tag or a branch itself, which can move):

```yaml
jobs:
  example:
    permissions:
      contents: read
    uses: mindwidgets/workflows/.github/workflows/<name>.yml@<full commit SHA of the tag> # vX.Y.Z
    secrets:
      SOME_SECRET: ${{ secrets.SOME_SECRET }}
```

- **Pass secrets by name**, each under `secrets:` with the name the workflow declares. Don't use `secrets: inherit`: it only reaches caller workflows in the same organization or enterprise as this repo, and it would hand every one of your secrets to shared code when the workflow needs one.
- **Grant the `permissions` the workflow asks for** on the calling job, and set `permissions: {}` at the top of your caller workflow. A called workflow can only narrow what the calling job grants; if one of its jobs asks for more, the run fails before any job starts.
- **Look up a release's SHA** with `git ls-remote --tags https://github.com/mindwidgets/workflows`, or on the tag's page.

Each workflow documents its own triggers, inputs, the secrets it takes and the `permissions` its calling job must grant, in the comment block at the top of its file.

### Keeping the pin up to date

Add Dependabot's `github-actions` ecosystem to your repo (`.github/dependabot.yml`), and it proposes a PR moving the pin, and its `# vX.Y.Z` comment, to each new release:

```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
```

It moves a SHA pin only to a SHA a release tag points at, so pin a tagged commit. Read the release's notes before merging the PR: they say when your caller workflow must change too.

## Releases

- One repo-wide tag sequence, `vX.Y.Z`, on `main`. The maintainer cuts a tag after a merge that changes a workflow. A tag is never moved or reused.
- A major bump (`v2.0.0`) marks a change consumers must act on: a new required input or secret, a wider permission, or changed triggers. A release's notes say when consumers must change their caller workflow, and how.
- If the repo ever versions its workflows separately, tags take the slash form `<name>/vX.Y.Z` (`triage/v1.2.0`), never a dash form such as `triage-v1.2.0`: Dependabot can't read a version from that, so it would move the pin to the branch head and leave the comment stale.

## Triage

`triage.yml` has Claude triage one issue read-only, then a separate deterministic step validates Claude's decision and applies it to that issue. All of it runs from the **tools checkout**: this repo's files at the commit you pinned, kept out of Claude's reach.

### What it does

- **`needs-triage` is the only switch.** Adding it to an open issue (creating the issue with it counts) starts a run. The gate re-reads the issue's live state, so any other label, a closed issue, or a dispatch on an issue without `needs-triage` changes nothing. Events from bots start nothing, and neither do the labels and comments triage writes itself.
- **Who can start a run:** people with write access to your repo. Someone who can only add labels can add `needs-triage`, but the Claude step refuses an actor without write access, so that run fails and changes nothing. Never add an issue template that applies `needs-triage`: it would let any reporter start a run.
- **Claude is read-only.** It reads your repo's default branch and the docs you name, with its file tools confined to that checkout: no writes, shell, web or GitHub tools, and no settings from your checkout.
- **One validated writer.** Only the apply step writes to GitHub, and only to the triggering issue. It sets a category (`bug` or `enhancement`, replacing the other) and one state: `needs-info` (with questions for the reporter), `ready-for-agent` (with an agent brief), `ready-for-human`, or `needs-triage` kept with a recommendation when Claude can't decide. It posts one comment, starting with an AI disclaimer, before it changes the labels.
- **What it never touches:** it never closes an issue, never applies `wontfix`, and never adds or removes a label outside the set below. The comment can notify no one but the issue's author and links no other issue or pull request. An invalid decision changes nothing, and a run where Claude returns no decision fails red.
- **Credentials stay in the Claude job:** before a decision leaves the job that holds your Claude credential, a check fails the job if the decision carries any part of that credential or the job token.
- **Re-triage:** re-add `needs-triage`, or dispatch your caller workflow with the issue number while the issue carries `needs-triage`. Replies and edits start nothing.

### Caller workflow

Save this as `.github/workflows/triage.yml` in your repo, pinned to `v1.0.0` below. For a later release, replace the SHA and the tag with that release's (see [Calling a workflow](#calling-a-workflow)):

```yaml
name: Triage

on:
  issues:
    types: [labeled]
  workflow_dispatch:
    inputs:
      issue:
        description: Issue number to triage again (it must be open and carry needs-triage)
        required: true
        type: number

permissions: {}

# One run per issue at a time, never cancelling one in progress, so two events apply in order.
# Without it, two runs on one issue can apply at once and undo each other's labels.
concurrency:
  group: triage-${{ github.event.issue.number || inputs.issue }}
  cancel-in-progress: false

jobs:
  triage:
    permissions:
      contents: read
      issues: write
    uses: mindwidgets/workflows/.github/workflows/triage.yml@11cfe9c10eda9ad0462de79d36a12a3c2df98cba # v1.0.0
    secrets:
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
    # All optional, shown at their defaults: delete any you don't change.
    with:
      labels-doc: docs/agents/triage-labels.md
      project-docs: |
        GLOSSARY.md
        docs/domain.md
        docs/adr/
      model: sonnet
      max-turns: 10
```

- The dispatch input must be named `issue`: the workflow reads it from your event.
- `labels-doc` is the doc Claude reads first, saying what each label means in your repo. `project-docs` lists the files and directories Claude reads for your project's terms and structure, one per line. A path holding a backtick or line break fails the run before Claude starts.
- `model` takes letters, digits, `.`, `-`, `_`, `[` and `]`; `max-turns` a whole number from 1 to 50. The gate rejects anything else, and then nothing else runs.

### Labels to create

Create these labels in your repo. Triage uses exactly these names, and adds or removes no others:

- `bug`
- `enhancement`
- `needs-triage`
- `needs-info`
- `ready-for-agent`
- `ready-for-human`

Describe what each means in your repo in your `labels-doc`, for Claude and for people.

### Claude credential

Your repo keeps its own Claude credential as a repository secret, and the caller workflow passes it by name; triage never sees one you didn't pass. Each consumer mints, stores and renews its own.

- **Subscription token (`CLAUDE_CODE_OAUTH_TOKEN`):** run `claude setup-token` locally and store the result as the secret. It expires one year after it is minted, so record the mint date and a renew-by date (about a month before expiry) in your repo's own docs, with a calendar reminder. To renew, mint a new token, replace the secret and update those dates. An expired or missing token fails the run red and leaves `needs-triage` on the issue.
- **API key instead:** add an `ANTHROPIC_API_KEY` secret holding a Claude Console key, and change the one line under `secrets:` to `ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}`.
- **Pass one, not both.** If you pass both, Claude uses `ANTHROPIC_API_KEY` and bills the Console key, not your subscription.

## Dependency updates

Dependabot (`.github/dependabot.yml`) checks the pinned actions (`github-actions`), the Python packages in `uv.lock` (`uv`) and the pre-commit hooks (`pre-commit`) weekly, and proposes each bump as a PR, which CI checks like any other. Each ecosystem's minor and patch updates arrive together in one PR; each major update arrives in its own PR, so a breaking one never holds up routine bumps. Actions stay pinned by full SHA, and Dependabot moves the SHA and its `# vX.Y.Z` comment together.

Two bumps need more than merging the PR:

- **`anthropics/claude-code-action`:** its Dependabot PR fails CI on purpose, until the port the triage tests use is rechecked against the new version (see [Bumping `claude-code-action`](#bumping-claude-code-action)).
- **uv itself:** Dependabot never reads values under `with:`, so it never moves the uv release the `setup-uv` steps install. Bump it by hand (see [Bumping uv](#bumping-uv)).

## Maintaining triage

The history behind these rules is in aura-prototype, triage's first consumer: the original spec ([aaronsilinskas/aura-prototype#1398](https://github.com/aaronsilinskas/aura-prototype/issues/1398)), the bug that dropped Claude's sandbox ([#1407](https://github.com/aaronsilinskas/aura-prototype/issues/1407)) and the acceptance pass ([#1403](https://github.com/aaronsilinskas/aura-prototype/issues/1403)).

### Editing `claude_args`

`claude_args` in `triage.yml` carries Claude's whole sandbox: model, turn cap, `--setting-sources user`, `--permission-mode dontAsk`, the allow and deny rules and the decision schema. Never put a comment inside it; explain the flags in YAML comments above the key. `claude-code-action` puts its own flags in front of the first line, so a comment there is no longer a whole-line comment, and its parser treats an unquoted `#` (even mid-word) as a comment running to the end of the input. Every flag after it is silently dropped: Claude runs with no model, turn cap, schema or allow and deny rules, and with the checkout's own settings loaded, on a run that still shows green. That happened once (#1407 above).

`scripts/triage/tests/test_workflow.py` guards it: it runs `claude_args` through a port of the pinned action's parser, with the default inputs and with every shape of model and turn cap the gate accepts, and checks every restriction reaches the CLI.

### Bumping `claude-code-action`

The port the regression test relies on, `scripts/triage/tests/claude_code_action.py`, is faithful only to the action SHA it names. On any bump of `anthropics/claude-code-action`, recheck the port against the new SHA's `base-action/src/parse-sdk-options.ts`, `src/modes/agent/index.ts` and the `shell-quote` version `base-action/bun.lock` locks, update it and the SHA its docstring names, and only then merge the bump.

A Dependabot bump of the action can't skip this: `test_the_parser_port_names_the_claude_code_action_sha_the_workflow_pins` in `scripts/triage/tests/test_workflow.py` fails while the SHA `triage.yml` pins differs from the one the port's docstring names. Push the recheck, and the docstring's new SHA, to the Dependabot PR's branch, and CI passes again.

### Bumping uv

Every `astral-sh/setup-uv` step, in `triage.yml` and in CI, installs one exact uv release (`version:`) and checks the download against that release's sha256 (`checksum:`, for `uv-x86_64-unknown-linux-gnu.tar.gz`). Without them, setup-uv installs whatever uv is newest when the job runs, including in the job holding the consumer's Claude credential and the one that writes to its issues. Python comes from the same pin: the workflows set `UV_PYTHON_PREFERENCE=only-managed`, so uv runs the CPython build its own release names and verifies it against the sha256 that release carries, never a Python on the runner image.

Dependabot doesn't read `version:` or `checksum:`, so a uv bump is a deliberate change, made by hand in its own PR:

1. Pick the latest stable release from [astral-sh/uv's releases](https://github.com/astral-sh/uv/releases), and read its changelog.
2. Take the checksum from its `uv-x86_64-unknown-linux-gnu.tar.gz.sha256` asset: `gh release download <version> -R astral-sh/uv -p 'uv-x86_64-unknown-linux-gnu.tar.gz.sha256' -O -`.
3. Update `version:` and `checksum:` on every `setup-uv` step together, in `triage.yml` and `ci.yml`.
4. Check that the new release still serves the Python in `.python-version` on the runners: run with the new uv, `UV_PYTHON_PREFERENCE=only-managed uv python list <python version> --only-downloads --all-platforms --all-arches` lists a `linux-x86_64-gnu` download.
5. Open the PR, and let CI run the suite on it. `scripts/triage/tests/test_workflow.py` fails if any step lacks an exact version or a checksum, or if the steps disagree.

### The actionlint ignore

`.github/actionlint.yaml` ignores one error, only in `triage.yml`: actionlint doesn't yet know the `job` context's documented `workflow_repository` and `workflow_sha`, which the tools checkout uses. Each job's first step fails the run if either renders empty, since `actions/checkout` would otherwise fall back to your repo and ref. The fix is upstream ([rhysd/actionlint#707](https://github.com/rhysd/actionlint/issues/707), still open). Once a release of actionlint knows `job.workflow_sha`, bump the pinned actionlint and delete the ignore.

## Contributing

See `AGENTS.md` for the issue tracker, labels and setup, and `CODING_STANDARDS.md` for the standards. `AGENTS.md` also gives the setup and the check command CI runs.
