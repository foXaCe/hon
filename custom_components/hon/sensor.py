"""Sensor platform for the hOn integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .devices.sensor import (
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

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the sensor platform."""

    hon = entry.runtime_data

    appliances = []
    for appliance in hon.appliances:
        coordinator = await hon.async_get_coordinator(appliance)
        device = coordinator.device

        _LOGGER.debug("Setting up sensors for %s (%s)", device.name, device._type_name)

        if "commandHistory" in device.attributes:
            _LOGGER.debug(
                "Command History content: %s", device.attributes["commandHistory"]
            )

        appliances.extend([HonBaseProgramName(hass, coordinator, entry, appliance)])

        if device.has("machMode"):
            appliances.extend([HonBaseMode(hass, coordinator, entry, appliance)])

        if device.has("temp"):
            appliances.extend(
                [
                    HonBaseTemperature(
                        hass, coordinator, entry, appliance, "temp", "Temperature"
                    )
                ]
            )
        if device.has("tempEnv"):
            appliances.extend(
                [
                    HonBaseTemperature(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "tempEnv",
                        "Environment temperature",
                    )
                ]
            )
        if device.has("tempIndoor"):
            appliances.extend(
                [
                    HonBaseTemperature(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "tempIndoor",
                        "Indoor temperature",
                    )
                ]
            )
        if device.has("tempOutdoor"):
            appliances.extend(
                [
                    HonBaseTemperature(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "tempOutdoor",
                        "Outdoor temperature",
                    )
                ]
            )
        if device.has("tempSel"):
            appliances.extend(
                [
                    HonBaseTemperature(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "tempSel",
                        "Selected temperature",
                    )
                ]
            )
        if device.has("tempSelZ1"):
            appliances.extend(
                [
                    HonBaseTemperature(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "tempSelZ1",
                        "Selected temperature zone 1",
                    )
                ]
            )
        if device.has("tempSelZ2"):
            appliances.extend(
                [
                    HonBaseTemperature(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "tempSelZ2",
                        "Selected temperature zone 2",
                    )
                ]
            )
        if device.has("tempSelZ3"):
            appliances.extend(
                [
                    HonBaseTemperature(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "tempSelZ3",
                        "Selected temperature zone 3",
                    )
                ]
            )
        if device.has("tempZ1"):
            appliances.extend(
                [
                    HonBaseTemperature(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "tempZ1",
                        "Temperature zone 1",
                    )
                ]
            )
        if device.has("tempZ2"):
            appliances.extend(
                [
                    HonBaseTemperature(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "tempZ2",
                        "Temperature zone 2",
                    )
                ]
            )
        if device.has("tempZ3"):
            appliances.extend(
                [
                    HonBaseTemperature(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "tempZ3",
                        "Temperature zone 3",
                    )
                ]
            )

        # AW Domestic hot water sensors
        if device.has("tempDhw"):
            appliances.extend(
                [
                    HonBaseTemperature(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "tempDhw",
                        "Temperature domestic hot water",
                    )
                ]
            )
        if device.has("tempSelDhw"):
            appliances.extend(
                [
                    HonBaseTemperature(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "tempSelDhw",
                        "Selected temperature domestic hot water",
                    )
                ]
            )

        if device.has("remainingTimeMM"):
            appliances.extend([HonBaseStart(hass, coordinator, entry, appliance)])
            appliances.extend([HonBaseEnd(hass, coordinator, entry, appliance)])
            appliances.extend(
                [HonBaseRemainingTime(hass, coordinator, entry, appliance)]
            )

        if device.has("humidity") and device.getInt("humidity") > 0:
            appliances.extend(
                [HonBaseHumidity(hass, coordinator, entry, appliance, "", "")]
            )
        if device.has("humidityZ1") and device.getInt("humidityZ1") > 0:
            appliances.extend(
                [HonBaseHumidity(hass, coordinator, entry, appliance, "Z1", "zone 1")]
            )
        if device.has("humidityZ2") and device.getInt("humidityZ2") > 0:
            appliances.extend(
                [HonBaseHumidity(hass, coordinator, entry, appliance, "Z2", "zone 2")]
            )
        if device.has("humidityIndoor") and device.getFloat("humidityIndoor") > 0.0:
            appliances.extend(
                [
                    HonBaseHumidity(
                        hass, coordinator, entry, appliance, "Indoor", "indoor"
                    )
                ]
            )
        if device.has("humidityOutdoor") and device.getFloat("humidityOutdoor") > 0.0:
            appliances.extend(
                [
                    HonBaseHumidity(
                        hass, coordinator, entry, appliance, "Outdoor", "outdoor"
                    )
                ]
            )
        if device.has("humidityEnv") and device.getInt("humidityEnv") > 0:
            appliances.extend(
                [
                    HonBaseHumidity(
                        hass, coordinator, entry, appliance, "Env", "environment"
                    )
                ]
            )

        if device.has("pm2p5ValueIndoor") and device.getFloat("pm2p5ValueIndoor") > 0:
            appliances.extend([HonBaseIndoorPM2p5(hass, coordinator, entry, appliance)])
        if device.has("pm10ValueIndoor") and device.getFloat("pm10ValueIndoor") > 0:
            appliances.extend([HonBaseIndoorPM10(hass, coordinator, entry, appliance)])

        if device.has("vocValueIndoor") and device.getFloat("vocValueIndoor") > 0:
            appliances.extend([HonBaseIndoorVOC(hass, coordinator, entry, appliance)])

        if device.has("coLevel"):
            appliances.extend([HonBaseCOlevel(hass, coordinator, entry, appliance)])
        if device.has("airQuality") and device.getFloat("airQuality") > 0:
            appliances.extend([HonBaseAIRquality(hass, coordinator, entry, appliance)])
        if device.has("mainFilterStatus"):
            appliances.extend([HonBaseMainFilter(hass, coordinator, entry, appliance)])
        if device.has("preFilterStatus"):
            appliances.extend([HonBasePreFilter(hass, coordinator, entry, appliance)])

        if device.has("dryLevel"):
            appliances.extend([HonBaseDryLevel(hass, coordinator, entry, appliance)])
        if device.has("prCode"):
            appliances.extend([HonBaseProgram(hass, coordinator, entry, appliance)])
        if device.has("prPhase"):
            appliances.extend(
                [HonBaseProgramPhase(hass, coordinator, entry, appliance)]
            )
        if device.has("prTime"):
            appliances.extend(
                [HonBaseProgramDuration(hass, coordinator, entry, appliance)]
            )

        if device.has("totalWaterUsed") and device.has("totalWashCycle"):
            appliances.extend(
                [HonBaseMeanWaterConsumption(hass, coordinator, entry, appliance)]
            )
        if (
            device.has("totalElectricityUsed")
            and device.getFloat("totalElectricityUsed") > 0
        ):
            appliances.extend(
                [HonBaseTotalElectricityUsed(hass, coordinator, entry, appliance)]
            )
        if device.has("totalWashCycle"):
            appliances.extend(
                [HonBaseTotalWashCycle(hass, coordinator, entry, appliance)]
            )
        if device.has("totalWaterUsed"):
            appliances.extend(
                [HonBaseTotalWaterUsed(hass, coordinator, entry, appliance)]
            )
        if device.has("actualWeight"):
            appliances.extend([HonBaseWeight(hass, coordinator, entry, appliance)])

        if device.has("currentWaterUsed"):
            appliances.extend(
                [HonBaseCurrentWaterUsed(hass, coordinator, entry, appliance)]
            )
        if device.has("errors"):
            appliances.extend([HonBaseError(hass, coordinator, entry, appliance)])
        if device.has("currentElectricityUsed"):
            appliances.extend(
                [HonBaseCurrentElectricityUsed(hass, coordinator, entry, appliance)]
            )
        if device.has("spinSpeed"):
            appliances.extend([HonBaseSpinSpeed(hass, coordinator, entry, appliance)])

        # Parameters found for some fridges
        if device.has("quickModeZ1"):
            appliances.extend(
                [
                    HonBaseInt(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "quickModeZ1",
                        "Quick mode Zone 1",
                    )
                ]
            )
        if device.has("quickModeZ2"):
            appliances.extend(
                [
                    HonBaseInt(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "quickModeZ2",
                        "Quick mode Zone 2",
                    )
                ]
            )
        if device.has("intelligenceMode"):
            appliances.extend(
                [
                    HonBaseInt(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "intelligenceMode",
                        "Intelligence mode",
                    )
                ]
            )
        if device.has("holidayMode"):
            appliances.extend(
                [
                    HonBaseInt(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "holidayMode",
                        "Holiday mode",
                    )
                ]
            )
        if device.has("sterilizationStatus"):
            appliances.extend(
                [
                    HonBaseInt(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "sterilizationStatus",
                        "Sterilization status",
                    )
                ]
            )

        # WH (Water Heater) additional sensors
        if device.has("power"):
            appliances.extend([HonBasePower(hass, coordinator, entry, appliance)])
        if device.has("remainingVolumeHotWater"):
            appliances.extend(
                [
                    HonBaseInt(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "remainingVolumeHotWater",
                        "Remaining hot water",
                    )
                ]
            )
        if device.has("totalWorkTime"):
            appliances.extend([HonBaseWorkTime(hass, coordinator, entry, appliance)])

        # WM additional sensors
        if device.has("currentWashCycle"):
            appliances.extend(
                [HonBaseCurrentWashCycle(hass, coordinator, entry, appliance)]
            )
        if device.has("remainingRinseIterations"):
            appliances.extend(
                [
                    HonBaseInt(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "remainingRinseIterations",
                        "Remaining rinse iterations",
                    )
                ]
            )
        if device.has("detergentPercent"):
            appliances.extend(
                [HonBaseDetergentPercent(hass, coordinator, entry, appliance)]
            )
        if device.has("haier_DetergentWeight"):
            appliances.extend(
                [
                    HonBaseDetergentWeight(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "haier_DetergentWeight",
                        "Detergent weight",
                    )
                ]
            )
        if device.has("haier_SoftenerWeight"):
            appliances.extend(
                [
                    HonBaseDetergentWeight(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "haier_SoftenerWeight",
                        "Softener weight",
                    )
                ]
            )
        if device.has("weight") and not device.has("actualWeight"):
            appliances.extend([HonBaseWeight(hass, coordinator, entry, appliance)])

        # DW additional sensors
        if device.has("waterHard"):
            appliances.extend(
                [HonBaseWaterHardness(hass, coordinator, entry, appliance)]
            )
        if device.has("delayTime"):
            appliances.extend([HonBaseDelayTime(hass, coordinator, entry, appliance)])

        # TV sensors
        if device.has("volume"):
            appliances.extend([HonBaseVolume(hass, coordinator, entry, appliance)])
        if device.has("displayedApp"):
            appliances.extend(
                [HonBaseDisplayedApp(hass, coordinator, entry, appliance)]
            )

        # Statistics sensors
        if device.get("statistics.programsCounter") is not None:
            appliances.extend(
                [HonBaseProgramsCounter(hass, coordinator, entry, appliance)]
            )

    async_add_entities(appliances)
