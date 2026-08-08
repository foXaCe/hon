"""Tests for the hOn sensor entity classes."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature

if TYPE_CHECKING:
    from collections.abc import Callable


from custom_components.hon.devices.sensor import (
    HonBaseAIRquality,
    HonBaseCOlevel,
    HonBaseCurrentElectricityUsed,
    HonBaseCurrentWashCycle,
    HonBaseCurrentWaterUsed,
    HonBaseDelayTime,
    HonBaseDetergentPercent,
    HonBaseDetergentWeight,
    HonBaseDisplayedApp,
    HonBaseDryLevel,
    HonBaseEnd,
    HonBaseError,
    HonBaseHumidity,
    HonBaseIndoorPM2p5,
    HonBaseIndoorPM10,
    HonBaseIndoorVOC,
    HonBaseInt,
    HonBaseMainFilter,
    HonBaseMeanWaterConsumption,
    HonBaseMode,
    HonBasePower,
    HonBasePreFilter,
    HonBaseProgram,
    HonBaseProgramDuration,
    HonBaseProgramName,
    HonBaseProgramPhase,
    HonBaseProgramsCounter,
    HonBaseRemainingTime,
    HonBaseSensorEntity,
    HonBaseSpinSpeed,
    HonBaseStart,
    HonBaseTemperature,
    HonBaseTotalElectricityUsed,
    HonBaseTotalWashCycle,
    HonBaseTotalWaterUsed,
    HonBaseVolume,
    HonBaseWaterHardness,
    HonBaseWeight,
    HonBaseWorkTime,
)
from tests.conftest import MAC


def test_hon_base_sensor_entity(coordinator, appliance, make_device) -> None:
    """The base sensor derives its unique id and reads the device value."""
    coordinator._device = make_device({"tempSel": "40"})
    entity = HonBaseSensorEntity(coordinator, appliance, "tempSel", "Temperature")

    assert entity.unique_id == f"{MAC}_temp_sel"
    assert entity.translation_key == "temp_sel"
    assert entity.native_value == "40"


def test_hon_base_sensor_empty_key_fallback(
    coordinator, appliance, make_device
) -> None:
    """An empty key falls back to the sensor name for the unique id."""
    coordinator._device = make_device({"onOffStatus": "1"})
    entity = HonBaseSensorEntity(coordinator, appliance, "", "Start time")
    assert entity.unique_id == f"{MAC}_start time"


def test_hon_base_mode_washing_machine(coordinator, appliance, make_device) -> None:
    """HonBaseMode maps a WM appliance to the wash translation key."""
    coordinator._device = make_device({"machMode": "1"})
    entity = HonBaseMode(None, coordinator, None, appliance)

    assert entity.translation_key == "wash_mode"
    assert entity.icon == "mdi:washing-machine"
    assert entity.native_value == "1"


def test_hon_base_mode_climate(coordinator, appliance_climate, make_device) -> None:
    """HonBaseMode maps a climate appliance to its translation key."""
    coordinator._device = make_device({"machMode": "4"})
    entity = HonBaseMode(None, coordinator, None, appliance_climate)

    assert entity.translation_key == "climate_mode"
    assert entity.native_value == "4"


def test_hon_base_program_name(coordinator, appliance, make_device) -> None:
    """HonBaseProgramName surfaces the resolved program name."""
    coordinator._device = make_device({}, program_name="cotton")
    entity = HonBaseProgramName(None, coordinator, None, appliance)
    assert entity.native_value == "cotton"


def test_hon_base_program_name_no_program(coordinator, appliance, make_device) -> None:
    """HonBaseProgramName falls back to 'No program'."""
    coordinator._device = make_device({}, program_name=None)
    entity = HonBaseProgramName(None, coordinator, None, appliance)
    assert entity.native_value == "No program"


def test_hon_base_temperature(coordinator, appliance, make_device) -> None:
    """HonBaseTemperature is a Celsius measurement sensor."""
    coordinator._device = make_device({"tempSel": "40"})
    entity = HonBaseTemperature(None, coordinator, None, appliance, "tempSel", "Sel")

    assert entity.device_class is SensorDeviceClass.TEMPERATURE
    assert entity.state_class is SensorStateClass.MEASUREMENT
    assert entity.native_unit_of_measurement == UnitOfTemperature.CELSIUS
    assert entity.native_value == "40"


def test_hon_base_humidity(coordinator, appliance, make_device) -> None:
    """HonBaseHumidity is a percentage humidity sensor."""
    coordinator._device = make_device({"humidityZ1": "50"})
    entity = HonBaseHumidity(None, coordinator, None, appliance, "Z1", "zone 1")

    assert entity.device_class is SensorDeviceClass.HUMIDITY
    assert entity.native_unit_of_measurement == PERCENTAGE
    assert entity.unique_id == f"{MAC}_humidity_z1"


def test_hon_base_remaining_time_washing_idle(
    coordinator, appliance, make_device
) -> None:
    """A WM in an idle mode reports zero remaining time."""
    coordinator._device = make_device({"remainingTimeMM": "30", "machMode": "1"})
    entity = HonBaseRemainingTime(None, coordinator, None, appliance)
    assert entity.native_value == 0


def test_hon_base_remaining_time_washing_active(
    coordinator, appliance, make_device
) -> None:
    """A WM in a running mode reports the remaining minutes."""
    coordinator._device = make_device({"remainingTimeMM": "30", "machMode": "4"})
    entity = HonBaseRemainingTime(None, coordinator, None, appliance)
    assert entity.native_value == 30


def test_hon_base_remaining_time_with_delay(
    coordinator, appliance_climate, make_device
) -> None:
    """Other appliances add the delay to the remaining time."""
    coordinator._device = make_device(
        {"remainingTimeMM": "30", "delayTime": "5", "machMode": "1"}
    )
    entity = HonBaseRemainingTime(None, coordinator, None, appliance_climate)
    assert entity.native_value == 35


def test_hon_base_start_on(coordinator, appliance, make_device) -> None:
    """HonBaseStart stamps the start time when the device turns on."""
    coordinator._device = make_device({"onOffStatus": "1", "delayTime": "0"})
    entity = HonBaseStart(None, coordinator, None, appliance)

    value = entity.native_value
    assert isinstance(value, datetime)
    now = datetime.now(UTC).replace(second=0)
    assert abs((value - now).total_seconds()) <= 1


def test_hon_base_start_off(coordinator, appliance, make_device) -> None:
    """HonBaseStart reports None while the device is off."""
    coordinator._device = make_device({"onOffStatus": "0"})
    entity = HonBaseStart(None, coordinator, None, appliance)
    assert entity.native_value is None


def test_hon_base_end_off(coordinator, appliance, make_device) -> None:
    """HonBaseEnd reports None while the device is off."""
    coordinator._device = make_device({"onOffStatus": "0", "remainingTimeMM": "30"})
    entity = HonBaseEnd(None, coordinator, None, appliance)
    assert entity.native_value is None


def test_hon_base_int(coordinator, appliance, make_device) -> None:
    """HonBaseInt exposes the raw device value."""
    coordinator._device = make_device({"quickModeZ1": "2"})
    entity = HonBaseInt(None, coordinator, None, appliance, "quickModeZ1", "Quick")
    assert entity.native_value == "2"


def test_hon_base_prefilter(coordinator, appliance, make_device) -> None:
    """HonBasePreFilter reports the remaining filter lifetime."""
    coordinator._device = make_device({"preFilterStatus": "30"})
    entity = HonBasePreFilter(None, coordinator, None, appliance)
    assert entity.native_value == 70.0


def test_hon_base_spin_speed_idle(coordinator, appliance, make_device) -> None:
    """HonBaseSpinSpeed reports zero for an idle WM."""
    coordinator._device = make_device({"spinSpeed": "800", "machMode": "1"})
    entity = HonBaseSpinSpeed(None, coordinator, None, appliance)
    assert entity.native_value == 0


def test_hon_base_mode_dishwasher(coordinator, appliance, make_device) -> None:
    """HonBaseMode maps a dishwasher appliance to its translation key."""
    dw_appliance = {
        **appliance,
        "applianceTypeId": 9,
        "applianceTypeName": "DW",
    }
    coordinator._device = make_device({"machMode": "1"})
    entity = HonBaseMode(None, coordinator, None, dw_appliance)
    assert entity.translation_key == "dishwasher_mode"


def test_hon_base_mode_tumbledryer(coordinator, appliance, make_device) -> None:
    """HonBaseMode maps a tumble dryer appliance to its translation key."""
    td_appliance = {
        **appliance,
        "applianceTypeId": 8,
        "applianceTypeName": "TD",
    }
    coordinator._device = make_device({"machMode": "1"})
    entity = HonBaseMode(None, coordinator, None, td_appliance)
    assert entity.translation_key == "tumbledryer_mode"


def test_hon_base_mode_purifier(coordinator, appliance, make_device) -> None:
    """HonBaseMode maps a purifier appliance to its translation key."""
    ap_appliance = {
        **appliance,
        "applianceTypeId": 7,
        "applianceTypeName": "AP",
    }
    coordinator._device = make_device({"machMode": "1"})
    entity = HonBaseMode(None, coordinator, None, ap_appliance)
    assert entity.translation_key == "purifier_mode"


def test_hon_base_mode_air_to_water(coordinator, appliance, make_device) -> None:
    """HonBaseMode maps an air-to-water appliance to its translation key."""
    aw_appliance = {
        **appliance,
        "applianceTypeId": 27,
        "applianceTypeName": "AW",
    }
    coordinator._device = make_device({"machMode": "1"})
    entity = HonBaseMode(None, coordinator, None, aw_appliance)
    assert entity.translation_key == "air_to_water_mode"
    assert entity.icon == "mdi:heat-pump-outline"


def test_hon_base_mode_water_heater(coordinator, appliance, make_device) -> None:
    """HonBaseMode maps a water heater appliance to its translation key."""
    wh_appliance = {
        **appliance,
        "applianceTypeId": 10,
        "applianceTypeName": "WH",
    }
    coordinator._device = make_device({"machMode": "1"})
    entity = HonBaseMode(None, coordinator, None, wh_appliance)
    assert entity.translation_key == "water_heater_mode"


def test_hon_base_remaining_time_wash_dryer_delayed(
    coordinator, appliance, make_device
) -> None:
    """A wash dryer in a delay mode reports only the delay."""
    wd_appliance = {
        **appliance,
        "applianceTypeId": 2,
        "applianceTypeName": "WD",
    }
    coordinator._device = make_device(
        {"remainingTimeMM": "30", "delayTime": "5", "machMode": "7"}
    )
    entity = HonBaseRemainingTime(None, coordinator, None, wd_appliance)
    assert entity.native_value == 5


def test_hon_base_remaining_time_wash_dryer_running(
    coordinator, appliance, make_device
) -> None:
    """A running wash dryer adds the delay to the remaining time."""
    wd_appliance = {
        **appliance,
        "applianceTypeId": 2,
        "applianceTypeName": "WD",
    }
    coordinator._device = make_device(
        {"remainingTimeMM": "30", "delayTime": "5", "machMode": "3"}
    )
    entity = HonBaseRemainingTime(None, coordinator, None, wd_appliance)
    assert entity.native_value == 35


def test_hon_base_program_phase_tumbledryer(
    coordinator, appliance, make_device
) -> None:
    """HonBaseProgramPhase maps a tumble dryer to its translation key."""
    td_appliance = {
        **appliance,
        "applianceTypeId": 8,
        "applianceTypeName": "TD",
    }
    coordinator._device = make_device({"prPhase": "3"})
    entity = HonBaseProgramPhase(None, coordinator, None, td_appliance)
    assert entity.translation_key == "tumbledryer_program_phase"


def test_hon_base_start_connected_fallback(coordinator, appliance, make_device) -> None:
    """HonBaseStart falls back to the connection category."""
    coordinator._device = make_device({})
    coordinator._device.attributes = {"lastConnEvent": {"category": "CONNECTED"}}
    entity = HonBaseStart(None, coordinator, None, appliance)
    assert entity.native_value is not None


def test_hon_base_end_remaining_zero(coordinator, appliance, make_device) -> None:
    """HonBaseEnd reports None when no time remains."""
    coordinator._device = make_device({"onOffStatus": "1", "remainingTimeMM": "0"})
    entity = HonBaseEnd(None, coordinator, None, appliance)
    assert entity.native_value is None


def test_hon_base_end_remaining(coordinator, appliance, make_device) -> None:
    """HonBaseEnd projects the end time from delay and remaining."""
    coordinator._device = make_device(
        {"onOffStatus": "1", "remainingTimeMM": "30", "delayTime": "5"}
    )
    entity = HonBaseEnd(None, coordinator, None, appliance)
    assert entity.native_value is not None


def test_hon_base_program(coordinator, appliance, make_device) -> None:
    """HonBaseProgram surfaces the program code."""
    coordinator._device = make_device({"prCode": "5"})
    entity = HonBaseProgram(None, coordinator, None, appliance)
    assert entity.native_value == "5"


def test_hon_base_program_phase(coordinator, appliance, make_device) -> None:
    """HonBaseProgramPhase surfaces the phase and WM icons."""
    coordinator._device = make_device({"prPhase": "3"})
    entity = HonBaseProgramPhase(None, coordinator, None, appliance)
    assert entity.native_value == "3"
    assert entity.translation_key == "wash_program_phase"


def test_hon_base_total_electricity(coordinator, appliance, make_device) -> None:
    """HonBaseTotalElectricityUsed exposes the accumulated kWh."""
    coordinator._device = make_device({"totalElectricityUsed": "5"})
    entity = HonBaseTotalElectricityUsed(None, coordinator, None, appliance)
    assert entity.native_value == 5.0


def test_hon_base_total_wash_cycle(coordinator, appliance, make_device) -> None:
    """HonBaseTotalWashCycle subtracts one from the raw counter."""
    coordinator._device = make_device({"totalWashCycle": "10"})
    entity = HonBaseTotalWashCycle(None, coordinator, None, appliance)
    assert entity.native_value == 9


def test_hon_base_mean_water(coordinator, appliance, make_device) -> None:
    """HonBaseMeanWaterConsumption averages the water used per cycle."""
    coordinator._device = make_device({"totalWaterUsed": "100", "totalWashCycle": "10"})
    entity = HonBaseMeanWaterConsumption(None, coordinator, None, appliance)
    assert entity.native_value == round(100 / 9, 2)


def test_hon_base_mean_water_no_cycles(coordinator, appliance, make_device) -> None:
    """HonBaseMeanWaterConsumption reports None without completed cycles."""
    coordinator._device = make_device({"totalWaterUsed": "0", "totalWashCycle": "1"})
    entity = HonBaseMeanWaterConsumption(None, coordinator, None, appliance)
    assert entity.native_value is None


def test_hon_base_error(coordinator, appliance, make_device) -> None:
    """HonBaseError surfaces the last error code."""
    coordinator._device = make_device({"errors": "E01"})
    entity = HonBaseError(None, coordinator, None, appliance)
    assert entity.native_value == "E01"


def test_hon_base_programs_counter(coordinator, appliance, make_device) -> None:
    """HonBaseProgramsCounter reads the nested statistics key."""
    coordinator._device = make_device({}, program_name=None)
    coordinator._device._data["statistics.programsCounter"] = "42"
    entity = HonBaseProgramsCounter(None, coordinator, None, appliance)
    assert entity.native_value == 42


SENSOR_BUILDERS: list[tuple[str, Callable[[Any, dict], Any]]] = [
    ("mode", lambda c, a: HonBaseMode(None, c, None, a)),
    ("program_name", lambda c, a: HonBaseProgramName(None, c, None, a)),
    ("temperature", lambda c, a: HonBaseTemperature(None, c, None, a, "temp", "T")),
    ("humidity", lambda c, a: HonBaseHumidity(None, c, None, a)),
    ("int", lambda c, a: HonBaseInt(None, c, None, a, "quickModeZ1", "Q")),
    ("remaining_time", lambda c, a: HonBaseRemainingTime(None, c, None, a)),
    ("indoor_pm2p5", lambda c, a: HonBaseIndoorPM2p5(None, c, None, a)),
    ("indoor_pm10", lambda c, a: HonBaseIndoorPM10(None, c, None, a)),
    ("indoor_voc", lambda c, a: HonBaseIndoorVOC(None, c, None, a)),
    ("co_level", lambda c, a: HonBaseCOlevel(None, c, None, a)),
    ("air_quality", lambda c, a: HonBaseAIRquality(None, c, None, a)),
    ("pre_filter", lambda c, a: HonBasePreFilter(None, c, None, a)),
    ("main_filter", lambda c, a: HonBaseMainFilter(None, c, None, a)),
    ("program", lambda c, a: HonBaseProgram(None, c, None, a)),
    ("program_phase", lambda c, a: HonBaseProgramPhase(None, c, None, a)),
    ("program_duration", lambda c, a: HonBaseProgramDuration(None, c, None, a)),
    ("dry_level", lambda c, a: HonBaseDryLevel(None, c, None, a)),
    ("start", lambda c, a: HonBaseStart(None, c, None, a)),
    ("end", lambda c, a: HonBaseEnd(None, c, None, a)),
    ("mean_water", lambda c, a: HonBaseMeanWaterConsumption(None, c, None, a)),
    ("total_electricity", lambda c, a: HonBaseTotalElectricityUsed(None, c, None, a)),
    ("total_wash_cycle", lambda c, a: HonBaseTotalWashCycle(None, c, None, a)),
    ("total_water", lambda c, a: HonBaseTotalWaterUsed(None, c, None, a)),
    ("weight", lambda c, a: HonBaseWeight(None, c, None, a)),
    ("current_water", lambda c, a: HonBaseCurrentWaterUsed(None, c, None, a)),
    ("error", lambda c, a: HonBaseError(None, c, None, a)),
    (
        "current_electricity",
        lambda c, a: HonBaseCurrentElectricityUsed(None, c, None, a),
    ),
    ("spin_speed", lambda c, a: HonBaseSpinSpeed(None, c, None, a)),
    ("volume", lambda c, a: HonBaseVolume(None, c, None, a)),
    ("displayed_app", lambda c, a: HonBaseDisplayedApp(None, c, None, a)),
    ("programs_counter", lambda c, a: HonBaseProgramsCounter(None, c, None, a)),
    ("current_wash_cycle", lambda c, a: HonBaseCurrentWashCycle(None, c, None, a)),
    ("detergent_percent", lambda c, a: HonBaseDetergentPercent(None, c, None, a)),
    (
        "detergent_weight",
        lambda c, a: HonBaseDetergentWeight(
            None, c, None, a, "haier_DetergentWeight", "Detergent weight"
        ),
    ),
    ("water_hardness", lambda c, a: HonBaseWaterHardness(None, c, None, a)),
    ("delay_time", lambda c, a: HonBaseDelayTime(None, c, None, a)),
    ("power", lambda c, a: HonBasePower(None, c, None, a)),
    ("work_time", lambda c, a: HonBaseWorkTime(None, c, None, a)),
]


@pytest.mark.parametrize(
    "name,builder",
    SENSOR_BUILDERS,
    ids=[name for name, _ in SENSOR_BUILDERS],
)
def test_sensor_classes_smoke(
    coordinator, appliance, make_device, full_data, name: str, builder: Callable
) -> None:
    """Every sensor class constructs cleanly and updates without errors."""
    coordinator._device = make_device(dict(full_data))
    entity = builder(coordinator, appliance)

    assert entity.unique_id.startswith(MAC)
    assert entity.translation_key
    entity.coordinator_update()
    assert entity.native_value is not None


def test_hon_base_entity_coordinator_update(
    coordinator, appliance, make_device
) -> None:
    """_handle_coordinator_update refreshes the state and writes it."""
    from unittest.mock import MagicMock, patch

    coordinator._device = make_device({"tempSel": "40"})
    entity = HonBaseSensorEntity(coordinator, appliance, "tempSel", "T")
    with patch.object(entity, "async_write_ha_state", MagicMock()):
        entity._handle_coordinator_update()
    assert entity.native_value == "40"


def test_hon_base_entity_coordinator_update_unavailable(
    coordinator, appliance, make_device
) -> None:
    """_handle_coordinator_update skips the refresh when unavailable."""
    from unittest.mock import MagicMock, patch

    coordinator._device = make_device({"tempSel": "40"})
    coordinator.last_update_success = False
    entity = HonBaseSensorEntity(coordinator, appliance, "tempSel", "T")
    with (
        patch.object(entity, "coordinator_update", MagicMock()) as update,
        patch.object(entity, "async_write_ha_state", MagicMock()),
    ):
        entity._handle_coordinator_update()
    update.assert_not_called()


def test_hon_base_entity_coordinator_update_not_implemented(
    coordinator, appliance, make_device
) -> None:
    """The abstract coordinator_update raises NotImplementedError."""
    import pytest

    from custom_components.hon.devices.base import HonBaseEntity

    coordinator._device = make_device({})
    entity = HonBaseEntity(coordinator, appliance)
    with pytest.raises(NotImplementedError):
        entity.coordinator_update()


def test_hon_base_end_connected_fallback(coordinator, appliance, make_device) -> None:
    """HonBaseEnd falls back to the connection category."""
    coordinator._device = make_device({"remainingTimeMM": "30"})
    coordinator._device.attributes = {"lastConnEvent": {"category": "CONNECTED"}}
    entity = HonBaseEnd(None, coordinator, None, appliance)
    assert entity.native_value is not None
