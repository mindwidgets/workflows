"""Tests for the triage workflow file: its sandbox reaches the CLI, and its privilege shape.

The uv pin is checked in CI's workflow too, since both install uv the same way.

The workflow's ``claude_args`` goes through claude-code-action's own parser, after the
action's flags, so the tests read it from ``triage.yml`` and run it through a port of that
parser (``scripts.triage.tests.claude_code_action``) rather than a shell.
"""

import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

from scripts.triage.inputs import (
    DEFAULT_MAX_TURNS,
    DEFAULT_MODEL,
    MAX_TURNS_LIMIT,
    validate_max_turns,
    validate_model,
)
from scripts.triage.prompt import DEFAULT_LABELS_DOC, DEFAULT_PROJECT_DOCS
from scripts.triage.tests.claude_code_action import (
    SdkOptions,
    agent_mode_claude_args,
    parse_sdk_options,
    shell_quote_parse,
)

_ROOT = Path(__file__).resolve().parents[3]
_WORKFLOW_PATH = _ROOT / ".github" / "workflows" / "triage.yml"
_WORKFLOW_TEXT = _WORKFLOW_PATH.read_text(encoding="utf-8")
_WORKFLOW: dict[Any, Any] = yaml.safe_load(_WORKFLOW_TEXT)
_JOBS: dict[str, Any] = _WORKFLOW["jobs"]
_CI: dict[Any, Any] = yaml.safe_load(
    (_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
)
_SCHEMA = _ROOT / "scripts" / "triage" / "decision.schema.json"

_MODEL_EXPRESSION = "${{ needs.gate.outputs.model }}"
_MAX_TURNS_EXPRESSION = "${{ needs.gate.outputs.max-turns }}"
_SCHEMA_EXPRESSION = "${{ steps.load.outputs.schema }}"
_CLAUDE_SECRETS = ("CLAUDE_CODE_OAUTH_TOKEN", "ANTHROPIC_API_KEY")

# The shape of the action's own MCP config on an issue run; its content doesn't matter here.
_ACTION_MCP_CONFIG = json.dumps(
    {
        "mcpServers": {
            "github_comment": {
                "command": "bun",
                "args": ["run", "/home/runner/work/_actions/github-comment-server.ts"],
                "env": {"GITHUB_TOKEN": "ghs_placeholder", "REPO_OWNER": "owner"},
            }
        }
    }
)

# The workflow's settings input sets no permission mode, so the action prefixes auto mode.
_EACH_ACTION_PREFIX = pytest.mark.parametrize(
    "auto_mode", [True, False], ids=["auto mode and MCP config", "MCP config only"]
)
# The raw model and max-turns inputs: unset (the defaults), and values at the edges of what
# the gate's validation accepts.
_EACH_INPUT_SHAPE = pytest.mark.parametrize(
    ("model_input", "max_turns_input"),
    [
        ("", ""),
        ("a", "1"),
        ("claude-sonnet-4-5[1m]", str(MAX_TURNS_LIMIT)),
        ("9]._-[Z", "09"),
    ],
    ids=["defaults", "shortest", "longest turn cap", "every model character"],
)


def _workflow_claude_args() -> str:
    (step,) = (step for step in _JOBS["triage"]["steps"] if step.get("id") == "claude")
    claude_args: str = step["with"]["claude_args"]
    return claude_args


def _decision_schema() -> dict[str, Any]:
    """The committed decision schema without ``$schema``, as the load step sends it."""
    schema: dict[str, Any] = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    del schema["$schema"]
    return schema


def _schema_as_the_load_step_writes_it() -> str:
    """``jq -c 'del(.["$schema"])'``, then every apostrophe as ``\\u0027``."""
    compact = json.dumps(_decision_schema(), separators=(",", ":"), ensure_ascii=False)
    return compact.replace("'", "\\u0027")


def _substitute(claude_args: str, model: str, max_turns: int) -> str:
    """*claude_args* with each expression replaced as the runner would fill it in."""
    for expression, value in (
        (_MODEL_EXPRESSION, model),
        (_MAX_TURNS_EXPRESSION, str(max_turns)),
        (_SCHEMA_EXPRESSION, _schema_as_the_load_step_writes_it()),
    ):
        assert expression in claude_args
        claude_args = claude_args.replace(expression, value)
    return claude_args


def _options(
    auto_mode: bool, model: str, max_turns: int, claude_args: str | None = None
) -> SdkOptions:
    user_args = _substitute(claude_args or _workflow_claude_args(), model, max_turns)
    return parse_sdk_options(agent_mode_claude_args(user_args, _ACTION_MCP_CONFIG, auto_mode))


@_EACH_ACTION_PREFIX
@_EACH_INPUT_SHAPE
def test_the_validated_model_and_turn_cap_reach_the_cli(auto_mode, model_input, max_turns_input):
    model, max_turns = validate_model(model_input), validate_max_turns(max_turns_input)

    options = _options(auto_mode, model, max_turns)

    assert (options.model, options.max_turns) == (model, max_turns)


def test_unset_inputs_give_sonnet_and_10_turns():
    options = _options(True, validate_model(""), validate_max_turns(""))

    assert (
        (options.model, options.max_turns) == (DEFAULT_MODEL, DEFAULT_MAX_TURNS) == ("sonnet", 10)
    )


@_EACH_ACTION_PREFIX
@_EACH_INPUT_SHAPE
def test_the_whole_sandbox_reaches_the_cli(auto_mode, model_input, max_turns_input):
    required_denies = {
        *("Bash", "Edit", "MultiEdit", "Write", "NotebookEdit", "WebFetch", "WebSearch"),
        *("mcp__github", "mcp__github_comment", "mcp__github_file_ops"),
        *("mcp__github_inline_comment", "mcp__github_ci"),
        *("Agent", "Task", "Skill", "Workflow", "CronCreate", "RemoteTrigger"),
        *("ScheduleWakeup", "SendMessage", "PushNotification", "EnterWorktree"),
        *("Read(//proc/**)", "Read(//sys/**)", "Read(//dev/**)", "Read(//etc/**)"),
        *("Read(//tmp/**)", "Read(//var/**)", "Read(//run/**)", "Read(//root/**)"),
        *("Read(//opt/**)", "Read(//usr/**)", "Read(~/.*)", "Read(~/.*/**)"),
        *("Read(~/work/_temp/**)", "Read(~/work/_actions/**)", "Read(~/work/_tool/**)"),
        *("Read(~/actions-runner/**)", "Read(~/runners/**)"),
    }

    options = _options(auto_mode, validate_model(model_input), validate_max_turns(max_turns_input))

    assert options.setting_sources == ["user"]
    assert options.permission_mode == "dontAsk"
    assert options.allowed_tools == ["Read(./**)"]
    assert options.disallowed_tools is not None
    assert required_denies <= set(options.disallowed_tools)
    assert options.has_json_schema
    assert json.loads(options.extra_args["json-schema"] or "") == _decision_schema()


@_EACH_INPUT_SHAPE
def test_claude_args_holds_no_shell_comment(model_input, max_turns_input):
    # Stricter than the action, which strips whole-line comments first: no comment at all.
    claude_args = _substitute(
        _workflow_claude_args(), validate_model(model_input), validate_max_turns(max_turns_input)
    )

    tokens = shell_quote_parse(claude_args)

    assert [token for token in tokens if isinstance(token, dict) and "comment" in token] == []


def test_a_comment_on_the_first_line_drops_every_later_flag():
    # The bug the two tests above guard against: the action's prefix turns a whole-line
    # comment into a mid-line one, which ends the input.
    commented = "# the sandbox\n" + _workflow_claude_args()

    options = _options(True, DEFAULT_MODEL, DEFAULT_MAX_TURNS, commented)

    assert (options.model, options.allowed_tools, options.has_json_schema) == (None, None, False)


_MODEL_CHARACTERS = "ABCXYZabcxyz0189._-[]"


@pytest.mark.parametrize(
    "model",
    [
        *(f"a{char}" for char in _MODEL_CHARACTERS),
        *(f"0{char}9" for char in _MODEL_CHARACTERS),
        "a" + _MODEL_CHARACTERS,
        "claude-sonnet-4-5[1m]",
    ],
)
def test_every_accepted_model_is_one_shell_word_without_a_hash(model):
    assert validate_model(model) == model
    assert shell_quote_parse(model) == [model]
    assert "#" not in model


@pytest.mark.parametrize("value", [str(turns) for turns in range(1, MAX_TURNS_LIMIT + 1)])
def test_every_accepted_turn_cap_is_one_shell_word_without_a_hash(value):
    turns = str(validate_max_turns(value))

    assert shell_quote_parse(turns) == [turns]
    assert "#" not in turns


def _strings_in(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [text for item in value.values() for text in _strings_in(item)]
    if isinstance(value, list):
        return [text for item in value for text in _strings_in(item)]
    return []


def test_the_workflow_grants_no_permission_of_its_own():
    assert _WORKFLOW["permissions"] == {}


@pytest.mark.parametrize(
    ("job", "permissions"),
    [
        ("gate", {"contents": "read", "issues": "read"}),
        ("triage", {"contents": "read", "issues": "read"}),
        ("apply", {"contents": "read", "issues": "write"}),
    ],
)
def test_each_job_holds_only_the_permissions_it_uses(job, permissions):
    assert _JOBS[job]["permissions"] == permissions


def test_the_three_jobs_are_gate_triage_and_apply():
    assert set(_JOBS) == {"gate", "triage", "apply"}


@pytest.mark.parametrize("job", sorted(_JOBS))
def test_only_the_triage_job_references_a_secret(job):
    references = [text for text in _strings_in(_JOBS[job]) if "secrets." in text]

    if job == "triage":
        assert {
            name for name in _CLAUDE_SECRETS if any(name in text for text in references)
        } == set(_CLAUDE_SECRETS)
    else:
        assert references == []


def test_nothing_outside_the_jobs_references_a_secret():
    outside = {key: value for key, value in _WORKFLOW.items() if key not in ("jobs", True)}

    assert [text for text in _strings_in(outside) if "secrets." in text] == []


@pytest.mark.parametrize("job", sorted(_JOBS))
def test_every_job_has_a_timeout_and_no_concurrency(job):
    assert isinstance(_JOBS[job]["timeout-minutes"], int)
    assert "concurrency" not in _JOBS[job]


def test_the_workflow_sets_no_concurrency():
    assert "concurrency" not in _WORKFLOW


def _checkouts(job: str) -> list[dict[str, Any]]:
    return [
        step.get("with", {})
        for step in _JOBS[job]["steps"]
        if step.get("uses", "").startswith("actions/checkout@")
    ]


@pytest.mark.parametrize("job", sorted(_JOBS))
def test_every_job_makes_the_tools_checkout_at_the_pinned_commit(job):
    tools = [
        checkout
        for checkout in _checkouts(job)
        if checkout.get("repository") == "${{ job.workflow_repository }}"
    ]

    assert [checkout.get("ref") for checkout in tools] == ["${{ job.workflow_sha }}"]


@pytest.mark.parametrize("job", sorted(_JOBS))
def test_every_checkout_drops_its_credentials_and_uses_the_default_token(job):
    for checkout in _checkouts(job):
        assert checkout["persist-credentials"] is False
        assert "token" not in checkout


def _run_steps() -> list[tuple[str, dict[str, Any]]]:
    return [(job, step) for job in _JOBS for step in _JOBS[job]["steps"] if "run" in step]


@pytest.mark.parametrize(
    ("job", "step"), _run_steps(), ids=[step.get("name", "run") for _, step in _run_steps()]
)
def test_no_run_script_holds_an_expression(job, step):
    # Stricter than the rule, which bans expressions with event data: none at all, so values
    # always arrive through env and are read as quoted shell variables.
    assert "${{" not in step["run"]


def test_the_triage_job_runs_scripts_only_from_the_tools_checkout_moved_out_of_claudes_reach():
    steps = _JOBS["triage"]["steps"]
    tools = "${{ runner.temp }}/triage-tools"
    move = next(i for i, step in enumerate(steps) if "mv " in step.get("run", ""))
    claude = next(i for i, step in enumerate(steps) if step.get("id") == "claude")
    script_steps = [step for step in steps if "python" in step.get("run", "")]
    (setup_uv,) = (step for step in steps if step.get("uses", "").startswith("astral-sh/setup-uv@"))

    assert move < claude
    assert steps[move]["run"].endswith('"$RUNNER_TEMP/triage-tools"')
    assert script_steps
    assert all(step.get("working-directory") == tools for step in script_steps)
    assert setup_uv["with"]["enable-cache"] is False
    assert setup_uv["with"]["working-directory"] == tools


def test_every_action_is_pinned_to_a_full_commit_sha():
    uses = [step["uses"] for job in _JOBS.values() for step in job["steps"] if "uses" in step]

    assert uses
    assert [use for use in uses if not re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", use)] == []


def _interface() -> dict[str, Any]:
    interface: dict[str, Any] = _WORKFLOW[True]["workflow_call"]
    return interface


def test_the_workflow_is_only_callable():
    assert set(_WORKFLOW[True]) == {"workflow_call"}


def test_the_inputs_are_the_docs_model_and_turn_cap_with_their_defaults():
    inputs = _interface()["inputs"]

    assert {name: (spec["type"], spec["default"]) for name, spec in inputs.items()} == {
        "labels-doc": ("string", DEFAULT_LABELS_DOC),
        "project-docs": ("string", "".join(f"{doc}\n" for doc in DEFAULT_PROJECT_DOCS)),
        "model": ("string", DEFAULT_MODEL),
        "max-turns": ("number", DEFAULT_MAX_TURNS),
    }
    assert not any(spec.get("required") for spec in inputs.values())


def test_the_secrets_are_the_two_optional_claude_credentials():
    secrets = _interface()["secrets"]

    assert set(secrets) == set(_CLAUDE_SECRETS)
    assert not any(spec.get("required") for spec in secrets.values())


def _header_comment() -> str:
    lines = _WORKFLOW_TEXT.splitlines()
    return "\n".join(line for line in lines[: lines.index("on:")] if line.startswith("#"))


@pytest.mark.parametrize(
    "documented",
    [
        *_interface()["inputs"],
        *_CLAUDE_SECRETS,
        "contents: read, issues: write",
        "types [labeled]",
        "workflow_dispatch",
        "named `issue`",
        "Concurrency",
    ],
)
def test_the_header_comment_documents_the_interface(documented):
    assert documented in _header_comment()


def test_the_gate_job_outputs_only_what_the_gate_step_validated():
    # claude_args trusts these outputs as validated: one wired to inputs.* would bypass the gate.
    assert _JOBS["gate"]["outputs"] == {
        "run": "${{ steps.gate.outputs.run }}",
        "model": "${{ steps.gate.outputs.model }}",
        "max-turns": "${{ steps.gate.outputs.max-turns }}",
    }


def test_the_gate_step_validates_the_callers_model_and_turn_cap():
    (step,) = (step for step in _JOBS["gate"]["steps"] if step.get("id") == "gate")
    words = shlex.split(step["run"])

    assert words[words.index("-m") + 1] == "scripts.triage.gate"
    assert (step["env"]["MODEL"], step["env"]["MAX_TURNS"]) == (
        "${{ inputs.model }}",
        "${{ inputs.max-turns }}",
    )
    assert words[words.index("--model") + 1] == "$MODEL"
    assert words[words.index("--max-turns") + 1] == "$MAX_TURNS"


def _tools_commit_check(job: str) -> dict[str, Any]:
    step: dict[str, Any] = _JOBS[job]["steps"][0]
    return step


@pytest.mark.parametrize("job", sorted(_JOBS))
def test_every_job_first_reads_the_tools_commit_from_the_job_context(job):
    assert _tools_commit_check(job)["env"] == {
        "WORKFLOW_REPOSITORY": "${{ job.workflow_repository }}",
        "WORKFLOW_SHA": "${{ job.workflow_sha }}",
    }


def _run_tools_commit_check(job: str, repository: str, sha: str) -> int:
    env = {"PATH": os.environ["PATH"], "WORKFLOW_REPOSITORY": repository, "WORKFLOW_SHA": sha}
    script = _tools_commit_check(job)["run"]
    return subprocess.run(["bash", "-c", script], env=env, capture_output=True).returncode


@pytest.mark.parametrize("job", sorted(_JOBS))
@pytest.mark.parametrize(
    ("repository", "sha"),
    [("", "0" * 40), ("mindwidgets/workflows", ""), ("", "")],
    ids=["no repository", "no sha", "neither"],
)
def test_every_job_fails_before_the_tools_checkout_when_the_job_context_is_empty(
    job, repository, sha
):
    # An empty value would make actions/checkout fall back to the consumer's repo and ref.
    assert _run_tools_commit_check(job, repository, sha) != 0


@pytest.mark.parametrize("job", sorted(_JOBS))
def test_every_job_goes_on_when_the_job_context_names_the_tools_commit(job):
    assert _run_tools_commit_check(job, "mindwidgets/workflows", "0" * 40) == 0


def _setup_uv_steps() -> list[tuple[str, dict[str, Any]]]:
    return [
        (f"{file} {job_name}", step)
        for file, workflow in (("triage.yml", _WORKFLOW), ("ci.yml", _CI))
        for job_name, job in workflow["jobs"].items()
        for step in job["steps"]
        if step.get("uses", "").startswith("astral-sh/setup-uv@")
    ]


def test_triage_and_ci_install_uv_in_every_job_that_runs_a_script():
    assert sorted(where for where, _ in _setup_uv_steps()) == [
        "ci.yml check",
        "triage.yml apply",
        "triage.yml gate",
        "triage.yml triage",
    ]


@pytest.mark.parametrize(
    ("where", "step"), _setup_uv_steps(), ids=[where for where, _ in _setup_uv_steps()]
)
def test_every_setup_uv_step_installs_an_exact_uv_release_checked_against_its_checksum(where, step):
    # Without a version, setup-uv installs whatever uv is newest at run time.
    assert re.fullmatch(r"\d+\.\d+\.\d+", str(step["with"].get("version")))
    assert re.fullmatch(r"[0-9a-f]{64}", str(step["with"].get("checksum")))


def test_every_setup_uv_step_installs_the_same_uv_build():
    builds = {
        (step["with"].get("version"), step["with"].get("checksum")) for _, step in _setup_uv_steps()
    }

    assert len(builds) == 1


@pytest.mark.parametrize("workflow", [_WORKFLOW, _CI], ids=["triage.yml", "ci.yml"])
def test_uv_runs_only_the_python_build_its_pinned_release_names(workflow):
    # A Python already on the runner image would otherwise win over the pinned uv's own build.
    assert workflow["env"]["UV_PYTHON_PREFERENCE"] == "only-managed"
