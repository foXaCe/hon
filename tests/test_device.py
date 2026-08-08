"""Tests for the hOn device model."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hon.const import DOMAIN
from custom_components.hon.devices.device import HonDevice
from custom_components.hon.parameter import HonParameterRange
from tests.conftest import MAC, build_appliance


@pytest.fixture
def device(hass, mock_connection, appliance) -> HonDevice:
    """A HonDevice built over the mocked connection."""
    coordinator = MagicMock()
    return HonDevice(mock_connection, coordinator, appliance)


def test_device_getitem_plain(device) -> None:
    """__getitem__ reads plain keys from data/parameters/appliance."""
    device.attributes["parameters"] = {"tempSel": "40"}
    assert device["tempSel"] == "40"
    assert device["macAddress"] == MAC


def test_device_getitem_dotted(device) -> None:
    """__getitem__ walks dotted paths and indexes lists."""
    device.attributes["lastConnEvent"] = {"category": "CONNECTED"}
    assert device["attributes.lastConnEvent.category"] == "CONNECTED"
    device.attributes["errors"] = ["E1", "E2"]
    assert device["attributes.errors.1"] == "E2"


def test_device_getitem_missing_raises(device) -> None:
    """__getitem__ raises KeyError for unknown keys."""
    with pytest.raises(KeyError):
        device["nope"]


def test_device_set_and_get(device) -> None:
    """set persists values in the mutable parameters store."""
    device.attributes["parameters"] = {"tempSel": "40"}
    device.set("tempSel", "50")
    assert device.get("tempSel") == "50"

    device.set("serialNumber", "SN-2")
    assert device.get("serialNumber") == "SN-2"


def test_device_get_default(device) -> None:
    """get returns the default when the key is missing."""
    assert device.get("missing", "fallback") == "fallback"
    assert device.get("missing") is None


def test_device_get_int_float_has(device) -> None:
    """getInt/getFloat convert values; has reports presence."""
    device.attributes["parameters"] = {"tempSel": "40"}
    assert device.getInt("tempSel") == 40
    assert device.getFloat("tempSel") == 40.0
    assert device.has("tempSel") is True
    assert device.has("missing") is False


def test_device_properties(device) -> None:
    """The device exposes its identity and data properties."""
    assert device.appliance_type == "WM"
    assert device.mac_address == MAC
    assert device.model_name == "HW100-B14959U1FR"
    assert device.name == "Lave-linge"
    assert device.appliance == build_appliance()
    assert device.attributes == {}
    assert device.statistics == {}
    assert device.commands == {}
    assert device.commands_options is None


async def test_device_load_context(device, mock_connection) -> None:
    """load_context merges the shadow parameters into attributes."""
    mock_connection.async_get_context = AsyncMock(
        return_value={"shadow": {"parameters": {"onOffStatus": {"parNewVal": "1"}}}}
    )
    await device.load_context()
    assert device.attributes["parameters"]["onOffStatus"] == "1"


async def test_device_load_context_no_shadow(device, mock_connection) -> None:
    """load_context keeps attributes empty without shadow data."""
    mock_connection.async_get_context = AsyncMock(return_value={"other": 1})
    await device.load_context()
    assert "parameters" not in device.attributes


async def test_device_load_context_no_parameters(device, mock_connection) -> None:
    """load_context keeps attributes empty without shadow parameters."""
    mock_connection.async_get_context = AsyncMock(
        return_value={"shadow": {"something": 1}}
    )
    await device.load_context()
    assert "parameters" not in device.attributes


def test_device_getitem_data_branch(device) -> None:
    """__getitem__ reads top-level data keys like appliance and attributes."""
    assert device["appliance"] is device.appliance
    assert device["attributes"] is device.attributes
    assert device["statistics"] is device.statistics


def test_device_set_data_branch(device) -> None:
    """set accepts data-backed keys (note: does not persist — source bug)."""
    device.set("appliance", {"x": 1})
    assert device.appliance["macAddress"] == MAC


def test_device_get_program_name_short(device) -> None:
    """getProgramName returns the raw name when it has no 3-part shape."""
    device.attributes["programName"] = "cotton"
    assert device.getProgramName() == "cotton"


def test_device_get_program_name_short_activity(device) -> None:
    """getProgramName handles a short activity program name."""
    device.attributes["activity"] = {"attributes": {"programName": "cotton"}}
    assert device.getProgramName() == "cotton"


def test_device_get_program_name_short_history(device) -> None:
    """getProgramName handles a short command-history program name."""
    device.attributes["commandHistory"] = {"command": {"programName": "cotton"}}
    assert device.getProgramName() == "cotton"


def test_device_settings_property(device) -> None:
    """settings flattens command settings under dotted keys."""
    command = MagicMock()
    command.settings = {
        "tempSel": HonParameterRange(
            "tempSel",
            {
                "minimumValue": "0",
                "maximumValue": "6",
                "incrementValue": "1",
                "defaultValue": "4",
            },
        )
    }
    device._commands = {"startProgram": command}
    assert "startProgram.tempSel" in device.settings


def test_device_update_command_unchanged(device) -> None:
    """update_command skips parameters already at the target value."""
    param = HonParameterRange(
        "tempSel",
        {
            "minimumValue": "0",
            "maximumValue": "6",
            "incrementValue": "1",
            "defaultValue": "3",
        },
    )
    command = MagicMock()
    command.parameters = {"tempSel": param}
    device.update_command(command, {"tempSel": 3})
    assert param.value == 3


def test_device_update_command_fallback_failure(device) -> None:
    """update_command swallows a failing fallback to the default."""

    class Unsettable:
        default = "d"

        def __init__(self) -> None:
            self._v = 0

        @property
        def value(self):
            return self._v

        @value.setter
        def value(self, value):
            raise ValueError("boom")

    command = MagicMock()
    command.parameters = {"k": Unsettable()}
    device.update_command(command, {"k": "new"})


def test_device_update_command_fallback(device) -> None:
    """update_command falls back to the default on invalid values."""
    param = HonParameterRange(
        "tempSel",
        {
            "minimumValue": "0",
            "maximumValue": "6",
            "incrementValue": "1",
            "defaultValue": "3",
        },
    )
    command = MagicMock()
    command.parameters = {"tempSel": param}
    device.update_command(command, {"tempSel": "99"})
    assert param.value == 3


def test_device_settings_command_writes_attributes(device) -> None:
    """settings_command mirrors command values into the attributes."""
    command = MagicMock()
    param = HonParameterRange(
        "tempSel",
        {
            "minimumValue": "0",
            "maximumValue": "6",
            "incrementValue": "1",
            "defaultValue": "3",
        },
    )
    command.parameters = {"tempSel": param}
    device._commands = {"settings": command}
    result = device.settings_command({"tempSel": "5"})
    assert result is command
    assert device.attributes["parameters"]["tempSel"] == 5


def test_device_start_command_writes_attributes(device) -> None:
    """start_command mirrors command values into the attributes."""
    command = MagicMock()
    param = HonParameterRange(
        "tempSel",
        {
            "minimumValue": "0",
            "maximumValue": "6",
            "incrementValue": "1",
            "defaultValue": "3",
        },
    )
    command.parameters = {"tempSel": param}
    device._commands = {"startProgram": command}
    device.start_command(parameters={"tempSel": "5"})
    assert device.attributes["parameters"]["tempSel"] == 5


def test_device_data_combined(device) -> None:
    """data combines attributes, appliance, statistics and parameters."""
    device.attributes["parameters"] = {"tempSel": "40"}
    data = device.data
    assert data["attributes"] is device.attributes
    assert data["appliance"] is device.appliance
    assert data["statistics"] is device.statistics
    assert data["attributes"]["parameters"]["tempSel"] == "40"


def test_device_get_program_name_from_activity(device) -> None:
    """getProgramName reads activity.attributes.programName first."""
    device.attributes["activity"] = {
        "attributes": {"programName": "PROGRAMS.WM.cotton"}
    }
    assert device.getProgramName() == "cotton"


def test_device_get_program_name_from_attributes(device) -> None:
    """getProgramName falls back to the direct programName attribute."""
    device.attributes["programName"] = "PROGRAMS.WM.cotton"
    assert device.getProgramName() == "cotton"


def test_device_get_program_name_from_command_history(device) -> None:
    """getProgramName falls back to the command history."""
    device.attributes["commandHistory"] = {
        "command": {"programName": "PROGRAMS.WM.cotton"}
    }
    assert device.getProgramName() == "cotton"


def test_device_get_program_name_unknown(device) -> None:
    """getProgramName returns None when nothing matches."""
    assert device.getProgramName() is None


def test_device_get_program_name_exception(device) -> None:
    """getProgramName returns None when the payload is malformed."""
    device.attributes["activity"] = "not-a-dict"
    assert device.getProgramName() is None


def test_device_update_command(device) -> None:
    """update_command applies values and skips fixed parameters."""
    command = MagicMock()
    param = HonParameterRange(
        "tempSel",
        {
            "minimumValue": "0",
            "maximumValue": "6",
            "incrementValue": "1",
            "defaultValue": "3",
        },
    )
    command.parameters = {"tempSel": param}
    device.update_command(command, {"tempSel": "5"})
    assert param.value == 5


def test_device_update_command_skip_fixed(device) -> None:
    """update_command never touches fixed parameters."""
    from custom_components.hon.parameter import HonParameterFixed

    command = MagicMock()
    real_fixed = HonParameterFixed("lockStatus", {"fixedValue": "0"})
    command.parameters = {"lockStatus": real_fixed}
    device.update_command(command, {"lockStatus": "1"})
    assert real_fixed.value == "0"


def test_device_settings_command(device) -> None:
    """settings_command updates and returns the settings command."""
    command = MagicMock()
    device._commands = {"settings": command}
    command.parameters = {}
    device.attributes["parameters"] = {}
    result = device.settings_command({"onOffStatus": "1"})
    assert result is command


def test_device_settings_command_missing(device) -> None:
    """settings_command raises when no settings command exists."""
    with pytest.raises(ValueError):
        device.settings_command()


def test_device_start_command(device) -> None:
    """start_command selects a program and updates the command."""
    command = MagicMock()
    device._commands = {"startProgram": command}
    command.parameters = {}
    device.attributes["parameters"] = {}
    result = device.start_command("cotton", {"onOffStatus": "1"})
    assert result is device._commands["startProgram"]


def test_device_start_command_missing(device) -> None:
    """start_command raises when no start command exists."""
    with pytest.raises(ValueError):
        device.start_command()


def test_device_stop_command(device) -> None:
    """stop_command returns the stop command when present."""
    command = MagicMock()
    command.parameters = {}
    device._commands = {"stopProgram": command}
    device.attributes["parameters"] = {}
    assert device.stop_command() is command


def test_device_stop_command_missing(device) -> None:
    """stop_command raises when no stop command exists."""
    with pytest.raises(ValueError):
        device.stop_command()


def test_device_get_setting(device) -> None:
    """get_setting resolves a dotted setting key."""
    command = MagicMock()
    command.settings = {"tempSel": "param"}
    device._commands = {"settings": command}
    assert device.get_setting("settings.tempSel") == "param"
    assert device.get_setting("missing.tempSel") is None


def test_device_has_current_setting(device) -> None:
    """has_current_setting checks the command parameters."""
    command = MagicMock()
    command.parameters = {"tempSel": MagicMock()}
    device._commands = {"settings": command}
    assert device.has_current_setting("settings.tempSel") is True
    assert device.has_current_setting("settings.other") is False
    assert device.has_current_setting("missing.tempSel") is False


async def test_device_load_commands_simple(device, mock_connection) -> None:
    """load_commands parses simple commands with parameters."""
    mock_connection.load_commands = AsyncMock(
        return_value={
            "applianceModel": {"options": {"op": 1}},
            "options": {},
            "dictionaryId": {},
            "startProgram": {
                "parameters": {"onOffStatus": {"typology": "enum", "enumValues": ["1"]}}
            },
        }
    )
    await device.load_commands()
    assert "startProgram" in device.commands
    assert device.commands_options == {"op": 1}


async def test_device_load_commands_set_parameters(device, mock_connection) -> None:
    """load_commands handles the setParameters shape."""
    mock_connection.load_commands = AsyncMock(
        return_value={
            "applianceModel": {"options": {}},
            "options": {},
            "dictionaryId": {},
            "settings": {
                "setParameters": {
                    "parameters": {
                        "tempSel": {
                            "typology": "range",
                            "minimumValue": "0",
                            "maximumValue": "6",
                            "incrementValue": "1",
                        }
                    }
                }
            },
        }
    )
    await device.load_commands()
    assert "settings" in device.commands


async def test_device_load_commands_multi(device, mock_connection) -> None:
    """load_commands builds one command per program."""
    mock_connection.load_commands = AsyncMock(
        return_value={
            "applianceModel": {"options": {}},
            "options": {},
            "dictionaryId": {},
            "startProgram": {
                "PROGRAMS.WM.cotton": {
                    "parameters": {
                        "onOffStatus": {"typology": "enum", "enumValues": ["1"]}
                    }
                }
            },
        }
    )
    await device.load_commands()
    assert "startProgram" in device.commands


async def test_device_load_commands_missing_model(device, mock_connection) -> None:
    """load_commands aborts when the applianceModel is absent."""
    mock_connection.load_commands = AsyncMock(return_value={"options": {}})
    await device.load_commands()
    assert device.commands == {}


async def test_device_load_statistics(device, mock_connection) -> None:
    """load_statistics stores the payload on the device."""
    mock_connection.load_statistics = AsyncMock(return_value={"programsCounter": "12"})
    await device.load_statistics()
    assert device.statistics == {"programsCounter": "12"}


def test_device_device_info(device) -> None:
    """device_info exposes the registry payload."""
    info = device.device_info
    assert info["identifiers"] == {(DOMAIN, MAC, "WM")}
    assert info["name"] == "Lave-linge"


def test_device_parameters_property(device) -> None:
    """parameters flattens command values per command name."""
    command = MagicMock()
    command.parameters = {
        "tempSel": HonParameterRange(
            "tempSel",
            {
                "minimumValue": "0",
                "maximumValue": "6",
                "incrementValue": "1",
                "defaultValue": "4",
            },
        )
    }
    device._commands = {"startProgram": command}
    assert device.parameters == {"startProgram": {"tempSel": 4}}
