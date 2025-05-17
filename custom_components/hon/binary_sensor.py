"""
Fichier: custom_components/hon/binary_sensor.py

Modifications principales:
1. Optimisation du chargement des entités
2. Chargement différé des appareils si nécessaire
"""

import logging
import asyncio
import json
from datetime import datetime, timedelta, timezone
from dateutil.tz import gettz
from typing import Optional
from enum import IntEnum

from .const import DOMAIN, APPLIANCE_TYPE
from .base import HonBaseCoordinator, HonBaseBinarySensorEntity

from homeassistant.core import callback
from homeassistant.helpers import entity_platform
from homeassistant.config_entries import ConfigEntry

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    """Configurer les binary_sensors après avoir chargé une entrée."""
    start_time = asyncio.get_event_loop().time()
    
    hon = hass.data[DOMAIN][entry.unique_id]
    
    # Charger les appareils si nécessaire
    await hon.load_appliances_if_needed()
    
    appliances = []
    for appliance in hon.appliances:
        # Éviter de configurer à nouveau des appareils déjà configurés
        mac = appliance.get("macAddress", "")
        if mac in hon.configured_devices:
            continue
            
        coordinator = await hon.async_get_coordinator(appliance)
        if not coordinator:
            continue
            
        device = coordinator.device

        # Charger les commandes ici plutôt que dans __init__.py pour paralléliser
        if not hasattr(device, '_commands_loaded') or not device._commands_loaded:
            try:
                await device.load_commands()
            except Exception as e:
                _LOGGER.error(f"Failed to load commands for device {mac}: {e}")
                continue

        # Every device should have a OnOff status
        appliances.extend([HonBaseOnOff(hass, coordinator, entry, appliance)])

        if device.has("doorStatus"):
            appliances.extend([HonBaseGenericStatus(hass, coordinator, entry, appliance, "doorStatus", "Door status", BinarySensorDeviceClass.DOOR)])
        if device.has("defrostStatus"):
            appliances.extend([HonBaseGenericStatus(hass, coordinator, entry, appliance, "defrostStatus", "Defrost status", BinarySensorDeviceClass.RUNNING)])

        if device.has("saltStatus"):
            appliances.extend([HonBaseGenericStatus(hass, coordinator, entry, appliance, "saltStatus", "Salt", BinarySensorDeviceClass.PRESENCE)])
        if device.has("rinseAidStatus"):
            appliances.extend([HonBaseGenericStatus(hass, coordinator, entry, appliance, "rinseAidStatus", "Rinse aid", BinarySensorDeviceClass.PRESENCE)])
        

        if device.has("doorStatusZ1"):
            appliances.extend([HonBaseDoorStatus(hass, coordinator, entry, appliance, "Z1", "zone 1")])
        if device.has("doorStatusZ2"):
            appliances.extend([HonBaseDoorStatus(hass, coordinator, entry, appliance, "Z2", "zone 2")])
        if device.has("doorLockStatus"):
            appliances.extend([HonBaseDoorLockStatus(hass, coordinator, entry, appliance)])

        if device.has("door2StatusZ1"):
            appliances.extend([HonBaseDoor2Status(hass, coordinator, entry, appliance, "Z1", "zone 1")])
        if device.has("door2StatusZ2"):
            appliances.extend([HonBaseDoor2Status(hass, coordinator, entry, appliance, "Z2", "zone 2")])

        if device.has("lockStatus"):
            appliances.extend([HonBaseChildLockStatus(hass, coordinator, entry, appliance)])
        if device.has("lightStatus"):
            appliances.extend([HonBaseLightStatus(hass, coordinator, entry, appliance)])
        if device.has("remoteCtrValid"):
            appliances.extend([HonBaseRemoteControl(hass, coordinator, entry, appliance)])
        if device.has("preheatStatus"):
            appliances.extend([HonBasePreheating(hass, coordinator, entry, appliance)])
        if device.has("healthMode"):
            appliances.extend([HonBaseHealthMode(hass, coordinator, entry, appliance)])

    if appliances:
        async_add_entities(appliances)
        
    end_time = asyncio.get_event_loop().time()
    _LOGGER.debug(f"binary_sensor setup took {end_time - start_time:.2f} seconds")



class HonBaseGenericStatus(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance, key, name, device_class) -> None:
        super().__init__(coordinator, appliance, key, name)
        self._attr_device_class = device_class



class HonBaseOnOff(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "onOffStatus", "Status")

        self._attr_device_class = BinarySensorDeviceClass.POWER

    def coordinator_update(self):
        if self._device.has("onOffStatus"):
            self._attr_is_on = self._device.get("onOffStatus") == "1"
        else:
            self._attr_is_on = self._device.get("attributes.lastConnEvent.category") == "CONNECTED"

class HonBaseDoorStatus(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance, zone, zone_name) -> None:
        super().__init__(coordinator, appliance, "doorStatus" + zone, f"Door status {zone_name}")

        self._attr_device_class = BinarySensorDeviceClass.DOOR

class HonBaseDoor2Status(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance, zone, zone_name) -> None:
        super().__init__(coordinator, appliance, "door2Status" + zone, f"Door 2 status {zone_name}")

        self._attr_device_class = BinarySensorDeviceClass.DOOR


class HonBaseLightStatus(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "lightStatus", "Light")

        self._attr_device_class = BinarySensorDeviceClass.LIGHT
        self._attr_icon = "mdi:lightbulb"

        self._attr_supported_attributes = ["SET_LIGHT"]

    @property
    def supported_attributes(self) -> set[str] | None:
        return self._attr_supported_attributes

class HonBaseRemoteControl(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "remoteCtrValid", "Remote control")

        self._attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
        self._attr_icon = "mdi:remote"


class HonBaseDoorLockStatus(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "doorLockStatus", "Door lock")

        self._attr_device_class = BinarySensorDeviceClass.LOCK

    def coordinator_update(self):
        self._attr_is_on = self._device.get("doorLockStatus") == "0"


class HonBaseChildLockStatus(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "lockStatus", "Child lock")

        translation_key = "lockStatus"
        self._attr_device_class = BinarySensorDeviceClass.LOCK

    def coordinator_update(self):
        self._attr_is_on = self._device.get("lockStatus") == "0"

class HonBasePreheating(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "preheatStatus", "Preheating")

        self._attr_device_class = BinarySensorDeviceClass.HEAT
        self._attr_icon = "mdi:thermometer-chevron-up"


class HonBaseHealthMode(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "healthMode", "Health mode")

        self._attr_device_class = BinarySensorDeviceClass.RUNNING
        self._attr_icon = "mdi:doctor"