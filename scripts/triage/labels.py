"""The triage labels: every label triage reads, adds or removes in a consumer's repo.

Consumers create these exact names (README.md, "Labels to create"); triage touches no other.
"""

from typing import Final

BUG: Final = "bug"
ENHANCEMENT: Final = "enhancement"

NEEDS_TRIAGE: Final = "needs-triage"
NEEDS_INFO: Final = "needs-info"
READY_FOR_AGENT: Final = "ready-for-agent"
READY_FOR_HUMAN: Final = "ready-for-human"

CATEGORY_LABELS: Final = frozenset({BUG, ENHANCEMENT})
"""An issue's kind; a triage decision picks exactly one."""

STATE_LABELS: Final = frozenset({NEEDS_TRIAGE, NEEDS_INFO, READY_FOR_AGENT, READY_FOR_HUMAN})
"""Where an issue stands in triage; a triage decision picks exactly one."""
