"""Tests for the root-level hOn platform setup functions."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.hon.binary_sensor import async_setup_entry as setup_binary_sensor
from custom_components.hon.button import async_setup_entry as setup_button
from custom_components.hon.climate import async_setup_entry as setup_climate
from custom_components.hon.number import async_setup_entry as setup_number
from custom_components.hon.parameter import HonParameterEnum, HonParameterRange
from custom_components.hon.select import async_setup_entry as setup_select
from custom_components.hon.sensor import async_setup_entry as setup_sensor
from custom_components.hon.switch import async_setup_entry as setup_switch
from custom_components.hon.water_heater import async_setup_entry as setup_water_heater
from tests.conftest import build_appliance


def _coordinator(device):
    """Build a coordinator mock exposing the given device."""
    coordinator = MagicMock()
    coordinator.device = device
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    return coordinator


def _entry(hass, connection):
    """Build an entry whose runtime_data is the mocked connection."""
    entry = MagicMock()
    entry.runtime_data = connection
    return entry


@pytest.fixture
def full_device(hass, mock_connection) -> tuple:
    """A mocked connection serving a single full-featured device."""
    from tests.devices.conftest import FakeDevice

    data = {
        "machMode": "1",
        "onOffStatus": "1",
        "temp": "40",
        "tempSel": "40",
        "humidity": "50",
        "humidityZ1": "50",
        "remainingTimeMM": "30",
        "delayTime": "5",
        "prCode": "5",
        "prPhase": "3",
        "prTime": "60",
        "dryLevel": "1",
        "totalWashCycle": "10",
        "totalWaterUsed": "100",
        "totalElectricityUsed": "5",
        "actualWeight": "5",
        "currentWaterUsed": "10",
        "currentElectricityUsed": "2",
        "errors": "E01",
        "spinSpeed": "800",
        "volume": "10",
        "displayedApp": "youtube",
        "currentWashCycle": "3",
        "detergentPercent": "80",
        "waterHard": "2",
        "power": "500",
        "totalWorkTime": "120",
        "preFilterStatus": "30",
        "mainFilterStatus": "40",
        "pm2p5ValueIndoor": "10",
        "pm10ValueIndoor": "20",
        "vocValueIndoor": "5",
        "coLevel": "3",
        "airQuality": "50",
        "windSpeed": "5",
        "quickModeZ1": "2",
        "remoteCtrValid": "1",
        "lockStatus": "0",
        "doorLockStatus": "0",
        "muteStatus": "1",
        "pause": "0",
        "doorStatus": "1",
        "lightStatus": "1",
        "preheatStatus": "1",
        "healthMode": "1",
        "doorStatusZ1": "1",
        "door2StatusZ1": "1",
        "statistics.programsCounter": "42",
        "tempEnv": "20",
        "tempIndoor": "22",
        "tempOutdoor": "18",
        "tempSelZ1": "20",
        "tempSelZ2": "22",
        "tempSelZ3": "24",
        "tempZ1": "19",
        "tempZ2": "21",
        "tempZ3": "23",
        "tempDhw": "55",
        "tempSelDhw": "60",
        "humidityZ2": "45",
        "humidityIndoor": "40",
        "humidityOutdoor": "60",
        "humidityEnv": "50",
        "quickModeZ2": "2",
        "intelligenceMode": "1",
        "holidayMode": "0",
        "sterilizationStatus": "1",
        "remainingVolumeHotWater": "80",
        "remainingRinseIterations": "2",
        "haier_DetergentWeight": "30",
        "haier_SoftenerWeight": "20",
        "defrostStatus": "0",
        "saltStatus": "1",
        "rinseAidStatus": "1",
        "doorStatusZ2": "1",
        "door2StatusZ2": "1",
        "heatingStatus": "1",
        "anodeMaintenanceStatus": "0",
        "tankMaintenanceStatus": "0",
        "nightWashStatus": "0",
        "steamStatus": "1",
        "energySavingStatus": "0",
        "extraDry": "0",
        "halfLoad": "0",
        "openDoor": "0",
        "ecoExpress": "1",
    }
    device = FakeDevice(data)
    device.commands = {"settings": MagicMock()}
    device.attributes["commandHistory"] = {"command": {}}
    device.settings = {
        "settings.tempLevel": HonParameterRange(
            "tempLevel",
            {
                "minimumValue": "30",
                "maximumValue": "60",
                "incrementValue": "5",
                "defaultValue": "40",
            },
        ),
        "settings.windSpeed": HonParameterEnum(
            "windSpeed", {"enumValues": ["1", "2", "5"], "defaultValue": "5"}
        ),
        "settings.binaryToggle": HonParameterEnum(
            "binaryToggle", {"enumValues": ["0", "1"], "defaultValue": "0"}
        ),
    }
    coordinator = _coordinator(device)
    mock_connection.async_get_coordinator = AsyncMock(return_value=coordinator)
    return mock_connection, coordinator, device


async def test_sensor_platform(hass, full_device) -> None:
    """The sensor platform creates entities from the device data."""
    connection, coordinator, device = full_device
    async_add_entities = MagicMock()
    await setup_sensor(hass, _entry(hass, connection), async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert entities


async def test_sensor_platform_weight_fallback(hass, mock_connection) -> None:
    """A device exposing weight (not actualWeight) still gets a weight sensor."""
    from tests.devices.conftest import FakeDevice

    device = FakeDevice({"weight": "5"})
    mock_connection.async_get_coordinator = AsyncMock(return_value=_coordinator(device))
    async_add_entities = MagicMock()
    await setup_sensor(hass, _entry(hass, mock_connection), async_add_entities)
    async_add_entities.assert_called_once()
    assert async_add_entities.call_args[0][0]


async def test_binary_sensor_platform(hass, full_device) -> None:
    """The binary sensor platform always adds an on/off sensor."""
    connection, _, _ = full_device
    async_add_entities = MagicMock()
    await setup_binary_sensor(hass, _entry(hass, connection), async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert entities
    assert any(type(e).__name__ == "HonBaseOnOff" for e in entities)


async def test_switch_platform(hass, full_device) -> None:
    """The switch platform creates an entity per present setting key."""
    connection, _, device = full_device
    device._data.update(
        {
            "silentSleepStatus": "0",
            "screenDisplayStatus": "1",
            "echoStatus": "0",
            "rapidMode": "0",
            "10degreeHeatingStatus": "0",
            "ecoMode": "0",
            "healthMode": "0",
        }
    )
    async_add_entities = MagicMock()
    await setup_switch(hass, _entry(hass, connection), async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) >= 2


async def test_switch_platform_no_settings(hass, mock_connection) -> None:
    """The switch platform adds nothing without a settings command."""
    from tests.devices.conftest import FakeDevice

    device = FakeDevice({"remoteCtrValid": "1"})
    device.commands = {}
    mock_connection.async_get_coordinator = AsyncMock(return_value=_coordinator(device))
    async_add_entities = MagicMock()
    await setup_switch(hass, _entry(hass, mock_connection), async_add_entities)
    async_add_entities.assert_called_once()
    assert async_add_entities.call_args[0][0] == []


async def test_number_platform(hass, full_device) -> None:
    """The number platform creates one entity per range setting."""
    connection, _, _ = full_device
    async_add_entities = MagicMock()
    with patch(
        "custom_components.hon.number.translation.async_get_translations",
        AsyncMock(return_value={}),
    ):
        await setup_number(hass, _entry(hass, connection), async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert entities


async def test_select_platform(hass, full_device) -> None:
    """The select platform creates one entity per enum setting."""
    connection, _, _ = full_device
    async_add_entities = MagicMock()
    with patch(
        "custom_components.hon.select.translation.async_get_translations",
        AsyncMock(return_value={}),
    ):
        await setup_select(hass, _entry(hass, connection), async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert entities


async def test_button_platform(hass, full_device) -> None:
    """The button platform adds the settings button for every device."""
    connection, _, _ = full_device
    async_add_entities = MagicMock()
    await setup_button(hass, _entry(hass, connection), async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1


async def test_button_platform_program_helper_only_ov_dw(
    hass, mock_connection, appliance
) -> None:
    """The program-details button is limited to oven/dishwasher appliances."""
    from tests.devices.conftest import FakeDevice

    appliance["applianceTypeId"] = 4  # OVEN
    device = FakeDevice({"onOffStatus": "1"})
    device.commands = {
        "startProgram": MagicMock(),
        "settings": MagicMock(),
    }
    device.settings = {}
    coordinator = _coordinator(device)
    mock_connection.appliances = [appliance]
    mock_connection.async_get_coordinator = AsyncMock(return_value=coordinator)

    async_add_entities = MagicMock()
    await setup_button(hass, _entry(hass, mock_connection), async_add_entities)
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 2  # program details + settings


async def test_climate_platform(hass, mock_connection, appliance_climate) -> None:
    """The climate platform creates an entity for AC appliances."""
    from custom_components.hon.devices.climate import HonClimateEntity
    from tests.devices.conftest import FakeDevice

    device = FakeDevice(
        {
            "tempSel": "22",
            "tempIndoor": "24",
            "windSpeed": "5",
            "onOffStatus": "1",
            "machMode": "1",
            "windDirectionHorizontal": "3",
            "windDirectionVertical": "4",
        }
    )
    device.settings = {
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
    mock_connection.appliances = [appliance_climate]
    mock_connection.async_get_coordinator = AsyncMock(return_value=_coordinator(device))
    async_add_entities = MagicMock()
    platform = MagicMock()
    with patch(
        "custom_components.hon.climate.entity_platform.async_get_current_platform",
        return_value=platform,
    ):
        await setup_climate(hass, _entry(hass, mock_connection), async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert entities
    assert isinstance(entities[0], HonClimateEntity)
    assert platform.async_register_entity_service.call_count > 0


async def test_water_heater_platform(hass, mock_connection) -> None:
    """The water heater platform creates an entity for WH appliances."""
    from custom_components.hon.devices.water_heater import HonWaterHeaterEntity
    from tests.devices.conftest import FakeDevice

    appliance = build_appliance(
        appliance_type="WH",
        appliance_type_id=10,
        model_name="ES80V-F7",
        nick_name="Chauffe-eau",
    )
    device = FakeDevice(
        {
            "temp": "40",
            "tempSel": "60",
            "onOffStatus": "1",
            "machMode": "1",
        }
    )
    device.settings = {
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
    mock_connection.appliances = [appliance]
    mock_connection.async_get_coordinator = AsyncMock(return_value=_coordinator(device))
    async_add_entities = MagicMock()
    await setup_water_heater(hass, _entry(hass, mock_connection), async_add_entities)
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert entities
    assert isinstance(entities[0], HonWaterHeaterEntity)
