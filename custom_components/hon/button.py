"""Button platform for the hOn integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .devices.button import HonBaseButtonEntity, HonBaseSettingsButtonEntity

PARALLEL_UPDATES = 0

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the button platform."""

    hon = entry.runtime_data

    appliances = []
    for appliance in hon.appliances:
        coordinator = await hon.async_get_coordinator(appliance)
        device = coordinator.device
        appliances.extend([HonBaseButtonEntity(coordinator, appliance)])
        if "settings" in device.commands:
            appliances.extend([HonBaseSettingsButtonEntity(coordinator, appliance)])
    async_add_entities(appliances)
