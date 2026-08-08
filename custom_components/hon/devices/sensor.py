"""Sensor entity classes for hOn devices."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    UnitOfDensity,
    UnitOfEnergy,
    UnitOfMass,
    UnitOfPower,
    UnitOfRatio,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
)

from ..const import APPLIANCE_TYPE
from .base import HonBaseSensorEntity

_LOGGER = logging.getLogger(__name__)

divider = 1.0


class HonBaseMode(HonBaseSensorEntity):
    """Sensor showing the operation mode."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "machMode", "Mode")

        if self._type_id == APPLIANCE_TYPE.CLIMATE:
            self.translation_key = "climate_mode"

        if self._type_id in (APPLIANCE_TYPE.WASHING_MACHINE, APPLIANCE_TYPE.WASH_DRYER):
            self.translation_key = "wash_mode"
            self._attr_icon = "mdi:washing-machine"

        if self._type_id == APPLIANCE_TYPE.DISH_WASHER:
            self.translation_key = "dishwasher_mode"

        if self._type_id == APPLIANCE_TYPE.TUMBLE_DRYER:
            self.translation_key = "tumbledryer_mode"

        if self._type_id == APPLIANCE_TYPE.PURIFIER:
            self.translation_key = "purifier_mode"

        if self._type_id == APPLIANCE_TYPE.AIR_TO_WATER:
            self.translation_key = "air_to_water_mode"
            self._attr_icon = "mdi:heat-pump-outline"

        if self._type_id == APPLIANCE_TYPE.WATER_HEATER:
            self.translation_key = "water_heater_mode"
            self._attr_icon = "mdi:water-boiler"

    def coordinator_update(self):
        mode = self._device.get("machMode")
        self._attr_native_value = f"{mode}"


class HonBaseProgramName(HonBaseSensorEntity):
    """Sensor showing the current program name."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "program_name", "Program name")

        self.translation_key = "programs_" + self._type_name.lower()
        self._attr_icon = "mdi:playlist-play"

    def coordinator_update(self):
        program_name = self._device.getProgramName()

        if program_name:
            self._attr_native_value = program_name
            self._attr_available = True
            _LOGGER.debug("[%s] Program name set to: %s", self._name, program_name)
        else:
            self._attr_native_value = "No program"
            self._attr_available = True
            _LOGGER.debug("[%s] Program name set to: No program", self._name)


class HonBaseTemperature(HonBaseSensorEntity):
    """Sensor showing a temperature value."""

    def __init__(self, hass, coordinator, entry, appliance, key, name) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, key, name)

        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS


class HonBaseHumidity(HonBaseSensorEntity):
    """Sensor showing the humidity."""

    def __init__(
        self, hass, coordinator, entry, appliance, zone="Z1", zone_name="Zone 1"
    ) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, appliance, "humidity" + zone, f"Humidity {zone_name}"
        )

        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_class = SensorDeviceClass.HUMIDITY
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_icon = "mdi:water-percent"


class HonBaseInt(HonBaseSensorEntity):
    """Sensor showing an integer value."""

    def __init__(self, hass, coordinator, entry, appliance, key, name) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, key, name)


class HonBaseRemainingTime(HonBaseSensorEntity):
    """Sensor showing the remaining time."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "remainingTimeMM", "Remaining time")

        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_icon = "mdi:progress-clock"

    def coordinator_update(self):
        delay = 0
        remainingTime = self._device.getInt("remainingTimeMM")
        if self._device.has("delayTime"):
            delay = self._device.getInt("delayTime")

        mach_mode = 0
        if self._device.has("machMode"):
            mach_mode = self._device.getInt("machMode")

        # Logic from WASHING_MACHINE implementation
        if self._type_id == APPLIANCE_TYPE.WASHING_MACHINE:
            if mach_mode in (1, 6):
                self._attr_native_value = 0
            else:
                self._attr_native_value = remainingTime

        # Logic from WASH_DRYER implementation
        elif self._type_id == APPLIANCE_TYPE.WASH_DRYER:
            time = delay
            if mach_mode != 7:
                time = delay + remainingTime
            self._attr_native_value = time

        else:
            self._attr_native_value = delay + remainingTime


