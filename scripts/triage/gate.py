"""The triage gate: whether an event starts a triage run.

:func:`gate` is pure: an event and the issue's live :class:`~scripts.triage.issue.IssueState`
in, a run-or-skip verdict out. ``main`` is the gate step's wrapper: it validates the
consumer's model and turn-cap inputs with :mod:`scripts.triage.inputs`, then reads that live
state with ``gh``.
"""

import argparse
import os
import sys
from collections.abc import Sequence
from typing import Final, NamedTuple

from scripts.triage.inputs import InvalidInputError, validate_max_turns, validate_model
from scripts.triage.issue import IssueState, read_issue_state

NEEDS_TRIAGE: Final = "needs-triage"

_LABELED: Final = "labeled"
_TRIGGER_KINDS: Final = frozenset({_LABELED, "workflow_dispatch"})


class TriageEvent(NamedTuple):
    """The workflow event that may start a run.

    ``kind`` is the ``issues`` activity type (``labeled``, ``opened``, ...) or another event
    name (``workflow_dispatch``, ``issue_comment``). ``added_label`` is set only for
    ``labeled``.
    """

    kind: str
    issue_number: int
    added_label: str | None
    sender_is_bot: bool


class GateVerdict(NamedTuple):
    run: bool
    reason: str


def gate(event: TriageEvent, issue: IssueState) -> GateVerdict:
    """Decide whether *event* starts a triage run on *issue*.

    Every trigger, a dispatch included, needs the issue open, not a pull request, and
    carrying ``needs-triage`` live, so a dispatch is a retry and never a bypass.
    """
    if event.sender_is_bot:
        return GateVerdict(False, "the sender is a bot")
    if event.kind not in _TRIGGER_KINDS:
        return GateVerdict(False, f"{event.kind!r} events never start a triage run")
    if event.kind == _LABELED and event.added_label != NEEDS_TRIAGE:
        return GateVerdict(False, f"the added label is {event.added_label!r}, not {NEEDS_TRIAGE!r}")
    if issue.is_pull_request:
        return GateVerdict(False, f"#{issue.number} is a pull request")
    if not issue.is_open:
        return GateVerdict(False, f"#{issue.number} is closed")
    if NEEDS_TRIAGE not in issue.labels:
        return GateVerdict(False, f"#{issue.number} does not carry {NEEDS_TRIAGE!r}")
    return GateVerdict(True, f"#{issue.number} is open and carries {NEEDS_TRIAGE!r}")


def main(argv: Sequence[str] | None = None) -> None:
    """Gate one event: log the verdict and write the step's outputs to ``$GITHUB_OUTPUT``.

    The outputs are ``run=true|false`` and the validated ``model`` and ``max-turns``, so no
    event-supplied text reaches the outputs file. An invalid input exits non-zero before the
    issue is read, and nothing is written.
    """
    parser = argparse.ArgumentParser(description="Decide whether an event starts a triage run.")
    parser.add_argument("--event", required=True, help="issues activity type, or event name")
    parser.add_argument("--issue", required=True, type=int, help="the issue number")
    parser.add_argument("--label", help="the added label, for a labeled event")
    parser.add_argument("--sender-type", default="User", help="the event sender's type")
    parser.add_argument("--model", default="", help="the model input; empty means the default")
    parser.add_argument(
        "--max-turns", default="", help="the turn-cap input; empty means the default"
    )
    args = parser.parse_args(argv)

    try:
        model = validate_model(args.model)
        max_turns = validate_max_turns(args.max_turns)
    except InvalidInputError as error:
        sys.exit(f"triage gate: invalid input: {error}")

    event = TriageEvent(
        kind=args.event,
        issue_number=args.issue,
        added_label=args.label,
        sender_is_bot=args.sender_type == "Bot",
    )
    verdict = gate(event, read_issue_state(event.issue_number))

    print(f"triage gate: {'run' if verdict.run else 'skip'}: {verdict.reason}")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as outputs:
        outputs.write(f"run={'true' if verdict.run else 'false'}\n")
        outputs.write(f"model={model}\nmax-turns={max_turns}\n")


if __name__ == "__main__":
    main()
