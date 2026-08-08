"""Water heater platform for the hOn integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .const import APPLIANCE_TYPE
from .devices.water_heater import HonWaterHeaterEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up the water heater platform."""

    hon = entry.runtime_data

    appliances = []
    for appliance in hon.appliances:
        if appliance["applianceTypeId"] == APPLIANCE_TYPE.WATER_HEATER:
            coordinator = await hon.async_get_coordinator(appliance)
            appliances.append(HonWaterHeaterEntity(hass, coordinator, entry, appliance))

    async_add_entities(appliances)
