"""The model and turn-cap inputs a consumer sets, validated before they reach ``claude_args``.

Both functions are pure: the raw input string in (empty when the consumer left it unset), the
value to pass to Claude out, or :class:`InvalidInputError` naming the input. Every value they
return is one shell word with no ``#``, so it cannot split a ``claude_args`` line or end it early.
"""

import re
from typing import Final

DEFAULT_MODEL: Final = "sonnet"
DEFAULT_MAX_TURNS: Final = 10
MAX_TURNS_LIMIT: Final = 50

# Letters, digits, `.`, `-`, `_` and the brackets of a suffix like `[1m]`, starting with a
# letter or digit so a value can't pass for a flag.
_MODEL: Final = re.compile(r"[A-Za-z0-9][A-Za-z0-9._\[\]-]*")
# ASCII digits only: int() alone would also take "+5", " 5", "5_0" and other scripts' digits.
_DIGITS: Final = re.compile(r"[0-9]+")


class InvalidInputError(ValueError):
    """A consumer input that triage refuses to run with; the message names the input."""


def validate_model(value: str) -> str:
    """Return the model *value* names, or the default when it is empty."""
    if not value:
        return DEFAULT_MODEL
    if not _MODEL.fullmatch(value):
        raise InvalidInputError(
            f"model {value!r} is not a model name: use letters, digits, '.', '-', '_', '[' and "
            "']', starting with a letter or digit"
        )
    return value


def validate_max_turns(value: str) -> int:
    """Return the turn cap *value* names, or the default when it is empty."""
    if not value:
        return DEFAULT_MAX_TURNS
    if not _DIGITS.fullmatch(value) or not 1 <= int(value) <= MAX_TURNS_LIMIT:
        raise InvalidInputError(
            f"max-turns {value!r} is not a whole number from 1 to {MAX_TURNS_LIMIT}"
        )
    return int(value)
