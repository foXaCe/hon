"""Tests for the hOn water heater entity."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.const import STATE_OFF

from custom_components.hon.const import DOMAIN
from custom_components.hon.devices.water_heater import HonWaterHeaterEntity
from custom_components.hon.parameter import HonParameterRange
from tests.conftest import MAC
from tests.devices.conftest import FakeDevice


def make_settings() -> dict:
    """Build the tempSel setting the water heater init reads."""
    return {
        "tempSel": HonParameterRange(
            "tempSel",
            {
                "minimumValue": "30",
                "maximumValue": "85",
                "incrementValue": "1",
                "defaultValue": "60",
            },
        )
    }


def make_device(data: dict | None = None) -> FakeDevice:
    """Build a water-heater-capable device."""
    defaults = {
        "temp": "40",
        "tempSel": "60",
        "onOffStatus": "1",
        "machMode": "1",
    }
    defaults.update(data or {})
    device = FakeDevice(defaults)
    device.settings = make_settings()
    return device


@pytest.fixture
def water_heater(hass, coordinator, appliance):
    """A water heater entity for a WH appliance."""
    coordinator._device = make_device()
    entry = MagicMock()
    entry.runtime_data = MagicMock()
    entity = HonWaterHeaterEntity(hass, coordinator, entry, appliance)
    entity.hass = hass
    return entity


def test_water_heater_init(water_heater) -> None:
    """The water heater exposes its attributes."""
    assert water_heater.unique_id == f"{MAC}_water_heater"
    assert water_heater.min_temp == 30
    assert water_heater.max_temp == 85
    assert water_heater.current_temperature == 40.0
    assert water_heater.target_temperature == 60.0
    assert water_heater.current_operation == "Eco"


def test_water_heater_off(water_heater) -> None:
    """An off device reports STATE_OFF as operation."""
    water_heater._device = make_device({"onOffStatus": "0"})
    water_heater._update_from_device(write=False)
    assert water_heater.current_operation == STATE_OFF


def test_water_heater_operation_list(water_heater) -> None:
    """operation_list contains off plus the hOn modes."""
    assert water_heater.operation_list == [STATE_OFF, "Eco", "Max", "BPS"]


def test_water_heater_device_info(water_heater, appliance) -> None:
    """device_info exposes the registry payload."""
    info = water_heater.device_info
    assert info["identifiers"] == {(DOMAIN, water_heater._mac, "WM")}


def test_water_heater_name(water_heater, appliance) -> None:
    """name falls back to the nick name."""
    assert water_heater.name == "Lave-linge"


async def test_water_heater_set_temperature(water_heater) -> None:
    """async_set_temperature sends the new target."""
    with (
        patch.object(water_heater, "start_watcher", MagicMock()),
        patch.object(water_heater, "async_write_ha_state", MagicMock()),
    ):
        await water_heater.async_set_temperature(temperature=65)
    water_heater._device._last_command.send.assert_awaited_once()
    assert water_heater.target_temperature == 65


async def test_water_heater_set_temperature_missing(water_heater) -> None:
    """Without a temperature the method is a no-op."""
    await water_heater.async_set_temperature()
    assert water_heater.target_temperature == 60


async def test_water_heater_set_operation_mode_off(water_heater) -> None:
    """Turning the operation off stops the device."""
    with (
        patch.object(water_heater, "start_watcher", MagicMock()),
        patch.object(water_heater, "async_write_ha_state", MagicMock()),
    ):
        await water_heater.async_set_operation_mode(STATE_OFF)
    water_heater._device._last_command.send.assert_awaited_once()
    assert water_heater.current_operation == STATE_OFF


async def test_water_heater_set_operation_mode_live(water_heater) -> None:
    """A live mode change keeps the current temperature."""
    with (
        patch.object(water_heater, "start_watcher", MagicMock()),
        patch.object(water_heater, "async_write_ha_state", MagicMock()),
    ):
        await water_heater.async_set_operation_mode("Max")
    water_heater._device._last_command.send.assert_awaited_once()
    assert water_heater.current_operation == "Max"


async def test_water_heater_set_operation_mode_powered_off(water_heater) -> None:
    """Starting a mode while off restarts with the matching program."""
    water_heater._device = make_device({"onOffStatus": "0"})
    with (
        patch.object(water_heater, "start_watcher", MagicMock()),
        patch.object(water_heater, "async_write_ha_state", MagicMock()),
    ):
        await water_heater.async_set_operation_mode("BPS")
    water_heater._device._last_command.send.assert_awaited_once()
    assert water_heater.current_operation == "BPS"


async def test_water_heater_turn_on(water_heater) -> None:
    """async_turn_on starts the current mode's program."""
    with (
        patch.object(water_heater, "start_watcher", MagicMock()),
        patch.object(water_heater, "async_write_ha_state", MagicMock()),
    ):
        await water_heater.async_turn_on()
    water_heater._device._last_command.send.assert_awaited_once()