class HonBaseIndoorPM2p5(HonBaseSensorEntity):
    """Sensor showing the indoor PM2.5 level."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "pm2p5ValueIndoor", "Indoor PM 2.5")

        self._attr_device_class = SensorDeviceClass.PM25
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfDensity.MICROGRAMS_PER_CUBIC_METER
        self._attr_icon = "mdi:blur"


class HonBaseIndoorPM10(HonBaseSensorEntity):
    """Sensor showing the indoor PM10 level."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "pm10ValueIndoor", "Indoor PM 10")

        self._attr_device_class = SensorDeviceClass.PM10
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfDensity.MICROGRAMS_PER_CUBIC_METER
        self._attr_icon = "mdi:blur"


class HonBaseIndoorVOC(HonBaseSensorEntity):
    """Sensor showing the indoor VOC level."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "vocValueIndoor", "Indoor VOC")

        self._attr_icon = "mdi:chemical-weapon"
        self.translation_key = "voc"  # APPLIANCE_TYPE.PURIFIER

    def coordinator_update(self):
        voc = self._device.get("vocValueIndoor")
        self._attr_native_value = f"{voc}"


class HonBaseCOlevel(HonBaseSensorEntity):
    """Sensor showing the CO level."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "coLevel", "CO level")

        self._attr_device_class = SensorDeviceClass.CO2
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfRatio.PARTS_PER_MILLION
        self._attr_icon = "mdi:molecule-co2"


class HonBaseAIRquality(HonBaseSensorEntity):
    """Sensor showing the air quality index."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "airQuality", "Air quality")

        self._attr_device_class = SensorDeviceClass.AQI
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:air-filter"


class HonBasePreFilter(HonBaseSensorEntity):
    """Sensor showing the pre-filter lifetime."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "preFilterStatus", "Pre filter")

        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:air-filter"

    def coordinator_update(self):
        lifeperc = 100
        lifepercvaluee = self._device.getFloat("preFilterStatus")
        lifepercfinale = lifeperc - float(lifepercvaluee)
        self._attr_native_value = float(lifepercfinale)


class HonBaseMainFilter(HonBaseSensorEntity):
    """Sensor showing the main filter lifetime."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "mainFilterStatus", "Main filter")

        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:air-filter"

    def coordinator_update(self):
        lifeperc = 100
        lifepercvaluee = self._device.getFloat("mainFilterStatus")
        lifepercfinale = lifeperc - float(lifepercvaluee)
        self._attr_native_value = float(lifepercfinale)


class HonBaseProgram(HonBaseSensorEntity):
    """Sensor showing the program code."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "prCode", "Program code")

    def coordinator_update(self):
        program = self._device.get("prCode")
        self._attr_native_value = f"{program}"


class HonBaseProgramPhase(HonBaseSensorEntity):
    """Sensor showing the program phase."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "prPhase", "Program phase")

        if self._type_id == APPLIANCE_TYPE.TUMBLE_DRYER:
            self.translation_key = "tumbledryer_program_phase"
            self._attr_icon = "mdi:tumble-dryer"

        if self._type_id in (APPLIANCE_TYPE.WASHING_MACHINE, APPLIANCE_TYPE.WASH_DRYER):
            self.translation_key = "wash_program_phase"
            self._attr_icon = "mdi:washing-machine"

    def coordinator_update(self):
        programPhase = self._device.get("prPhase")
        self._attr_native_value = programPhase


class HonBaseProgramDuration(HonBaseSensorEntity):
    """Sensor showing the program duration."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "prTime", "Program duration")

        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_icon = "mdi:timelapse"


