"""Binary sensor entity classes for hOn devices."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
)

from .base import HonBaseBinarySensorEntity


class HonBaseGenericStatus(HonBaseBinarySensorEntity):
    def __init__(
        self, hass, coordinator, entry, appliance, key, name, device_class
    ) -> None:
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
            self._attr_is_on = (
                self._device.get("attributes.lastConnEvent.category") == "CONNECTED"
            )


class HonBaseDoorStatus(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance, zone, zone_name) -> None:
        super().__init__(
            coordinator, appliance, "doorStatus" + zone, f"Door status {zone_name}"
        )

        self._attr_device_class = BinarySensorDeviceClass.DOOR


class HonBaseDoor2Status(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance, zone, zone_name) -> None:
        super().__init__(
            coordinator, appliance, "door2Status" + zone, f"Door 2 status {zone_name}"
        )

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

        self.translation_key = "lockstatus"
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


class HonBaseMuteStatus(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "muteStatus", "Mute")

        self._attr_icon = "mdi:volume-off"

    def coordinator_update(self):
        self._attr_is_on = self._device.get("muteStatus") == "1"


class HonBasePauseStatus(HonBaseBinarySensorEntity):
    def __init__(self, hass, coordinator, entry, appliance) -> None:
        super().__init__(coordinator, appliance, "pause", "Paused")

        self._attr_icon = "mdi:pause-circle"

    def coordinator_update(self):
        self._attr_is_on = self._device.get("pause") == "1"