async def test_water_heater_turn_off(water_heater) -> None:
    """async_turn_off stops the device."""
    with (
        patch.object(water_heater, "start_watcher", MagicMock()),
        patch.object(water_heater, "async_write_ha_state", MagicMock()),
    ):
        await water_heater.async_turn_off()
    water_heater._device._last_command.send.assert_awaited_once()
    assert water_heater.current_operation == STATE_OFF


def test_water_heater_watcher(water_heater) -> None:
    """start_watcher tracks a time interval and is cleared on callback."""
    with patch(
        "custom_components.hon.devices.water_heater.async_track_time_interval"
    ) as track:
        track.return_value = MagicMock()
        water_heater.start_watcher()
    track.assert_called_once()
    assert water_heater._watcher is not None


def test_water_heater_watcher_cleared(water_heater) -> None:
    """The watcher callback clears the watcher and requests a refresh."""
    watcher = MagicMock()
    water_heater._watcher = watcher
    water_heater._coordinator.async_request_refresh = AsyncMock()
    water_heater._watcher = watcher

    import asyncio

    async def run():
        await water_heater._clear_watcher()
        watcher.assert_called_once()
        assert water_heater._watcher is None
        water_heater._coordinator.async_request_refresh.assert_awaited_once()

    asyncio.run(run())


async def test_water_heater_handle_coordinator_update(water_heater) -> None:
    """The coordinator update refreshes the device values."""
    with patch.object(water_heater, "async_write_ha_state", MagicMock()):
        water_heater._handle_coordinator_update()
    assert water_heater.current_temperature == 40.0


async def test_water_heater_handle_coordinator_update_watcher(water_heater) -> None:
    """A running watcher suppresses coordinator updates."""
    water_heater._watcher = MagicMock()
    water_heater._handle_coordinator_update()
    assert water_heater._watcher is not None


async def test_water_heater_will_remove_from_hass(water_heater) -> None:
    """Removal cancels the watcher."""
    watcher = MagicMock()
    water_heater._watcher = watcher
    await water_heater.async_will_remove_from_hass()
    watcher.assert_called_once()
    assert water_heater._watcher is None


def test_water_heater_watcher_cancels_previous(water_heater) -> None:
    """start_watcher cancels any previous watcher."""
    previous = MagicMock()
    water_heater._watcher = previous
    with patch(
        "custom_components.hon.devices.water_heater.async_track_time_interval"
    ) as track:
        track.return_value = MagicMock()
        water_heater.start_watcher()
    previous.assert_called_once()


async def test_water_heater_handle_coordinator_update_data_false(
    water_heater,
) -> None:
    """A False coordinator data blocks the device refresh."""
    water_heater._coordinator.data = False
    with patch.object(water_heater, "_update_from_device", MagicMock()) as update:
        water_heater._handle_coordinator_update()
    update.assert_not_called()
