"""Button entity classes for hOn devices."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.components.persistent_notification import create
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.update_coordinator import CoordinatorEntity


class HonBaseButtonEntity(CoordinatorEntity, ButtonEntity):
    """Button that dumps the start program parameters."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, appliance) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._device = coordinator.device

        self._attr_unique_id = f"{coordinator.unique_id_prefix}_start_button"
        self._attr_translation_key = "start_button"

    @property
    def device_info(self):
        """Return the device registry info."""
        return self._device.device_info

    async def async_press(self) -> None:
        """Handle the button press."""
        command = self._device.commands.get("startProgram")
        programs = command.get_programs()
        # device_id = get_device_id(self._coordinator.hass, self.entity_id)
        device_id = None
        entry = er.async_get(self._coordinator.hass).async_get(self.entity_id)
        if entry:
            device_id = entry.device_id

        for program in programs.keys():
            command.set_program(program)
            command = self._device.commands.get("startProgram")
            alert_text, example = command.dump()

            text = f"""#### Parameters:
{alert_text}
#### Start this program with default parameters:
    service: hon.start_program
    data:
      program: {program}
    target:
      device_id: {device_id}

#### Start this program with customized parameters:
    service: hon.start_program
    data:
      program: {program}
      parameters: >-
        {example}
    target:
      device_id: {device_id}
"""
            create(self._coordinator.hass, text, "Program [" + program + "]")


class HonBaseSettingsButtonEntity(CoordinatorEntity, ButtonEntity):
    """Button that dumps the settings parameters."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, appliance) -> None:
        """Initialize the button entity."""
        super().__init__(coordinator)
        self._coordinator = coordinator
        self._device = coordinator.device

        self._attr_unique_id = f"{coordinator.unique_id_prefix}_settings_button"
        self._attr_translation_key = "settings_button"

    @property
    def device_info(self):
        """Return the device registry info."""
        return self._device.device_info

    async def async_press(self) -> None:
        """Handle the button press."""
        # device_id = get_device_id(self._coordinator.hass, self.entity_id)
        device_id = None
        entry = er.async_get(self._coordinator.hass).async_get(self.entity_id)
        if entry:
            device_id = entry.device_id
        command = self._device.commands.get("settings")
        alert_text, example = command.dump()

        text = f"""#### Parameters:
{alert_text}
#### Update settings:
    service: hon.update_settings
    data:
      parameters: >-
        {example}
    target:
      device_id: {device_id}
"""
        create(self._coordinator.hass, text, "Get all settings")
