"""Binary sensor platform for the hOn integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)

from .devices.binary_sensor import (
    HonBaseChildLockStatus,
    HonBaseDoor2Status,
    HonBaseDoorLockStatus,
    HonBaseDoorStatus,
    HonBaseGenericStatus,
    HonBaseHealthMode,
    HonBaseLightStatus,
    HonBaseMuteStatus,
    HonBaseOnOff,
    HonBasePauseStatus,
    HonBasePreheating,
    HonBaseRemoteControl,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the binary sensor platform."""

    hon = entry.runtime_data

    appliances = []
    for appliance in hon.appliances:
        coordinator = await hon.async_get_coordinator(appliance)
        device = coordinator.device

        # Every device should have a OnOff status
        appliances.extend([HonBaseOnOff(hass, coordinator, entry, appliance)])

        if device.has("doorStatus"):
            appliances.extend(
                [
                    HonBaseGenericStatus(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "doorStatus",
                        "Door status",
                        BinarySensorDeviceClass.DOOR,
                    )
                ]
            )
        if device.has("defrostStatus"):
            appliances.extend(
                [
                    HonBaseGenericStatus(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "defrostStatus",
                        "Defrost status",
                        BinarySensorDeviceClass.RUNNING,
                    )
                ]
            )

        if device.has("saltStatus"):
            appliances.extend(
                [
                    HonBaseGenericStatus(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "saltStatus",
                        "Salt",
                        BinarySensorDeviceClass.PRESENCE,
                    )
                ]
            )
        if device.has("rinseAidStatus"):
            appliances.extend(
                [
                    HonBaseGenericStatus(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "rinseAidStatus",
                        "Rinse aid",
                        BinarySensorDeviceClass.PRESENCE,
                    )
                ]
            )

        if device.has("doorStatusZ1"):
            appliances.extend(
                [HonBaseDoorStatus(hass, coordinator, entry, appliance, "Z1", "zone 1")]
            )
        if device.has("doorStatusZ2"):
            appliances.extend(
                [HonBaseDoorStatus(hass, coordinator, entry, appliance, "Z2", "zone 2")]
            )
        if device.has("doorLockStatus"):
            appliances.extend(
                [HonBaseDoorLockStatus(hass, coordinator, entry, appliance)]
            )

        if device.has("door2StatusZ1"):
            appliances.extend(
                [
                    HonBaseDoor2Status(
                        hass, coordinator, entry, appliance, "Z1", "zone 1"
                    )
                ]
            )
        if device.has("door2StatusZ2"):
            appliances.extend(
                [
                    HonBaseDoor2Status(
                        hass, coordinator, entry, appliance, "Z2", "zone 2"
                    )
                ]
            )

        if device.has("lockStatus"):
            appliances.extend(
                [HonBaseChildLockStatus(hass, coordinator, entry, appliance)]
            )
        if device.has("lightStatus"):
            appliances.extend([HonBaseLightStatus(hass, coordinator, entry, appliance)])
        if device.has("remoteCtrValid"):
            appliances.extend(
                [HonBaseRemoteControl(hass, coordinator, entry, appliance)]
            )
        if device.has("preheatStatus"):
            appliances.extend([HonBasePreheating(hass, coordinator, entry, appliance)])
        if device.has("healthMode"):
            appliances.extend([HonBaseHealthMode(hass, coordinator, entry, appliance)])
        if device.has("muteStatus"):
            appliances.extend([HonBaseMuteStatus(hass, coordinator, entry, appliance)])

        # WH (Water Heater) additional binary sensors
        if device.has("heatingStatus"):
            appliances.extend(
                [
                    HonBaseGenericStatus(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "heatingStatus",
                        "Heating",
                        BinarySensorDeviceClass.HEAT,
                    )
                ]
            )
        if device.has("anodeMaintenanceStatus"):
            appliances.extend(
                [
                    HonBaseGenericStatus(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "anodeMaintenanceStatus",
                        "Anode maintenance",
                        BinarySensorDeviceClass.PROBLEM,
                    )
                ]
            )
        if device.has("tankMaintenanceStatus"):
            appliances.extend(
                [
                    HonBaseGenericStatus(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "tankMaintenanceStatus",
                        "Tank maintenance",
                        BinarySensorDeviceClass.PROBLEM,
                    )
                ]
            )

        # WM additional binary sensors
        if device.has("pause"):
            appliances.extend([HonBasePauseStatus(hass, coordinator, entry, appliance)])
        if device.has("nightWashStatus"):
            appliances.extend(
                [
                    HonBaseGenericStatus(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "nightWashStatus",
                        "Night wash",
                        BinarySensorDeviceClass.RUNNING,
                    )
                ]
            )
        if device.has("steamStatus"):
            appliances.extend(
                [
                    HonBaseGenericStatus(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "steamStatus",
                        "Steam",
                        BinarySensorDeviceClass.RUNNING,
                    )
                ]
            )
        if device.has("energySavingStatus"):
            appliances.extend(
                [
                    HonBaseGenericStatus(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "energySavingStatus",
                        "Energy saving",
                        BinarySensorDeviceClass.RUNNING,
                    )
                ]
            )

        # DW additional binary sensors
        if device.has("extraDry"):
            appliances.extend(
                [
                    HonBaseGenericStatus(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "extraDry",
                        "Extra dry",
                        BinarySensorDeviceClass.RUNNING,
                    )
                ]
            )
        if device.has("halfLoad"):
            appliances.extend(
                [
                    HonBaseGenericStatus(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "halfLoad",
                        "Half load",
                        BinarySensorDeviceClass.RUNNING,
                    )
                ]
            )
        if device.has("openDoor"):
            appliances.extend(
                [
                    HonBaseGenericStatus(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "openDoor",
                        "Open door at end",
                        BinarySensorDeviceClass.RUNNING,
                    )
                ]
            )
        if device.has("ecoExpress"):
            appliances.extend(
                [
                    HonBaseGenericStatus(
                        hass,
                        coordinator,
                        entry,
                        appliance,
                        "ecoExpress",
                        "Eco express",
                        BinarySensorDeviceClass.RUNNING,
                    )
                ]
            )

    async_add_entities(appliances)
