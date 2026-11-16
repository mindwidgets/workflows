"""The triage package is shared by every consumer, so no file in it names one."""

import re
from pathlib import Path

import pytest

_PACKAGE = Path(__file__).parents[1]

# Built from parts, so this file doesn't trip its own check.
_CONSUMER_NAMES = re.compile(
    "|".join(["au" + "ra", "/us" + "ers/", "/ho" + "me/", "~" + "/"]), re.IGNORECASE
)

_FILES = sorted(
    path
    for path in _PACKAGE.rglob("*")
    if path.is_file() and path.suffix in {".py", ".json", ".md"}
)


@pytest.mark.parametrize("path", _FILES, ids=lambda path: str(path.relative_to(_PACKAGE)))
def test_no_package_file_names_a_consumer_or_a_local_path(path):
    assert not _CONSUMER_NAMES.findall(path.read_text(encoding="utf-8"))
