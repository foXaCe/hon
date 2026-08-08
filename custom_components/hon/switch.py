"""Switch platform for the hOn integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .devices.switch import HonSwitchEntity, HonSwitchEntityDescription

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the switch platform."""

    hon = entry.runtime_data

    appliances = []
    for appliance in hon.appliances:
        coordinator = await hon.async_get_coordinator(appliance)
        device = coordinator.device

        if ("settings" in device.commands) and (
            device.get("silentSleepStatus", "N/A") != "N/A"
        ):
            description = HonSwitchEntityDescription(
                key="silentSleepStatus",
                name="Sleep Mode",
                icon="mdi:bed",
                translation_key="sleep_mode",
            )
            appliances.extend(
                [HonSwitchEntity(hass, coordinator, entry, appliance, description)]
            )

        if ("settings" in device.commands) and (
            device.get("screenDisplayStatus", "N/A") != "N/A"
        ):
            description = HonSwitchEntityDescription(
                key="screenDisplayStatus",
                name="Screen Display",
                icon="mdi:monitor-small",
                translation_key="screen_display_status",
            )
            appliances.extend(
                [HonSwitchEntity(hass, coordinator, entry, appliance, description)]
            )

        if ("settings" in device.commands) and (
            device.get("muteStatus", "N/A") != "N/A"
        ):
            description = HonSwitchEntityDescription(
                key="muteStatus",
                name="Silent Mode",
                icon="mdi:volume-off",
                translation_key="silent_mode",
            )
            appliances.extend(
                [HonSwitchEntity(hass, coordinator, entry, appliance, description)]
            )

        if ("settings" in device.commands) and (
            device.get("echoStatus", "N/A") != "N/A"
        ):
            description = HonSwitchEntityDescription(
                key="echoStatus",
                name="Echo",
                icon="mdi:account-voice",
                translation_key="echo_status",
            )
            appliances.extend(
                [
                    HonSwitchEntity(
                        hass, coordinator, entry, appliance, description, True
                    )
                ]
            )

        if ("settings" in device.commands) and (
            device.get("rapidMode", "N/A") != "N/A"
        ):
            description = HonSwitchEntityDescription(
                key="rapidMode",
                name="Rapid Mode",
                icon="mdi:car-turbocharger",
                translation_key="rapid_mode",
            )
            appliances.extend(
                [HonSwitchEntity(hass, coordinator, entry, appliance, description)]
            )

        if ("settings" in device.commands) and (
            device.get("10degreeHeatingStatus", "N/A") != "N/A"
        ):
            description = HonSwitchEntityDescription(
                key="10degreeHeatingStatus",
                name="10° Heating",
                icon="mdi:heat-wave",
                translation_key="10_degree_heating",
            )
            appliances.extend(
                [HonSwitchEntity(hass, coordinator, entry, appliance, description)]
            )

        if ("settings" in device.commands) and (device.get("ecoMode", "N/A") != "N/A"):
            description = HonSwitchEntityDescription(
                key="ecoMode",
                name="Eco Mode",
                icon="mdi:sprout",
                translation_key="eco_mode",
            )
            appliances.extend(
                [HonSwitchEntity(hass, coordinator, entry, appliance, description)]
            )

        if ("settings" in device.commands) and (device.get("ecoMode", "N/A") != "N/A"):
            description = HonSwitchEntityDescription(
                key="turboMode",
                name="Turbo Mode",
                icon="mdi:rocket-launch",
                translation_key="turbo_mode",
            )
            appliances.extend(
                [HonSwitchEntity(hass, coordinator, entry, appliance, description)]
            )

        if ("settings" in device.commands) and (
            device.get("healthMode", "N/A") != "N/A"
        ):
            description = HonSwitchEntityDescription(
                key="healthMode",
                name="Health Mode",
                icon="mdi:heart",
                translation_key="health_mode",
            )
            appliances.extend(
                [HonSwitchEntity(hass, coordinator, entry, appliance, description)]
            )

    async_add_entities(appliances)