class HonBaseDryLevel(HonBaseSensorEntity):
    """Sensor showing the dry level."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "dryLevel", "Dry level")

        self._attr_icon = "mdi:hair-dryer"
        self.translation_key = "dry_level"

    def coordinator_update(self):
        drylevel = self._device.get("dryLevel")
        self._attr_native_value = f"{drylevel}"


class HonBaseStart(HonBaseSensorEntity):
    """Sensor showing the planned start time."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "", "Start time")

        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:clock-start"

    def coordinator_update(self):

        if not hasattr(self, "_on"):
            self._on = False

        previous = self._on
        if self._device.has("onOffStatus"):
            self._on = self._device.get("onOffStatus") == "1"
        else:
            self._on = (
                self._device.get("attributes.lastConnEvent.category") == "CONNECTED"
            )

        delay = 0
        if self._device.has("delayTime"):
            delay = self._device.getInt("delayTime")

        if delay == 0:
            if self._on is True and previous is False:
                self._attr_native_value = datetime.now(UTC).replace(second=0)
            elif self._on is False:
                self._attr_native_value = None

        else:
            self._attr_native_value = datetime.now(UTC).replace(second=0) + timedelta(
                minutes=delay
            )


class HonBaseEnd(HonBaseSensorEntity):
    """Sensor showing the planned end time."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "", "End time")

        self._attr_device_class = SensorDeviceClass.TIMESTAMP
        self._attr_icon = "mdi:clock-end"

    def coordinator_update(self):

        if not hasattr(self, "_on"):
            self._on = False

        if self._device.has("onOffStatus"):
            self._on = self._device.get("onOffStatus") == "1"
        else:
            self._on = (
                self._device.get("attributes.lastConnEvent.category") == "CONNECTED"
            )

        delay = 0
        if self._device.has("delayTime"):
            delay = self._device.getInt("delayTime")
        remaining = self._device.getInt("remainingTimeMM")

        if remaining == 0:
            self._attr_native_value = None
            return
        if self._on is False:
            self._attr_native_value = None
            return

        self._attr_available = True
        self._attr_native_value = datetime.now(UTC).replace(second=0) + timedelta(
            minutes=delay + remaining
        )


class HonBaseMeanWaterConsumption(HonBaseSensorEntity):
    """Sensor showing the mean water consumption."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "", "Mean water consumption")

        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_icon = "mdi:water-sync"

        # TODO: keys totalWashCycle, totalWaterUsed must be in the list

    def coordinator_update(self):
        if self._device.getInt("totalWashCycle") - 1 <= 0:
            self._attr_native_value = None
        else:
            self._attr_native_value = round(
                (self._device.getFloat("totalWaterUsed"))
                / (self._device.getFloat("totalWashCycle") - 1),
                2,
            )


class HonBaseTotalElectricityUsed(HonBaseSensorEntity):
    """Sensor showing the total electricity used."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, appliance, "totalElectricityUsed", "Total electricity used"
        )

        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:connection"

    def coordinator_update(self):
        self._attr_native_value = self._device.getFloat("totalElectricityUsed")


class HonBaseTotalWashCycle(HonBaseSensorEntity):
    """Sensor showing the total wash cycle count."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "totalWashCycle", "Total wash cycle")

        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:counter"

    def coordinator_update(self):
        self._attr_native_value = self._device.getInt("totalWashCycle") - 1


class HonBaseTotalWaterUsed(HonBaseSensorEntity):
    """Sensor showing the total water used."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "totalWaterUsed", "Total water used")

        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:water-pump"

    def coordinator_update(self):
        self._attr_native_value = self._device.getFloat("totalWaterUsed") / divider


class HonBaseWeight(HonBaseSensorEntity):
    """Sensor showing the estimated load weight."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "actualWeight", "Estimated weight")

        self._attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
        self._attr_device_class = SensorDeviceClass.WEIGHT
        self._attr_icon = "mdi:weight-kilogram"

    def coordinator_update(self):
        self._attr_native_value = self._device.getFloat("actualWeight")


class HonBaseCurrentWaterUsed(HonBaseSensorEntity):
    """Sensor showing the current water used."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, appliance, "currentWaterUsed", "Current water used"
        )

        self._attr_native_unit_of_measurement = UnitOfVolume.LITERS
        self._attr_device_class = SensorDeviceClass.WATER
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:water"

    def coordinator_update(self):
        self._attr_native_value = self._device.getFloat("currentWaterUsed") / divider


class HonBaseError(HonBaseSensorEntity):
    """Sensor showing the last error code."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "errors", "Error")

        self.translation_key = "error"

        self._attr_icon = "mdi:math-log"
        if self._type_id == APPLIANCE_TYPE.WASHING_MACHINE:
            self.translation_key = "washingmachine_error"

    def coordinator_update(self):
        error = self._device.get("errors")
        self._attr_native_value = f"{error}"


