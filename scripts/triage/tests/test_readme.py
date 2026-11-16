"""Tests that README's triage docs agree with the triage workflow a consumer calls.

A consumer copies README's caller workflow and creates README's labels, so both are checked
against ``triage.yml`` and the labels the apply step writes.
"""

import re
from pathlib import Path
from typing import Any

import yaml

from scripts.triage.labels import CATEGORY_LABELS, STATE_LABELS

_ROOT = Path(__file__).resolve().parents[3]
_README = (_ROOT / "README.md").read_text(encoding="utf-8")
_WORKFLOW: dict[Any, Any] = yaml.safe_load(
    (_ROOT / ".github" / "workflows" / "triage.yml").read_text(encoding="utf-8")
)
_CALLED = "mindwidgets/workflows/.github/workflows/triage.yml"


def _caller_example_text() -> str:
    blocks = re.findall(r"^```yaml\n(.*?)^```", _README, flags=re.MULTILINE | re.DOTALL)
    (example,) = (block for block in blocks if f"uses: {_CALLED}@" in block)
    return str(example)


def _caller_example() -> dict[Any, Any]:
    example: dict[Any, Any] = yaml.safe_load(_caller_example_text())
    return example


def _calling_job() -> dict[str, Any]:
    job: dict[str, Any]
    (job,) = _caller_example()["jobs"].values()
    return job


def test_the_caller_example_pins_a_full_sha_with_the_release_tag_in_a_comment():
    pins = re.findall(rf"uses: {re.escape(_CALLED)}@(\S+)(.*)$", _caller_example_text(), re.M)

    assert len(pins) == 1
    sha, comment = pins[0]
    assert re.fullmatch(r"[0-9a-f]{40}", sha)
    assert re.fullmatch(r" # v\d+\.\d+\.\d+", comment)


def test_the_caller_example_passes_its_secret_by_name():
    secrets = _calling_job()["secrets"]

    assert secrets == {"CLAUDE_CODE_OAUTH_TOKEN": "${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}"}


def test_the_caller_example_passes_only_inputs_and_secrets_the_workflow_declares():
    interface = _WORKFLOW[True]["workflow_call"]
    job = _calling_job()

    assert set(job.get("with", {})) <= set(interface["inputs"])
    assert set(job["secrets"]) <= set(interface["secrets"])


def test_the_caller_example_shows_every_input_at_the_workflows_default():
    # README says the example's inputs are "shown at their defaults".
    inputs = _WORKFLOW[True]["workflow_call"]["inputs"]

    assert _calling_job()["with"] == {name: spec["default"] for name, spec in inputs.items()}


def test_the_caller_example_grants_the_calling_job_exactly_what_triage_needs():
    assert _caller_example()["permissions"] == {}
    assert _calling_job()["permissions"] == {"contents": "read", "issues": "write"}


def test_the_caller_example_triggers_on_a_label_or_a_dispatch_with_an_issue_number():
    triggers = _caller_example()[True]

    assert set(triggers) == {"issues", "workflow_dispatch"}
    assert triggers["issues"] == {"types": ["labeled"]}
    assert triggers["workflow_dispatch"]["inputs"]["issue"]["required"] is True
    assert triggers["workflow_dispatch"]["inputs"]["issue"]["type"] == "number"


def test_the_caller_example_runs_one_issue_at_a_time_without_cancelling():
    concurrency = _caller_example()["concurrency"]

    assert "github.event.issue.number" in concurrency["group"]
    assert "inputs.issue" in concurrency["group"]
    assert concurrency["cancel-in-progress"] is False


def test_the_readme_never_recommends_inheriting_secrets():
    assert "secrets: inherit" not in _caller_example_text()
    assert not re.search(r"^\s*secrets: inherit", _README, re.MULTILINE)


def _section(heading: str) -> str:
    (section,) = re.findall(rf"^{re.escape(heading)}\n(.*?)(?=^#)", _README, re.M | re.DOTALL)
    return str(section)


def test_the_labels_to_create_are_the_labels_triage_writes():
    listed = re.findall(r"^- `([^`]+)`$", _section("### Labels to create"), re.MULTILINE)

    assert len(listed) == len(set(listed))
    assert set(listed) == CATEGORY_LABELS | STATE_LABELS
