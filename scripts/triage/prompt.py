"""The triage prompt: the committed generic prompt with the consumer's docs named in it.

:func:`render_prompt` is pure: the ``labels-doc`` and ``project-docs`` inputs in (empty when
the consumer left them unset), the prompt text out. ``main`` is the workflow step's wrapper,
which prints it.
"""

import argparse
from collections.abc import Sequence
from pathlib import Path
from string import Template
from typing import Final

DEFAULT_LABELS_DOC: Final = "docs/agents/triage-labels.md"
DEFAULT_PROJECT_DOCS: Final = ("GLOSSARY.md", "docs/domain.md", "docs/adr/")

_TEMPLATE: Final = Template(Path(__file__).with_name("prompt.md").read_text(encoding="utf-8"))
# The project docs are a list under step 1 of the prompt, indented to sit inside that step.
_DOC_ITEM: Final = "   - `{doc}`"


def render_prompt(*, labels_doc: str, project_docs: str) -> str:
    """Render the prompt naming *labels_doc* and each path in *project_docs*.

    *project_docs* is newline-separated; each line is stripped and blank lines are dropped. An
    input that is empty after that names the defaults instead.
    """
    docs = [line.strip() for line in project_docs.splitlines() if line.strip()]
    return _TEMPLATE.substitute(
        labels_doc=f"`{labels_doc.strip() or DEFAULT_LABELS_DOC}`",
        project_docs="\n".join(_DOC_ITEM.format(doc=doc) for doc in docs or DEFAULT_PROJECT_DOCS),
    )


def main(argv: Sequence[str] | None = None) -> None:
    """Print the triage prompt for the consumer's docs."""
    parser = argparse.ArgumentParser(description="Print the triage prompt.")
    parser.add_argument(
        "--labels-doc", default="", help=f"the labels doc (default {DEFAULT_LABELS_DOC})"
    )
    parser.add_argument(
        "--project-docs",
        default="",
        help=f"newline-separated project docs (default {', '.join(DEFAULT_PROJECT_DOCS)})",
    )
    args = parser.parse_args(argv)

    print(render_prompt(labels_doc=args.labels_doc, project_docs=args.project_docs), end="")


if __name__ == "__main__":
    main()
