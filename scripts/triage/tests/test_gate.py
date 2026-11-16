"""Tests for scripts.triage.gate: the gate that decides whether an event starts a triage run."""

from unittest.mock import patch

import pytest

from scripts.triage.gate import TriageEvent, gate, main
from scripts.triage.issue import IssueState
from scripts.triage.tests.fake_gh import FakeGh, gh_issue


def _issue(*labels: str, is_open: bool = True, is_pull_request: bool = False) -> IssueState:
    return IssueState(
        number=7,
        is_open=is_open,
        is_pull_request=is_pull_request,
        labels=frozenset(labels),
        author="reporter",
    )


def _open_issue(*labels: str) -> IssueState:
    return _issue(*labels)


def _labeled(label: str) -> TriageEvent:
    return TriageEvent(kind="labeled", issue_number=7, added_label=label, sender_is_bot=False)


def test_adding_needs_triage_to_an_open_issue_that_still_carries_it_runs():
    verdict = gate(_labeled("needs-triage"), _open_issue("needs-triage", "bug"))

    assert verdict.run


def test_adding_any_other_label_skips_even_when_the_issue_carries_needs_triage():
    verdict = gate(_labeled("bug"), _open_issue("needs-triage", "bug"))

    assert not verdict.run


def test_adding_needs_triage_skips_when_the_live_labels_no_longer_include_it():
    verdict = gate(_labeled("needs-triage"), _open_issue("bug"))

    assert not verdict.run


def _dispatch() -> TriageEvent:
    return TriageEvent(
        kind="workflow_dispatch", issue_number=7, added_label=None, sender_is_bot=False
    )


def test_a_dispatch_runs_on_an_open_issue_carrying_needs_triage():
    assert gate(_dispatch(), _open_issue("needs-triage")).run


def test_a_dispatch_skips_an_issue_without_needs_triage():
    assert not gate(_dispatch(), _open_issue("ready-for-agent")).run


_EVENTS_THAT_WOULD_RUN = [_labeled("needs-triage"), _dispatch()]


@pytest.mark.parametrize("event", _EVENTS_THAT_WOULD_RUN, ids=lambda e: e.kind)
def test_a_closed_issue_skips(event):
    assert not gate(event, _issue("needs-triage", is_open=False)).run


@pytest.mark.parametrize("event", _EVENTS_THAT_WOULD_RUN, ids=lambda e: e.kind)
def test_a_pull_request_skips(event):
    assert not gate(event, _issue("needs-triage", is_pull_request=True)).run


@pytest.mark.parametrize("event", _EVENTS_THAT_WOULD_RUN, ids=lambda e: e.kind)
def test_a_bot_sender_skips(event):
    from_bot = event._replace(sender_is_bot=True)

    assert not gate(from_bot, _open_issue("needs-triage")).run


@pytest.mark.parametrize("kind", ["opened", "edited", "issue_comment"])
def test_any_other_event_kind_skips(kind):
    event = TriageEvent(kind=kind, issue_number=7, added_label="needs-triage", sender_is_bot=False)

    assert not gate(event, _open_issue("needs-triage")).run


def test_each_skip_states_its_own_reason():
    skips = [
        gate(_labeled("needs-triage")._replace(sender_is_bot=True), _open_issue("needs-triage")),
        gate(_labeled("needs-triage")._replace(kind="opened"), _open_issue("needs-triage")),
        gate(_labeled("bug"), _open_issue("needs-triage")),
        gate(_dispatch(), _issue(is_pull_request=True)),
        gate(_dispatch(), _issue(is_open=False)),
        gate(_dispatch(), _open_issue()),
    ]

    reasons = [verdict.reason for verdict in skips]
    assert all(reasons)
    assert len(set(reasons)) == len(reasons)


# ---------------------------------------------------------------------------
# The command-line entry point. gh is stubbed: no network.
# ---------------------------------------------------------------------------


def _run_main(args, fake_gh, tmp_path, monkeypatch) -> dict[str, str]:
    """Run the entry point against *fake_gh* and return what it wrote to the step's outputs."""
    outputs = tmp_path / "github_output"
    outputs.touch()
    monkeypatch.setenv("GITHUB_OUTPUT", str(outputs))
    with patch("scripts.triage.issue.subprocess.run", fake_gh):
        main(args)
    return dict(line.split("=", 1) for line in outputs.read_text().splitlines())


def test_the_entry_point_outputs_run_for_a_live_needs_triage_label(tmp_path, monkeypatch):
    outputs = _run_main(
        ["--event", "labeled", "--issue", "42", "--label", "needs-triage"],
        FakeGh(gh_issue(42, labels=("needs-triage",))),
        tmp_path,
        monkeypatch,
    )

    assert outputs["run"] == "true"


def test_the_entry_point_trusts_the_live_labels_over_the_event(tmp_path, monkeypatch):
    outputs = _run_main(
        ["--event", "labeled", "--issue", "42", "--label", "needs-triage"],
        FakeGh(gh_issue(42, labels=("bug",))),
        tmp_path,
        monkeypatch,
    )

    assert outputs["run"] == "false"


def test_the_entry_point_treats_a_bot_sender_type_as_a_bot(tmp_path, monkeypatch):
    outputs = _run_main(
        ["--event", "workflow_dispatch", "--issue", "42", "--sender-type", "Bot"],
        FakeGh(gh_issue(42, labels=("needs-triage",))),
        tmp_path,
        monkeypatch,
    )

    assert outputs["run"] == "false"


def test_the_entry_point_logs_the_skip_reason(tmp_path, monkeypatch, capsys):
    _run_main(
        ["--event", "workflow_dispatch", "--issue", "42"],
        FakeGh(gh_issue(42, state="CLOSED", labels=("needs-triage",))),
        tmp_path,
        monkeypatch,
    )

    assert "skip: #42 is closed" in capsys.readouterr().out


def test_the_entry_point_outputs_the_default_model_and_turn_cap_when_both_are_empty(
    tmp_path, monkeypatch
):
    outputs = _run_main(
        ["--event", "workflow_dispatch", "--issue", "42", "--model", "", "--max-turns", ""],
        FakeGh(gh_issue(42, labels=("needs-triage",))),
        tmp_path,
        monkeypatch,
    )

    assert outputs == {"run": "true", "model": "sonnet", "max-turns": "10"}


def test_the_entry_point_outputs_a_valid_model_and_turn_cap_as_given(tmp_path, monkeypatch):
    outputs = _run_main(
        [
            *("--event", "workflow_dispatch", "--issue", "42"),
            *("--model", "claude-opus-4-1", "--max-turns", "50"),
        ],
        FakeGh(gh_issue(42, labels=("needs-triage",))),
        tmp_path,
        monkeypatch,
    )

    assert (outputs["model"], outputs["max-turns"]) == ("claude-opus-4-1", "50")


@pytest.mark.parametrize(
    ("option", "value", "named"),
    [("--model", "sonnet #x", "model"), ("--max-turns", "51", "max-turns")],
)
def test_the_entry_point_fails_on_an_invalid_input_before_reading_the_issue(
    option, value, named, tmp_path, monkeypatch
):
    fake_gh = FakeGh(gh_issue(42, labels=("needs-triage",)))

    with pytest.raises(SystemExit) as exit_info:
        _run_main(
            ["--event", "workflow_dispatch", "--issue", "42", option, value],
            fake_gh,
            tmp_path,
            monkeypatch,
        )

    assert exit_info.value.code != 0
    assert named in str(exit_info.value.code)
    assert fake_gh.calls == []
    assert (tmp_path / "github_output").read_text() == ""
