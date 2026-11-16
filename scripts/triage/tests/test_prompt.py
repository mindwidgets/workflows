"""Tests for scripts.triage.prompt: the triage prompt rendered with a consumer's docs."""

import json

import pytest

from scripts.triage.apply import DECISION_SCHEMA
from scripts.triage.issue_input import INPUT_PATH
from scripts.triage.prompt import main, render_prompt

_SCHEMA = json.loads(DECISION_SCHEMA.read_text(encoding="utf-8"))


def test_with_both_inputs_unset_the_prompt_names_the_default_docs():
    prompt = render_prompt(labels_doc="", project_docs="")

    for doc in ["docs/agents/triage-labels.md", "GLOSSARY.md", "docs/domain.md", "docs/adr/"]:
        assert f"`{doc}`" in prompt


def test_the_prompt_names_the_configured_labels_doc_instead_of_the_default():
    prompt = render_prompt(labels_doc="LABELS.md", project_docs="")

    assert "`LABELS.md`" in prompt
    assert "triage-labels.md" not in prompt


def test_the_prompt_names_every_configured_project_doc_and_no_default():
    prompt = render_prompt(
        labels_doc="", project_docs="CONTEXT.md\n  docs/architecture.md\n\ndecisions/\n"
    )

    for doc in ["CONTEXT.md", "docs/architecture.md", "decisions/"]:
        assert f"`{doc}`" in prompt
    for default in ["GLOSSARY.md", "docs/domain.md", "docs/adr/"]:
        assert default not in prompt


def test_the_prompt_names_the_input_file_and_frames_it_as_untrusted():
    prompt = render_prompt(labels_doc="", project_docs="")

    assert f"`{INPUT_PATH}`" in prompt
    assert "untrusted data" in prompt


@pytest.mark.parametrize(
    "value",
    _SCHEMA["properties"]["category"]["enum"] + _SCHEMA["properties"]["state"]["enum"],
)
def test_the_prompt_offers_every_category_and_state_the_schema_allows(value):
    assert f"`{value}`" in render_prompt(labels_doc="", project_docs="")


@pytest.mark.parametrize("field", list(_SCHEMA["properties"]))
def test_the_prompt_describes_every_decision_field(field):
    assert f"`{field}`" in render_prompt(labels_doc="", project_docs="")


def test_the_prompt_carries_the_needs_info_template():
    prompt = render_prompt(labels_doc="", project_docs="")

    assert "## Triage Notes" in prompt
    assert "**What we still need from you" in prompt


def test_the_prompt_carries_the_agent_brief_format():
    prompt = render_prompt(labels_doc="", project_docs="")

    assert "## Agent Brief" in prompt
    assert "**Acceptance criteria:**" in prompt
    assert "**Files to start from:**" in prompt


def test_the_command_prints_the_rendered_prompt(capsys):
    main(["--labels-doc", "LABELS.md", "--project-docs", "CONTEXT.md"])

    assert capsys.readouterr().out == render_prompt(
        labels_doc="LABELS.md", project_docs="CONTEXT.md"
    )
