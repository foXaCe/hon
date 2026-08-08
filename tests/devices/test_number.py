"""Tests for the hOn number entity classes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from homeassistant.components.number import NumberEntityDescription

from custom_components.hon.devices.number import HonBaseNumberEntity, HonNumber
from custom_components.hon.parameter import HonParameterRange
from tests.conftest import MAC


def make_description(
    key: str = "settings.tempLevel", **overrides
) -> NumberEntityDescription:
    """Build a number entity description."""
    kwargs = {"key": key, "name": "Temp level"}
    kwargs.update(overrides)
    return NumberEntityDescription(**kwargs)


def make_setting() -> HonParameterRange:
    """Build a tempSel-style range setting."""
    return HonParameterRange(
        "tempLevel",
        {
            "minimumValue": "30",
            "maximumValue": "60",
            "incrementValue": "5",
            "defaultValue": "40",
        },
    )


def test_hon_base_number_entity(coordinator, appliance, make_device) -> None:
    """The base number entity reads its key and derives the unique id."""
    coordinator._device = make_device({"tempLevel": "40"})
    entity = HonBaseNumberEntity(coordinator, appliance, "tempLevel", "Temp level")

    assert entity.unique_id == f"{MAC}_temp_level"
    assert entity.translation_key == "temp_level"
    assert entity.native_value == "40"


def test_hon_number_bounds(coordinator, appliance, make_device) -> None:
    """HonNumber reads min/max/step from the range setting."""
    coordinator._device = make_device({"tempLevel": "40"})
    coordinator._device.settings = {"settings.tempLevel": make_setting()}
    coordinator.last_update_success = True
    entity = HonNumber(None, coordinator, appliance, make_description())

    entity._refresh_bounds()
    assert entity.native_value == 40
    assert entity.native_min_value == 30
    assert entity.native_max_value == 60
    assert entity.native_step == 5


def test_hon_number_coordinator_update(coordinator, appliance, make_device) -> None:
    """The coordinator update refreshes the bounds and the value."""
    coordinator._device = make_device({})
    coordinator._device.settings = {"settings.tempLevel": make_setting()}
    coordinator.last_update_success = True
    entity = HonNumber(None, coordinator, appliance, make_description())

    with patch.object(entity, "async_write_ha_state", MagicMock()):
        entity._handle_coordinator_update()
    assert entity.native_value == 40
    assert entity.native_min_value == 30


def test_hon_number_no_setting(coordinator, appliance, make_device) -> None:
    """Without a matching setting the number reports None."""
    coordinator._device = make_device({})
    entity = HonNumber(None, coordinator, appliance, make_description())
    assert entity.native_value is None


async def test_hon_number_set_native_value(coordinator, appliance, make_device) -> None:
    """async_set_native_value sends the new value through start_command."""
    device = make_device({})
    device.settings = {"settings.tempLevel": make_setting()}
    coordinator._device = device
    coordinator.async_set_updated_data = MagicMock()
    entity = HonNumber(None, coordinator, appliance, make_description())

    await entity.async_set_native_value(45)
    coordinator.async_set_updated_data.assert_called_once_with({})


def test_hon_number_available(coordinator, appliance, make_device) -> None:
    """available requires a current setting."""
    coordinator._device = make_device({})
    coordinator.last_update_success = True
    entity = HonNumber(None, coordinator, appliance, make_description())
    assert entity.available is False

    coordinator._device.settings = {"settings.tempLevel": make_setting()}
    entity = HonNumber(None, coordinator, appliance, make_description())
    assert entity.available is True


def test_hon_base_number_entity_coordinator_update(
    coordinator, appliance, make_device
) -> None:
    """The base number entity refreshes its value on coordinator updates."""
    coordinator._device = make_device({"tempLevel": "40"})
    entity = HonBaseNumberEntity(coordinator, appliance, "tempLevel", "Temp level")
    with patch.object(entity, "async_write_ha_state", MagicMock()):
        entity._handle_coordinator_update()
    assert entity.native_value == "40"


def test_hon_base_number_entity_coordinator_update_unavailable(
    coordinator, appliance, make_device
) -> None:
    """The base number entity skips updates while unavailable."""
    coordinator._device = make_device({"tempLevel": "40"})
    coordinator.last_update_success = False
    entity = HonBaseNumberEntity(coordinator, appliance, "tempLevel", "Temp level")
    with (
        patch.object(entity, "coordinator_update", MagicMock()) as update,
        patch.object(entity, "async_write_ha_state", MagicMock()),
    ):
        entity._handle_coordinator_update()
    update.assert_not_called()
