"""Tests for the hOn climate entity."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.components.climate import (
    SWING_BOTH,
    SWING_HORIZONTAL,
    SWING_OFF,
    SWING_VERTICAL,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE

from custom_components.hon.const import (
    DOMAIN,
    ClimateSwingHorizontal,
    ClimateSwingVertical,
)
from custom_components.hon.devices.climate import HonClimateEntity
from custom_components.hon.parameter import HonParameterEnum, HonParameterRange
from tests.conftest import MAC, MAC2
from tests.devices.conftest import FakeDevice


def make_settings() -> dict:
    """Build the tempSel + windSpeed settings the climate init needs."""
    return {
        "tempSel": HonParameterRange(
            "tempSel",
            {
                "minimumValue": "16",
                "maximumValue": "30",
                "incrementValue": "1",
                "defaultValue": "22",
            },
        ),
        "windSpeed": HonParameterEnum(
            "windSpeed", {"enumValues": ["1", "2", "5"], "defaultValue": "5"}
        ),
    }


def make_device(data: dict | None = None) -> FakeDevice:
    """Build a climate-capable device."""
    defaults = {
        "tempSel": "22",
        "tempIndoor": "24",
        "windSpeed": "5",
        "onOffStatus": "1",
        "machMode": "1",
        "windDirectionHorizontal": "3",
        "windDirectionVertical": "4",
        "silentSleepStatus": "0",
        "echoStatus": "1",
        "screenDisplayStatus": "1",
        "rapidMode": "0",
        "muteStatus": "0",
        "humanSensingStatus": "0",
    }
    defaults.update(data or {})
    device = FakeDevice(defaults)
    device.settings = make_settings()
    return device


@pytest.fixture
def climate(hass, coordinator, appliance_climate):
    """A climate entity wired to a climate-capable device."""
    coordinator._device = make_device()
    entry = MagicMock()
    entry.runtime_data = MagicMock()
    entity = HonClimateEntity(hass, coordinator, entry, appliance_climate)
    entity.hass = hass
    return entity


def test_climate_init_attributes(climate) -> None:
    """The climate entity exposes its HA attributes."""
    assert climate.unique_id == f"{MAC}_climate"
    assert climate.name == "Climatiseur"
    assert climate.min_temp == 16
    assert climate.max_temp == 30
    assert climate.target_temperature == 22
    assert climate.current_temperature == 24.0
    assert climate.hvac_mode == HVACMode.COOL
    assert climate.target_temperature_step == 1


def test_climate_hvac_off(climate) -> None:
    """An off device reports HVACMode.OFF."""
    climate._device = make_device({"onOffStatus": "0"})
    with patch.object(climate, "async_write_ha_state", MagicMock()):
        climate._handle_coordinator_update()
    assert climate.hvac_mode == HVACMode.OFF


def test_climate_available(climate) -> None:
    """available reflects the entity availability."""
    assert climate.available is True


def test_climate_device_info(climate) -> None:
    """device_info exposes the registry payload."""
    info = climate.device_info
    assert info["identifiers"] == {(DOMAIN, MAC2, "AC")}
    assert info["name"] == "Climatiseur"


def test_climate_state_attributes(climate) -> None:
    """state_attributes include the hOn-specific modes."""
    attrs = climate.state_attributes
    assert "sleep_mode" in attrs
    assert "echo_mode" in attrs
    assert "rapid_mode" in attrs
    assert "silent_mode" in attrs
    assert "screen_display" in attrs
    assert "wind_direction_horizontal" in attrs
    assert "wind_direction_vertical" in attrs
    assert "eco_pilot_mode" in attrs


def test_climate_update_swing_mode(climate) -> None:
    """update_swing_mode maps wind directions to swing modes."""
    climate.update_swing_mode(ClimateSwingHorizontal.AUTO, ClimateSwingVertical.AUTO)
    assert climate.swing_mode == SWING_BOTH

    climate.update_swing_mode(ClimateSwingHorizontal.AUTO, "4")
    assert climate.swing_mode == SWING_HORIZONTAL

    climate.update_swing_mode("3", ClimateSwingVertical.AUTO)
    assert climate.swing_mode == SWING_VERTICAL

    climate.update_swing_mode("3", "4")
    assert climate.swing_mode == SWING_OFF


async def test_climate_set_sleep_mode(climate) -> None:
    """async_set_sleep_mode sends the matching parameter."""
    with patch.object(climate, "start_watcher", MagicMock()):
        await climate.async_set_sleep_mode(True)
    climate._device._last_command.send.assert_awaited_once()


@pytest.mark.parametrize(
    "method,kwargs,parameter",
    [
        ("async_set_sleep_mode", {"sleep_mode": True}, "silentSleepStatus"),
        ("async_set_rapid_mode", {"rapid_mode": True}, "rapidMode"),
        ("async_set_silent_mode", {"silent_mode": True}, "muteStatus"),
        ("async_set_screen_display", {"screen_display": True}, "screenDisplayStatus"),
        ("async_set_echo_mode", {"echo_mode": True}, "echoStatus"),
        (
            "async_set_wind_direction_horizontal",
            {"value": 5},
            "windDirectionHorizontal",
        ),
        ("async_set_wind_direction_vertical", {"value": 3}, "windDirectionVertical"),
        ("async_set_eco_pilot_mode", {"value": 2}, "humanSensingStatus"),
    ],
)
async def test_climate_setters(climate, method: str, kwargs, parameter: str) -> None:
    """The mode setters send a settings command."""
    with patch.object(climate, "start_watcher", MagicMock()):
        await getattr(climate, method)(**kwargs)
    climate._device._last_command.send.assert_awaited_once()


def test_climate_start_watcher(climate) -> None:
    """start_watcher schedules a state-change watcher."""
    with (
        patch("custom_components.hon.devices.climate.async_call_later") as call_later,
        patch.object(climate, "async_write_ha_state", MagicMock()),
    ):
        call_later.return_value = MagicMock()
        climate.start_watcher()
    call_later.assert_called_once()
    assert climate._watcher is not None


def test_climate_start_watcher_cancels_previous(climate) -> None:
    """start_watcher cancels any previous watcher."""
    previous = MagicMock()
    climate._watcher = previous
    with (
        patch("custom_components.hon.devices.climate.async_call_later") as call_later,
        patch.object(climate, "async_write_ha_state", MagicMock()),
    ):
        call_later.return_value = MagicMock()
        climate.start_watcher()
    previous.assert_called_once()


async def test_climate_update_after_state_change(climate) -> None:
    """The watcher callback clears the watcher."""
    climate._watcher = MagicMock()
    await climate.async_update_after_state_change()
    assert climate._watcher is None


async def test_climate_will_remove_from_hass(climate) -> None:
    """Removal cancels the watcher."""
    watcher = MagicMock()
    climate._watcher = watcher
    await climate.async_will_remove_from_hass()
    watcher.assert_called_once()
    assert climate._watcher is None


async def test_climate_set_temperature(climate) -> None:
    """async_set_temperature sends the new target."""
    with patch.object(climate, "start_watcher", MagicMock()):
        await climate.async_set_temperature(**{ATTR_TEMPERATURE: 25})
    climate._device._last_command.send.assert_awaited_once()
    assert climate.target_temperature == 25


async def test_climate_set_temperature_missing(climate) -> None:
    """Without a temperature the method is a no-op."""
    result = await climate.async_set_temperature()
    assert result is False


@pytest.mark.parametrize(
    "mode,command",
    [
        (HVACMode.OFF, "stop"),
        (HVACMode.COOL, "iot_cool"),
        (HVACMode.HEAT, "iot_heat"),
        (HVACMode.DRY, "iot_dry"),
        (HVACMode.AUTO, "iot_auto"),
        (HVACMode.FAN_ONLY, "iot_fan"),
    ],
)
async def test_climate_set_hvac_mode(climate, mode, command: str) -> None:
    """Each hvac mode maps to a stop/start command."""
    with patch.object(climate, "start_watcher", MagicMock()):
        await climate.async_set_hvac_mode(mode)
    if command == "stop":
        climate._device._last_command.send.assert_awaited_once()
    else:
        climate._device._last_command.send.assert_awaited_once()
    assert climate.hvac_mode == mode


async def test_climate_turn_off(climate) -> None:
    """async_turn_off stops the device."""
    with patch.object(climate, "start_watcher", MagicMock()):
        await climate.async_turn_off()
    climate._device._last_command.send.assert_awaited_once()
    assert climate.hvac_mode == HVACMode.OFF


async def test_climate_turn_on(climate) -> None:
    """async_turn_on starts the device."""
    with patch.object(climate, "start_watcher", MagicMock()):
        await climate.async_turn_on()
    climate._device._last_command.send.assert_awaited_once()


async def test_climate_set_fan_mode(climate) -> None:
    """async_set_fan_mode sends the wind speed mapping."""
    with patch.object(climate, "start_watcher", MagicMock()):
        await climate.async_set_fan_mode("auto")
    climate._device._last_command.send.assert_awaited_once()
    assert climate.fan_mode == "auto"


async def test_climate_set_swing_mode_both(climate) -> None:
    """SWING_BOTH sets both directions to auto."""
    with patch.object(climate, "start_watcher", MagicMock()):
        await climate.async_set_swing_mode(SWING_BOTH)
    climate._device._last_command.send.assert_awaited_once()
    assert climate.swing_mode == SWING_BOTH


async def test_climate_set_swing_mode_horizontal(climate) -> None:
    """SWING_HORIZONTAL with a vertical auto keeps horizontal auto."""
    climate._device = make_device({"windDirectionVertical": ClimateSwingVertical.AUTO})
    with patch.object(climate, "start_watcher", MagicMock()):
        await climate.async_set_swing_mode(SWING_HORIZONTAL)
    climate._device._last_command.send.assert_awaited_once()


async def test_climate_set_swing_mode_vertical(climate) -> None:
    """SWING_VERTICAL with a horizontal auto keeps vertical auto."""
    climate._device = make_device(
        {"windDirectionHorizontal": ClimateSwingHorizontal.AUTO}
    )
    with patch.object(climate, "start_watcher", MagicMock()):
        await climate.async_set_swing_mode(SWING_VERTICAL)
    climate._device._last_command.send.assert_awaited_once()


async def test_climate_set_swing_mode_off(climate) -> None:
    """Turning the swing off sets the directions to middle."""
    climate._device = make_device(
        {
            "windDirectionHorizontal": ClimateSwingHorizontal.AUTO,
            "windDirectionVertical": ClimateSwingVertical.AUTO,
        }
    )
    with patch.object(climate, "start_watcher", MagicMock()):
        await climate.async_set_swing_mode(SWING_OFF)
    climate._device._last_command.send.assert_awaited_once()
    assert climate.swing_mode == SWING_OFF


def test_climate_watcher_blocks_update(climate) -> None:
    """A running watcher suppresses coordinator updates."""
    climate._watcher = MagicMock()
    climate._handle_coordinator_update()
    assert climate._watcher is not None


def test_climate_float_temperature_step(hass, coordinator, appliance_climate) -> None:
    """A float temperature step is honoured from the setting."""
    device = make_device()
    device.settings = {
        "tempSel": HonParameterRange(
            "tempSel",
            {
                "minimumValue": "16",
                "maximumValue": "30",
                "incrementValue": "0,5",
                "defaultValue": "22",
            },
        ),
        "windSpeed": HonParameterEnum(
            "windSpeed", {"enumValues": ["1", "2", "5"], "defaultValue": "5"}
        ),
    }
    coordinator._device = device
    entry = MagicMock()
    entry.runtime_data = MagicMock()
    entity = HonClimateEntity(hass, coordinator, entry, appliance_climate)
    assert entity.target_temperature_step == 0.5


async def test_climate_set_swing_mode_horizontal_plain(climate) -> None:
    """SWING_HORIZONTAL with a non-auto vertical keeps horizontal auto."""
    with patch.object(climate, "start_watcher", MagicMock()):
        await climate.async_set_swing_mode(SWING_HORIZONTAL)
    climate._device._last_command.send.assert_awaited_once()


async def test_climate_set_swing_mode_vertical_plain(climate) -> None:
    """SWING_VERTICAL with a non-auto horizontal keeps vertical auto."""
    with patch.object(climate, "start_watcher", MagicMock()):
        await climate.async_set_swing_mode(SWING_VERTICAL)
    climate._device._last_command.send.assert_awaited_once()
