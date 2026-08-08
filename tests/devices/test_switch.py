"""Tests for the hOn switch entity classes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hon.devices.switch import (
    HonSwitchEntity,
    HonSwitchEntityDescription,
)
from custom_components.hon.parameter import HonParameter, HonParameterRange
from tests.conftest import MAC


def make_description(
    key: str = "muteStatus", **overrides
) -> HonSwitchEntityDescription:
    """Build a switch entity description."""
    kwargs = {
        "key": key,
        "name": "Silent Mode",
        "icon": "mdi:volume-off",
        "translation_key": "silent_mode",
    }
    kwargs.update(overrides)
    return HonSwitchEntityDescription(**kwargs)


@pytest.fixture
def switch(coordinator, appliance, make_device) -> HonSwitchEntity:
    """A switch entity bound to a fake device."""
    coordinator._device = make_device({"muteStatus": "1", "remoteCtrValid": "1"})
    return HonSwitchEntity(None, coordinator, None, appliance, make_description())


async def test_switch_unique_id_and_name(switch) -> None:
    """The switch derives its unique id and name from the description."""
    assert switch.unique_id == f"{MAC}_mute_status"
    assert switch.name == "Silent Mode"


def test_switch_is_on(coordinator, appliance, make_device) -> None:
    """is_on reflects the device value."""
    coordinator._device = make_device({"muteStatus": "1"})
    entity = HonSwitchEntity(None, coordinator, None, appliance, make_description())
    assert entity.is_on is True

    coordinator._device = make_device({"muteStatus": "0"})
    entity = HonSwitchEntity(None, coordinator, None, appliance, make_description())
    assert entity.is_on is False


def test_switch_is_on_inverted(coordinator, appliance, make_device) -> None:
    """An inverted switch reports the inverse state."""
    coordinator._device = make_device({"echoStatus": "0"})
    entity = HonSwitchEntity(
        None,
        coordinator,
        None,
        appliance,
        make_description(key="echoStatus", name="Echo", translation_key="echo_status"),
        invert=True,
    )
    assert entity.is_on is True


def test_switch_available(coordinator, appliance, make_device) -> None:
    """available is True when the device is reachable and the key exists."""
    coordinator._device = make_device({"muteStatus": "1", "remoteCtrValid": "1"})
    entity = HonSwitchEntity(None, coordinator, None, appliance, make_description())
    assert entity.available is True


def test_switch_available_missing_key(coordinator, appliance, make_device) -> None:
    """available is False when the underlying key is absent."""
    coordinator._device = make_device({"remoteCtrValid": "1"})
    entity = HonSwitchEntity(None, coordinator, None, appliance, make_description())
    assert entity.available is False


def test_switch_available_no_remote_control(
    coordinator, appliance, make_device
) -> None:
    """available is False when remote control is disabled."""
    coordinator._device = make_device({"muteStatus": "1", "remoteCtrValid": "0"})
    entity = HonSwitchEntity(None, coordinator, None, appliance, make_description())
    assert entity.available is False


def test_switch_available_disconnected(coordinator, appliance, make_device) -> None:
    """available is False when the device reports DISCONNECTED."""
    coordinator._device = make_device({"muteStatus": "1", "remoteCtrValid": "1"})
    coordinator._device.attributes = {"lastConnEvent": {"category": "DISCONNECTED"}}
    entity = HonSwitchEntity(None, coordinator, None, appliance, make_description())
    assert entity.available is False


async def test_switch_turn_on(switch, coordinator, appliance) -> None:
    """async_turn_on sends the on value through the coordinator."""
    coordinator._device.set = MagicMock()
    coordinator.async_set_updated_data = MagicMock()
    with patch.object(switch, "async_write_ha_state", MagicMock()):
        await switch.async_turn_on()
    coordinator._hon.async_set.assert_awaited_once_with(MAC, "WM", {"muteStatus": "1"})
    coordinator._device.set.assert_called_once_with("muteStatus", "1")
    coordinator.async_set_updated_data.assert_called_once_with({})


async def test_switch_turn_off(switch, coordinator, appliance) -> None:
    """async_turn_off sends the off value through the coordinator."""
    coordinator._device.set = MagicMock()
    coordinator.async_set_updated_data = MagicMock()
    with patch.object(switch, "async_write_ha_state", MagicMock()):
        await switch.async_turn_off()
    coordinator._hon.async_set.assert_awaited_once_with(MAC, "WM", {"muteStatus": "0"})
    coordinator._device.set.assert_called_once_with("muteStatus", "0")


async def test_switch_turn_on_inverted(coordinator, appliance, make_device) -> None:
    """An inverted switch sends the inverse value when turned on."""
    coordinator._device = make_device({"echoStatus": "0", "remoteCtrValid": "1"})
    coordinator._device.set = MagicMock()
    coordinator.async_set_updated_data = MagicMock()
    entity = HonSwitchEntity(
        None,
        coordinator,
        None,
        appliance,
        make_description(key="echoStatus", name="Echo", translation_key="echo_status"),
        invert=True,
    )
    with patch.object(entity, "async_write_ha_state", MagicMock()):
        await entity.async_turn_on()
    coordinator._hon.async_set.assert_awaited_once_with(MAC, "WM", {"echoStatus": "0"})


def test_switch_available_coordinator_unavailable(
    coordinator, appliance, make_device
) -> None:
    """available is False when the coordinator reports an update failure."""
    coordinator._device = make_device({"muteStatus": "1", "remoteCtrValid": "1"})
    coordinator.last_update_success = False
    entity = HonSwitchEntity(None, coordinator, None, appliance, make_description())
    assert entity.available is False


async def test_switch_turn_on_inverted_range(
    coordinator, appliance, make_device
) -> None:
    """An inverted switch moves a range setting to its minimum."""
    setting = HonParameterRange(
        "echoStatus",
        {
            "minimumValue": "0",
            "maximumValue": "5",
            "incrementValue": "1",
            "defaultValue": "3",
        },
    )
    coordinator._device = make_device({"echoStatus": "3", "remoteCtrValid": "1"})
    coordinator._device.settings = {"settings.echoStatus": setting}
    command = MagicMock()
    command.send = AsyncMock(return_value=True)
    coordinator._device.commands = {"settings": command}
    coordinator._device.set = MagicMock()
    coordinator.async_set_updated_data = MagicMock()
    entity = HonSwitchEntity(
        None,
        coordinator,
        None,
        appliance,
        make_description(key="echoStatus", name="Echo", translation_key="echo_status"),
        invert=True,
    )
    with patch.object(entity, "async_write_ha_state", MagicMock()):
        await entity.async_turn_on()
    assert setting.value == 0
    coordinator._device.set.assert_called_once_with("echoStatus", "0")


def test_switch_handle_coordinator_update(switch) -> None:
    """The coordinator update writes the is_on state."""
    with patch.object(switch, "async_write_ha_state", MagicMock()):
        switch._handle_coordinator_update()
    assert switch.is_on is True


def test_switch_handle_coordinator_update_no_write(switch) -> None:
    """The coordinator update can skip the state write."""
    with patch.object(switch, "async_write_ha_state", MagicMock()) as write:
        switch._handle_coordinator_update(update=False)
    write.assert_not_called()


async def test_switch_turn_on_range_setting(
    coordinator, appliance, make_device
) -> None:
    """With a range setting the switch uses its min/max bounds."""
    setting = HonParameterRange(
        "muteStatus",
        {
            "minimumValue": "0",
            "maximumValue": "5",
            "incrementValue": "1",
            "defaultValue": "0",
        },
    )
    coordinator._device = make_device({"muteStatus": "0", "remoteCtrValid": "1"})
    coordinator._device.settings = {"settings.muteStatus": setting}
    command = MagicMock()
    command.send = AsyncMock(return_value=True)
    coordinator._device.commands = {"settings": command}
    coordinator._device.set = MagicMock()
    coordinator.async_set_updated_data = MagicMock()

    entity = HonSwitchEntity(None, coordinator, None, appliance, make_description())
    with patch.object(entity, "async_write_ha_state", MagicMock()):
        await entity.async_turn_on()

    assert setting.value == 5
    command.send.assert_awaited_once()
    coordinator._device.set.assert_called_once_with("muteStatus", "5")


async def test_switch_turn_off_range_setting(
    coordinator, appliance, make_device
) -> None:
    """Turning off a range setting moves it to its minimum."""
    setting = HonParameterRange(
        "muteStatus",
        {
            "minimumValue": "0",
            "maximumValue": "5",
            "incrementValue": "1",
            "defaultValue": "3",
        },
    )
    coordinator._device = make_device({"muteStatus": "3", "remoteCtrValid": "1"})
    coordinator._device.settings = {"settings.muteStatus": setting}
    command = MagicMock()
    command.send = AsyncMock(return_value=True)
    coordinator._device.commands = {"settings": command}
    coordinator._device.set = MagicMock()
    coordinator.async_set_updated_data = MagicMock()

    entity = HonSwitchEntity(None, coordinator, None, appliance, make_description())
    with patch.object(entity, "async_write_ha_state", MagicMock()):
        await entity.async_turn_off()

    assert setting.value == 0
    coordinator._device.set.assert_called_once_with("muteStatus", "0")


async def test_switch_turn_on_plain_parameter_returns(
    coordinator, appliance, make_device
) -> None:
    """A bare HonParameter setting is not controllable and returns early."""
    setting = HonParameter("muteStatus", {})
    coordinator._device = make_device({"muteStatus": "", "remoteCtrValid": "1"})
    coordinator._device.settings = {"settings.muteStatus": setting}
    coordinator._device.commands = {}
    entity = HonSwitchEntity(None, coordinator, None, appliance, make_description())
    with patch.object(entity, "async_write_ha_state", MagicMock()):
        await entity.async_turn_on()
    coordinator._hon.async_set.assert_not_awaited()


async def test_switch_turn_off_plain_parameter_returns(
    coordinator, appliance, make_device
) -> None:
    """A bare HonParameter setting cannot be turned off."""
    setting = HonParameter("muteStatus", {})
    coordinator._device = make_device({"muteStatus": "", "remoteCtrValid": "1"})
    coordinator._device.settings = {"settings.muteStatus": setting}
    coordinator._device.commands = {}
    entity = HonSwitchEntity(None, coordinator, None, appliance, make_description())
    with patch.object(entity, "async_write_ha_state", MagicMock()):
        await entity.async_turn_off()
    coordinator._hon.async_set.assert_not_awaited()


async def test_switch_turn_off_inverted_range(
    coordinator, appliance, make_device
) -> None:
    """Turning off an inverted switch moves a range to its maximum."""
    setting = HonParameterRange(
        "echoStatus",
        {
            "minimumValue": "0",
            "maximumValue": "5",
            "incrementValue": "1",
            "defaultValue": "3",
        },
    )
    coordinator._device = make_device({"echoStatus": "3", "remoteCtrValid": "1"})
    coordinator._device.settings = {"settings.echoStatus": setting}
    command = MagicMock()
    command.send = AsyncMock(return_value=True)
    coordinator._device.commands = {"settings": command}
    coordinator._device.set = MagicMock()
    coordinator.async_set_updated_data = MagicMock()
    entity = HonSwitchEntity(
        None,
        coordinator,
        None,
        appliance,
        make_description(key="echoStatus", name="Echo", translation_key="echo_status"),
        invert=True,
    )
    with patch.object(entity, "async_write_ha_state", MagicMock()):
        await entity.async_turn_off()
    assert setting.value == 5
    coordinator._device.set.assert_called_once_with("echoStatus", "5")


def test_switch_available_with_setting(coordinator, appliance, make_device) -> None:
    """available is True when a live setting backs the switch."""
    from custom_components.hon.parameter import HonParameterRange

    setting = HonParameterRange(
        "muteStatus",
        {
            "minimumValue": "0",
            "maximumValue": "1",
            "incrementValue": "1",
            "defaultValue": "0",
        },
    )
    coordinator._device = make_device({"muteStatus": "0", "remoteCtrValid": "1"})
    coordinator._device.settings = {"settings.muteStatus": setting}
    coordinator.last_update_success = True
    entity = HonSwitchEntity(None, coordinator, None, appliance, make_description())
    assert entity.available is True
