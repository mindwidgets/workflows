"""Tests for scripts.triage.issue: reading an issue's live state with ``gh``. No network."""

from unittest.mock import patch

import pytest

from scripts.triage.issue import IssueState, read_issue_state
from scripts.triage.tests.fake_gh import FakeGh, gh_issue


def _read_with(fake_gh: FakeGh, number: int = 42) -> IssueState:
    with patch("scripts.triage.issue.subprocess.run", fake_gh):
        return read_issue_state(number)


def test_the_reader_views_the_given_issue_with_gh():
    fake_gh = FakeGh(gh_issue(42))

    _read_with(fake_gh, number=42)

    assert fake_gh.views == [["gh", "issue", "view", "42"]]


def test_the_reader_reports_the_issues_live_state_labels_and_author():
    fake_gh = FakeGh(gh_issue(42, state="OPEN", labels=("needs-triage", "bug"), author="octo"))

    issue = _read_with(fake_gh, number=42)

    assert issue == IssueState(
        number=42,
        is_open=True,
        is_pull_request=False,
        labels=frozenset({"needs-triage", "bug"}),
        author="octo",
    )


@pytest.mark.parametrize("state", ["CLOSED", "MERGED"])
def test_the_reader_reports_any_state_but_open_as_closed(state):
    assert not _read_with(FakeGh(gh_issue(42, state=state))).is_open


def test_the_reader_recognises_a_pull_request_by_its_url():
    assert _read_with(FakeGh(gh_issue(42, kind="pull"))).is_pull_request


def test_the_reader_reads_a_deleted_author_as_ghost():
    assert _read_with(FakeGh(gh_issue(42, author=None))).author == "ghost"
