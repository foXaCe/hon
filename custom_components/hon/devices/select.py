"""Select entity classes for hOn devices."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntity
from homeassistant.core import callback

from ..parameter import HonParameterEnum, HonParameterFixed, HonParameterProgram
from .base import HonBaseEntity

_LOGGER = logging.getLogger(__name__)

default_values = {
    "windSpeed": {
        "icon": "mdi:fan",
    },
    "windDirectionHorizontal": {
        "icon": "mdi:swap-horizontal",
    },
    "windDirectionVertical": {
        "icon": "mdi:swap-vertical",
    },
}


class HonSelect(HonBaseEntity, SelectEntity):
    """Select entity bound to an enum setting parameter."""

    _attr_has_entity_name = True

    def __init__(self, hon, coordinator, appliance, description) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator, appliance)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_unique_id = (
            f"{coordinator.unique_id_prefix}-select-{description.key}"
        )
        self._refresh_options()

    def _get_setting(self):
        return self._device.get_setting(self.entity_description.key)

    def _refresh_options(self):
        setting = self._get_setting()
        if setting is None:
            self._attr_options = []
        elif isinstance(setting, HonParameterFixed):
            self._attr_options = [setting.value]
        else:
            self._attr_options = list(setting.values)

    @property
    def current_option(self) -> str | None:
        setting = self._get_setting()
        if setting is None:
            return None
        value = setting.value
        if value not in self._attr_options:
            return None
        return value

    async def async_select_option(self, option: str) -> None:
        command_name, parameter_name = self.entity_description.key.split(".", 1)
        if command_name == "settings":
            command = self._device.settings_command({parameter_name: option})
            await command.send()
            await self.coordinator.async_request_refresh()
            return

        if parameter_name == "program":
            command = self._device.start_command(program=option)
        else:
            command = self._device.start_command(parameters={parameter_name: option})
        await command.send()
        self.coordinator.async_set_updated_data({})

    @callback
    def _handle_coordinator_update(self):
        if not self.available:
            return
        setting = self._get_setting()
        self._refresh_options()
        self._attr_current_option = None if setting is None else setting.value
        self.async_write_ha_state()

    @property
    def available(self) -> bool:
        return super().available and self._device.has_current_setting(
            self.entity_description.key
        )
