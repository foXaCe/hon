"""Tests for the hOn command model."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from custom_components.hon.command import HonCommand
from custom_components.hon.parameter import (
    HonParameterEnum,
    HonParameterFixed,
    HonParameterRange,
)


def base_attributes() -> dict:
    """Build command attributes covering the three parameter typologies."""
    return {
        "description": "A command",
        "parameters": {
            "tempSel": {
                "typology": "range",
                "minimumValue": "0",
                "maximumValue": "6",
                "incrementValue": "1",
                "defaultValue": "3",
            },
            "machMode": {"typology": "enum", "enumValues": ["1", "2"]},
            "lockStatus": {"typology": "fixed", "fixedValue": "0"},
        },
        "ancillaryParameters": {
            "channel": {"typology": "enum", "enumValues": ["mobileApp"]}
        },
    }


def make_command(**kwargs) -> HonCommand:
    """Build a command wired to mocked connector/device."""
    connector = MagicMock()
    connector.send_command = AsyncMock(return_value=True)
    return HonCommand(
        "startProgram", base_attributes(), connector, MagicMock(), **kwargs
    )


def test_command_creates_typed_parameters() -> None:
    """Parameters are created according to their typology."""
    command = make_command()
    assert isinstance(command.parameters["tempSel"], HonParameterRange)
    assert isinstance(command.parameters["machMode"], HonParameterEnum)
    assert isinstance(command.parameters["lockStatus"], HonParameterFixed)


def test_command_ancillary_parameters() -> None:
    """ancillary_parameters returns the current values."""
    command = make_command()
    assert command.ancillary_parameters == {"channel": "0"}


async def test_command_send() -> None:
    """send forwards the values through the connector."""
    connector = MagicMock()
    connector.send_command = AsyncMock(return_value=True)
    device = MagicMock()
    command = HonCommand("startProgram", base_attributes(), connector, device)

    assert await command.send() is True
    connector.send_command.assert_awaited_once_with(
        device,
        "startProgram",
        {"tempSel": 3, "machMode": "0", "lockStatus": "0"},
        {"channel": "0"},
    )


def test_command_get_programs() -> None:
    """get_programs returns the multi-program mapping."""
    command = make_command()
    assert command.get_programs() == {}


def test_command_set_program() -> None:
    """set_program swaps the active command in the device."""
    device = MagicMock()
    multi = {"eco": MagicMock(), "max": MagicMock()}
    connector = MagicMock()
    command = HonCommand(
        "startProgram", base_attributes(), connector, device, multi=multi
    )
    command.set_program("max")
    device.commands.__setitem__.assert_called_with("startProgram", multi["max"])


def test_command_setting_keys() -> None:
    """setting_keys excludes fixed parameters."""
    command = make_command()
    assert set(command.setting_keys) == {"tempSel", "machMode"}


def test_command_setting_keys_multi() -> None:
    """setting_keys for a multi-program command adds the program key."""
    multi = {"eco": MagicMock(), "max": MagicMock()}
    command = make_command(multi=multi)
    assert "program" in command.setting_keys


def test_command_settings_property() -> None:
    """settings exposes every non-fixed parameter."""
    command = make_command()
    settings = command.settings
    assert set(settings) == {"tempSel", "machMode"}


def test_command_repr() -> None:
    """The repr identifies the command."""
    command = make_command()
    assert repr(command) == "startProgram command"


def test_command_multi_settings_property() -> None:
    """settings for multi-program commands resolves shared parameters."""
    connector = MagicMock()
    device = MagicMock()
    program_attributes = {
        "parameters": {
            "tempSel": {
                "typology": "range",
                "minimumValue": "0",
                "maximumValue": "6",
                "incrementValue": "1",
                "defaultValue": "3",
            }
        }
    }
    eco = HonCommand("startProgram", program_attributes, connector, device)
    max_ = HonCommand("startProgram", program_attributes, connector, device)
    command = HonCommand(
        "startProgram",
        {"parameters": {}},
        connector,
        device,
        multi={"eco": eco, "max": max_},
    )
    settings = command.settings
    assert "tempSel" in settings
    assert "program" in settings


def test_command_dump() -> None:
    """dump returns a text description and an example dict."""
    command = make_command()
    text, example = command.dump()
    assert "tempSel" in text
    assert "machMode" in text
    assert "lockStatus" not in text
    assert example == "{'tempSel':3,'machMode':None}"
