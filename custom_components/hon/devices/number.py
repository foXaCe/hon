"""Number entity classes for hOn devices."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from homeassistant.const import UnitOfTemperature, UnitOfTime
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..parameter import HonParameterRange
from .base import HonBaseEntity

_LOGGER = logging.getLogger(__name__)

default_values = {
    "delayTime": {
        "icon": "mdi:timer-plus",
        "native_unit_of_measurement": UnitOfTime.MINUTES,
    },
    "rinseIterations": {
        "icon": "mdi:rotate-right",
    },
    "mainWashTime": {
        "icon": "mdi:clock-start",
        "native_unit_of_measurement": UnitOfTime.MINUTES,
    },
    "dryLevel": {
        "icon": "mdi:hair-dryer",
    },
    "tempLevel": {
        "icon": "mdi:thermometer",
        "native_unit_of_measurement": UnitOfTemperature.CELSIUS,
    },
    "antiCreaseTime": {
        "icon": "mdi:timer",
        "native_unit_of_measurement": UnitOfTime.MINUTES,
    },
    "sterilizationStatus": {
        "icon": "mdi:clock-start",
    },
}


class HonBaseNumberEntity(HonBaseEntity, NumberEntity):
    """Base number entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, appliance, key, sensor_name) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, appliance)
        self._key = key
        self._attr_unique_id = self._unique_id_from_key(key, sensor_name)
        self._attr_name = sensor_name
        self.coordinator_update()

    @callback
    def _handle_coordinator_update(self):
        if not self.available:
            return
        self.coordinator_update()
        self.async_write_ha_state()

    def coordinator_update(self):
        self._attr_native_value = self._device.get(self._key)


class HonNumber(HonBaseNumberEntity):
    """Number entity bound to a settings parameter."""

    def __init__(self, hon, coordinator, appliance, description) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator, appliance, description.key, description.name)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.unique_id_prefix}-number-{description.key}"
        )

    def _get_setting(self):
        return self._device.get_setting(self.entity_description.key)

    def _refresh_bounds(self):
        setting = self._get_setting()
        if isinstance(setting, HonParameterRange):
            self._attr_native_max_value = setting.max
            self._attr_native_min_value = setting.min
            self._attr_native_step = setting.step

    @property
    def native_value(self) -> float | None:
        setting = self._get_setting()
        return None if setting is None else setting.value

    async def async_set_native_value(self, value: float) -> None:
        command_name, parameter_name = self.entity_description.key.split(".", 1)
        command = self._device.start_command(parameters={parameter_name: value})
        await command.send()
        self.coordinator.async_set_updated_data({})

    @callback
    def _handle_coordinator_update(self):
        setting = self._get_setting()
        self._refresh_bounds()
        self._attr_native_value = None if setting is None else setting.value
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return super().available and self._device.has_current_setting(
            self.entity_description.key
        )
