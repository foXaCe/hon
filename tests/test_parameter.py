"""Tests for the hOn command parameter models."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.hon.parameter import (
    HonParameter,
    HonParameterEnum,
    HonParameterFixed,
    HonParameterProgram,
    HonParameterRange,
)


def range_attributes(**overrides) -> dict:
    """Build integer range attributes with sensible defaults."""
    attrs = {
        "category": "cat",
        "typology": "range",
        "mandatory": True,
        "minimumValue": "0",
        "maximumValue": "6",
        "incrementValue": "1",
        "defaultValue": "3",
    }
    attrs.update(overrides)
    return attrs


def test_hon_parameter_base() -> None:
    """The base parameter exposes its attributes."""
    param = HonParameter("spinSpeed", {"category": "c", "typology": "t"})
    assert param.key == "spinSpeed"
    assert param.category == "c"
    assert param.typology == "t"
    assert param.mandatory is None
    assert param.value == ""


def test_hon_parameter_range_int() -> None:
    """Integer ranges expose min/max/step/default."""
    param = HonParameterRange("spinSpeed", range_attributes())
    assert param.min == 0
    assert param.max == 6
    assert param.step == 1
    assert param.default == 3
    assert param.value == 3


def test_hon_parameter_range_default_is_min() -> None:
    """A missing defaultValue falls back to the minimum."""
    attrs = range_attributes()
    del attrs["defaultValue"]
    param = HonParameterRange("spinSpeed", attrs)
    assert param.default == 0
    assert param.value == 0


def test_hon_parameter_range_float() -> None:
    """Comma-separated decimal ranges are parsed as floats."""
    param = HonParameterRange(
        "tempSel",
        range_attributes(
            minimumValue="0,5",
            maximumValue="6,5",
            incrementValue="0,5",
            defaultValue="1,0",
        ),
    )
    assert param.min == 0.5
    assert param.max == 6.5
    assert param.step == 0.5
    assert param.default == 1.0


def test_hon_parameter_range_set_valid() -> None:
    """A valid in-range step-matching value is accepted."""
    param = HonParameterRange("spinSpeed", range_attributes())
    param.value = 4
    assert param.value == 4


def test_hon_parameter_range_set_string() -> None:
    """String values are converted before validation."""
    param = HonParameterRange("tempSel", range_attributes())
    param.value = "2"
    assert param.value == 2


def test_hon_parameter_range_set_float_string() -> None:
    """Comma-separated strings are handled for float ranges."""
    param = HonParameterRange(
        "tempSel",
        range_attributes(minimumValue="0,5", maximumValue="6,5", incrementValue="0,5"),
    )
    param.value = "2,5"
    assert param.value == 2.5


def test_hon_parameter_range_set_out_of_range() -> None:
    """Out-of-range values raise ValueError."""
    param = HonParameterRange("spinSpeed", range_attributes())
    with pytest.raises(ValueError):
        param.value = 7


def test_hon_parameter_range_set_wrong_step() -> None:
    """Values not aligned with the step raise ValueError."""
    param = HonParameterRange(
        "spinSpeed",
        range_attributes(maximumValue="6", incrementValue="2"),
    )
    with pytest.raises(ValueError):
        param.value = 3


def test_hon_parameter_range_dump() -> None:
    """dump returns a human-readable description."""
    param = HonParameterRange("spinSpeed", range_attributes())
    assert "spinSpeed" in param.dump()
    assert "[0 - 6]" in param.dump()


def test_hon_parameter_enum() -> None:
    """Enums expose their allowed values sorted."""
    param = HonParameterEnum(
        "machMode", {"enumValues": ["3", "1", "2"], "defaultValue": "2"}
    )
    assert param.default == "2"
    assert param.values == ["1", "2", "3"]
    assert param.valuesBase == ["1", "2", "3"]
    assert param.value == "2"


def test_hon_parameter_enum_set_valid() -> None:
    """An allowed enum value is accepted."""
    param = HonParameterEnum("machMode", {"enumValues": ["1", "2"]})
    param.value = "1"
    assert param.value == "1"


def test_hon_parameter_enum_set_invalid() -> None:
    """A disallowed enum value raises ValueError."""
    param = HonParameterEnum("machMode", {"enumValues": ["1", "2"]})
    with pytest.raises(ValueError):
        param.value = "9"


def test_hon_parameter_enum_default_value_fallback() -> None:
    """Without a default the empty string value is kept."""
    param = HonParameterEnum("machMode", {"enumValues": ["2", "1"]})
    assert param.value == "0"


def test_hon_parameter_enum_dump() -> None:
    """dump lists the allowed values."""
    param = HonParameterEnum("machMode", {"enumValues": ["1", "2"]})
    assert param.dump() == "machMode: ['1', '2'] - Default: None"


def test_hon_parameter_fixed() -> None:
    """Fixed parameters report their immutable value."""
    param = HonParameterFixed("lockStatus", {"fixedValue": "5"})
    assert param.value == "5"


def test_hon_parameter_fixed_set_same_value() -> None:
    """Assigning the same value is allowed."""
    param = HonParameterFixed("lockStatus", {"fixedValue": "5"})
    param.value = "5"
    assert param.value == "5"


def test_hon_parameter_fixed_set_different() -> None:
    """Assigning a different value raises ValueError."""
    param = HonParameterFixed("lockStatus", {"fixedValue": "5"})
    with pytest.raises(ValueError):
        param.value = "6"


def test_hon_parameter_fixed_repr() -> None:
    """The repr identifies the fixed parameter."""
    param = HonParameterFixed("lockStatus", {"fixedValue": "5"})
    assert "lockStatus" in repr(param)
    assert "fixed" in repr(param)


def test_hon_parameter_program() -> None:
    """Program parameters delegate program selection to the command."""
    command = MagicMock()
    command._program = "eco"
    command._multi = {"eco": MagicMock(), "max": MagicMock()}
    param = HonParameterProgram("program", command)

    assert param.value == "eco"
    assert param.default == "eco"
    assert param.typology == "enum"
    assert param.values == ["eco", "max"]

    param.value = "max"
    command.set_program.assert_called_once_with("max")


def test_hon_parameter_program_invalid() -> None:
    """An unknown program raises ValueError."""
    command = MagicMock()
    command._program = "eco"
    command._multi = {"eco": MagicMock(), "max": MagicMock()}
    param = HonParameterProgram("program", command)
    with pytest.raises(ValueError):
        param.value = "unknown"
    command.set_program.assert_not_called()


def test_hon_parameter_range_value_none_returns_min() -> None:
    """A None value falls back to the range minimum."""
    param = HonParameterRange("spinSpeed", range_attributes())
    param._value = None
    assert param.value == 0


def test_hon_parameter_enum_repr() -> None:
    """The enum repr lists the allowed values."""
    param = HonParameterEnum("machMode", {"enumValues": ["1", "2"]})
    assert "machMode" in repr(param)
    assert "['1', '2']" in repr(param)


def test_hon_parameter_program_dump() -> None:
    """The program parameter dump reports the current program."""
    command = MagicMock()
    command._program = "eco"
    command._multi = {"eco": MagicMock(), "max": MagicMock()}
    param = HonParameterProgram("program", command)
    assert param.dump() == "program: eco"


def test_hon_parameter_range_repr() -> None:
    """The range repr lists the min/max bounds."""
    param = HonParameterRange("spinSpeed", range_attributes())
    assert "spinSpeed" in repr(param)
    assert "[0 - 6]" in repr(param)
