"""Base entity classes shared across the hOn platforms."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..const import APPLIANCE_DEFAULT_NAME, DOMAIN
from ..coordinator import HonBaseCoordinator
from ..helpers import snake_case

_LOGGER = logging.getLogger(__name__)


class HonBaseEntity(CoordinatorEntity[HonBaseCoordinator]):
    """Common behaviour for every hOn entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HonBaseCoordinator,
        appliance: dict[str, Any],
    ) -> None:
        """Initialize the entity from the raw appliance payload."""
        super().__init__(coordinator)
        self._mac = appliance["macAddress"]
        self._type_id = appliance["applianceTypeId"]
        self._type_name = appliance["applianceTypeName"]
        self._brand = appliance["brand"]
        self._model = appliance["modelName"]
        self._fw_version = appliance["fwVersion"]
        self._device = coordinator.device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._mac, self._type_name)},
            "name": appliance.get(
                "nickName",
                APPLIANCE_DEFAULT_NAME.get(
                    str(self._type_id), "Device ID: " + str(self._type_id)
                ),
            ),
            "manufacturer": self._brand,
            "model": self._model,
            "sw_version": self._fw_version,
        }
        self._name = self._attr_device_info["name"]
        self._uid_prefix = coordinator.unique_id_prefix

    def _unique_id_from_key(self, key: str, fallback: str = "") -> str:
        """Build the unique id from a camelCase API key.

        Format: ``{entry_unique_id}_{mac}_{key}`` — stable across reloads and
        namespaced per config entry.
        """
        key_formatted = snake_case(key)
        if not key_formatted:
            key_formatted = snake_case(fallback)
        return f"{self._uid_prefix}_{key_formatted}"

    @callback
    def _handle_coordinator_update(self) -> None:
        if not self.available:
            return
        self.coordinator_update()
        self.async_write_ha_state()

    def coordinator_update(self) -> None:
        """Refresh the entity state from the device data."""
        raise NotImplementedError


class HonBaseBinarySensorEntity(HonBaseEntity, BinarySensorEntity):
    """Binary sensor entity reading a boolean device attribute."""

    def __init__(
        self,
        coordinator: HonBaseCoordinator,
        appliance: dict[str, Any],
        key: str,
        sensor_name: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, appliance)
        self._key = key
        self._attr_unique_id = self._unique_id_from_key(key, sensor_name)
        self._attr_name = sensor_name
        self.coordinator_update()

    def coordinator_update(self) -> None:
        self._attr_is_on = self._device.get(self._key) == "1"


class HonBaseSensorEntity(HonBaseEntity, SensorEntity):
    """Sensor entity reading a device attribute."""

    def __init__(
        self,
        coordinator: HonBaseCoordinator,
        appliance: dict[str, Any],
        key: str,
        sensor_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, appliance)
        self._key = key
        self._attr_unique_id = self._unique_id_from_key(key, sensor_name)
        self._attr_name = sensor_name
        self.coordinator_update()

    def coordinator_update(self) -> None:
        self._attr_native_value = self._device.get(self._key)


class HonBaseSwitchEntity(HonBaseEntity, SwitchEntity):
    """Switch entity bound to a settings parameter."""

    def __init__(
        self,
        coordinator: HonBaseCoordinator,
        appliance: dict[str, Any],
        entity_description,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, appliance)
        self._key = entity_description.key
        self.entity_description = entity_description
        self.translation_key = entity_description.translation_key
        self._attr_unique_id = self._unique_id_from_key(entity_description.key)
        self._attr_name = entity_description.name
        self.coordinator_update()

    def coordinator_update(self) -> None:
        self._attr_native_value = self._device.get(self._key)
