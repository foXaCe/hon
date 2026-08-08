"""Tests for the hOn select entity classes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from homeassistant.components.select import SelectEntityDescription

from custom_components.hon.devices.select import HonSelect
from custom_components.hon.parameter import HonParameterEnum, HonParameterFixed
from tests.conftest import MAC


def make_description(
    key: str = "settings.windSpeed", **overrides
) -> SelectEntityDescription:
    """Build a select entity description."""
    kwargs = {"key": key, "name": "Wind speed"}
    kwargs.update(overrides)
    return SelectEntityDescription(**kwargs)


def make_enum() -> HonParameterEnum:
    """Build an enum setting."""
    return HonParameterEnum(
        "windSpeed", {"enumValues": ["1", "2", "5"], "defaultValue": "5"}
    )


def test_hon_select_options(coordinator, appliance, make_device) -> None:
    """HonSelect exposes the enum values as options."""
    coordinator._device = make_device({})
    coordinator._device.settings = {"settings.windSpeed": make_enum()}
    coordinator.last_update_success = True
    entity = HonSelect(None, coordinator, appliance, make_description())

    assert entity.unique_id == f"{MAC}-select-settings.windSpeed"
    assert entity.options == ["1", "2", "5"]
    assert entity.current_option == "5"


def test_hon_select_no_setting(coordinator, appliance, make_device) -> None:
    """Without a matching setting the select has no options."""
    coordinator._device = make_device({})
    coordinator.last_update_success = True
    entity = HonSelect(None, coordinator, appliance, make_description())

    assert entity.options == []
    assert entity.current_option is None


def test_hon_select_fixed_setting(coordinator, appliance, make_device) -> None:
    """A fixed setting yields a single option."""
    coordinator._device = make_device({})
    coordinator._device.settings = {
        "settings.windSpeed": HonParameterFixed("windSpeed", {"fixedValue": "2"})
    }
    coordinator.last_update_success = True
    entity = HonSelect(None, coordinator, appliance, make_description())

    assert entity.options == ["2"]
    assert entity.current_option == "2"


async def test_hon_select_select_option_settings(
    coordinator, appliance, make_device
) -> None:
    """Selecting a settings option sends the settings command."""
    device = make_device({})
    device.settings = {"settings.windSpeed": make_enum()}
    coordinator._device = device
    coordinator.last_update_success = True
    coordinator.async_request_refresh = AsyncMock()
    entity = HonSelect(None, coordinator, appliance, make_description())

    await entity.async_select_option("2")
    coordinator.async_request_refresh.assert_awaited_once()


async def test_hon_select_select_option_start_program(
    coordinator, appliance, make_device
) -> None:
    """Selecting a program option uses start_command."""
    coordinator._device = make_device({})
    coordinator.async_set_updated_data = MagicMock()
    entity = HonSelect(
        None, coordinator, appliance, make_description(key="startProgram.program")
    )

    await entity.async_select_option("cotton")
    coordinator.async_set_updated_data.assert_called_once_with({})


async def test_hon_select_select_option_start_parameter(
    coordinator, appliance, make_device
) -> None:
    """Selecting a non-program parameter uses start_command too."""
    coordinator._device = make_device({})
    coordinator.async_set_updated_data = MagicMock()
    entity = HonSelect(
        None, coordinator, appliance, make_description(key="startProgram.machMode")
    )

    await entity.async_select_option("1")
    coordinator.async_set_updated_data.assert_called_once_with({})


def test_hon_select_coordinator_update(coordinator, appliance, make_device) -> None:
    """The coordinator update refreshes options and the current option."""
    coordinator._device = make_device({})
    coordinator._device.settings = {"settings.windSpeed": make_enum()}
    coordinator.last_update_success = True
    entity = HonSelect(None, coordinator, appliance, make_description())

    with patch.object(entity, "async_write_ha_state", MagicMock()):
        entity._handle_coordinator_update()
    assert entity.options == ["1", "2", "5"]
    assert entity.current_option == "5"


def test_hon_select_available(coordinator, appliance, make_device) -> None:
    """available requires a current setting."""
    coordinator._device = make_device({})
    coordinator.last_update_success = True
    entity = HonSelect(None, coordinator, appliance, make_description())
    assert entity.available is False

    coordinator._device.settings = {"settings.windSpeed": make_enum()}
    entity = HonSelect(None, coordinator, appliance, make_description())
    assert entity.available is True


def test_hon_select_current_option_not_in_options(
    coordinator, appliance, make_device
) -> None:
    """current_option is None when the value is not among the options."""
    coordinator._device = make_device({})
    coordinator._device.settings = {
        "settings.windSpeed": HonParameterEnum(
            "windSpeed", {"enumValues": ["1", "2"], "defaultValue": "9"}
        )
    }
    coordinator.last_update_success = True
    entity = HonSelect(None, coordinator, appliance, make_description())
    assert entity.current_option is None


def test_hon_select_coordinator_update_unavailable(
    coordinator, appliance, make_device
) -> None:
    """The coordinator update skips when the entity is unavailable."""
    coordinator._device = make_device({})
    coordinator._device.settings = {"settings.windSpeed": make_enum()}
    coordinator.last_update_success = False
    entity = HonSelect(None, coordinator, appliance, make_description())
    with (
        patch.object(entity, "_refresh_options", MagicMock()) as refresh,
        patch.object(entity, "async_write_ha_state", MagicMock()),
    ):
        entity._handle_coordinator_update()
    refresh.assert_not_called()