class HonBaseCurrentElectricityUsed(HonBaseSensorEntity):
    """Sensor showing the current electricity used."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, appliance, "currentElectricityUsed", "Current electricity used"
        )

        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL
        self._attr_icon = "mdi:lightning-bolt"

    def coordinator_update(self):
        self._attr_native_value = (
            self._device.getFloat("currentElectricityUsed") / divider
        )


class HonBaseSpinSpeed(HonBaseSensorEntity):
    """Sensor showing the spin speed."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "spinSpeed", "Spin speed")

        self._attr_native_unit_of_measurement = REVOLUTIONS_PER_MINUTE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:speedometer"

    def coordinator_update(self):
        self._attr_native_value = self._device.getInt("spinSpeed")

        if self._type_id == APPLIANCE_TYPE.WASHING_MACHINE:
            if self._device.get("machMode") in ("1", "6"):
                self._attr_native_value = 0


class HonBaseVolume(HonBaseSensorEntity):
    """Sensor showing the volume."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "volume", "Volume")

        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:volume-high"
        self._attr_native_unit_of_measurement = PERCENTAGE

    def coordinator_update(self):
        self._attr_native_value = self._device.getInt("volume")


class HonBaseDisplayedApp(HonBaseSensorEntity):
    """Sensor showing the currently displayed app."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "displayedApp", "Displayed app")

        self._attr_icon = "mdi:application"

    def coordinator_update(self):
        app = self._device.get("displayedApp")
        self._attr_native_value = f"{app}"


class HonBaseProgramsCounter(HonBaseSensorEntity):
    """Sensor showing the total programs count."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, appliance, "statistics.programsCounter", "Total programs"
        )

        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:counter"

    def coordinator_update(self):
        value = self._device.get("statistics.programsCounter")
        if value is not None:
            self._attr_native_value = int(value)


class HonBaseCurrentWashCycle(HonBaseSensorEntity):
    """Sensor showing the current wash cycle count."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(
            coordinator, appliance, "currentWashCycle", "Current wash cycle"
        )

        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:counter"

    def coordinator_update(self):
        self._attr_native_value = self._device.getInt("currentWashCycle")


class HonBaseDetergentPercent(HonBaseSensorEntity):
    """Sensor showing the detergent level."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "detergentPercent", "Detergent level")

        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:bottle-tonic"

    def coordinator_update(self):
        self._attr_native_value = self._device.getInt("detergentPercent")


class HonBaseDetergentWeight(HonBaseSensorEntity):
    """Sensor showing the detergent weight."""

    def __init__(self, hass, coordinator, entry, appliance, key, name) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, key, name)

        self._attr_native_unit_of_measurement = UnitOfMass.GRAMS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:bottle-tonic"

    def coordinator_update(self):
        self._attr_native_value = self._device.getFloat(self._key)


class HonBaseWaterHardness(HonBaseSensorEntity):
    """Sensor showing the water hardness."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "waterHard", "Water hardness")

        self._attr_icon = "mdi:water-opacity"

    def coordinator_update(self):
        self._attr_native_value = self._device.getInt("waterHard")


class HonBaseDelayTime(HonBaseSensorEntity):
    """Sensor showing the delay time."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "delayTime", "Delay time")

        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_icon = "mdi:timer-sand"

    def coordinator_update(self):
        self._attr_native_value = self._device.getInt("delayTime")


class HonBasePower(HonBaseSensorEntity):
    """Sensor showing the power consumption."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "power", "Power")

        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:lightning-bolt"

    def coordinator_update(self):
        self._attr_native_value = self._device.getInt("power")


class HonBaseWorkTime(HonBaseSensorEntity):
    """Sensor showing the total work time."""

    def __init__(self, hass, coordinator, entry, appliance) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance, "totalWorkTime", "Total work time")

        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_device_class = SensorDeviceClass.DURATION
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_icon = "mdi:timer-cog"

    def coordinator_update(self):
        self._attr_native_value = self._device.getInt("totalWorkTime")
