"""The triggering issue as GitHub reports it live, read with ``gh``.

:func:`view_issue` is the one ``gh issue view`` call every triage step reads an issue with;
:func:`read_issue_state` builds the gate's and the apply step's :class:`IssueState` on it.
"""

import json
import subprocess
from collections.abc import Iterable, Mapping
from typing import Any, NamedTuple


class IssueState(NamedTuple):
    """An issue's live state as GitHub reports it, read fresh rather than from an event payload.

    The gate reads its state and labels; the apply step reads its labels and its author, the
    one login a triage comment may mention.
    """

    number: int
    is_open: bool
    is_pull_request: bool
    labels: frozenset[str]
    author: str


def view_issue(number: int, fields: Iterable[str]) -> dict[str, Any]:
    """Read *fields* of issue *number* with ``gh issue view --json``; raises if ``gh`` fails."""
    result = subprocess.run(
        ["gh", "issue", "view", str(number), "--json", ",".join(fields)],
        capture_output=True,
        text=True,
        check=True,
    )
    issue: dict[str, Any] = json.loads(result.stdout)
    return issue


def login(user: Mapping[str, Any] | None) -> str:
    """A ``gh`` user's login; GitHub reports a deleted account as no user, read as ``ghost``."""
    if not user:
        return "ghost"
    name: str = user["login"]
    return name


def label_names(issue: Mapping[str, Any]) -> frozenset[str]:
    """The names of a ``gh issue view --json labels`` issue's labels."""
    return frozenset(label["name"] for label in issue["labels"])


def read_issue_state(number: int) -> IssueState:
    """Read issue *number*'s live :class:`IssueState`; raises if ``gh`` fails.

    ``gh issue view`` also answers for a pull request number, which only its URL tells apart.
    """
    issue = view_issue(number, ("state", "labels", "url", "author"))
    return IssueState(
        number=number,
        is_open=issue["state"] == "OPEN",
        is_pull_request="/pull/" in issue["url"],
        labels=label_names(issue),
        author=login(issue["author"]),
    )
