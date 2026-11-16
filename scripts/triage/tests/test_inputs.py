"""Tests for scripts.triage.inputs: the model and turn-cap inputs a consumer sets."""

import pytest

from scripts.triage.inputs import InvalidInputError, validate_max_turns, validate_model


@pytest.mark.parametrize("model", ["sonnet", "claude-opus-4-1", "claude-sonnet-4-5[1m]", "a_b.c"])
def test_a_model_name_is_accepted_as_given(model):
    assert validate_model(model) == model


@pytest.mark.parametrize(
    "model", ["son net", "sonnet#x", "'sonnet'", '"sonnet"', "$MODEL", "sonnet\n", "--max-turns"]
)
def test_a_model_name_with_a_shell_or_flag_character_is_rejected_naming_model(model):
    with pytest.raises(InvalidInputError, match="model"):
        validate_model(model)


def test_an_empty_model_means_sonnet():
    assert validate_model("") == "sonnet"


@pytest.mark.parametrize(("value", "turns"), [("1", 1), ("10", 10), ("50", 50)])
def test_a_turn_cap_from_1_to_50_is_accepted(value, turns):
    assert validate_max_turns(value) == turns


@pytest.mark.parametrize("value", ["0", "51", "-1", "1.5", "ten", " 5", "+5", "5_0", "\u0665"])
def test_a_turn_cap_that_is_not_a_whole_number_from_1_to_50_is_rejected_naming_max_turns(value):
    with pytest.raises(InvalidInputError, match="max-turns"):
        validate_max_turns(value)


def test_an_empty_turn_cap_means_10():
    assert validate_max_turns("") == 10
