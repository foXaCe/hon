"""Climate platform for the hOn integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_platform

from .devices.climate import HonClimateEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    """Set up the climate platform."""

    hon = entry.runtime_data

    appliances = []
    for appliance in hon.appliances:
        if appliance["applianceTypeId"] == 11:
            coordinator = await hon.async_get_coordinator(appliance)
            appliances.append(HonClimateEntity(hass, coordinator, entry, appliance))

    async_add_entities(appliances)

    platform = entity_platform.async_get_current_platform()

    platform.async_register_entity_service(
        "climate_set_sleep_mode",
        {
            vol.Required("sleep_mode"): cv.boolean,
        },
        "async_set_sleep_mode",
    )

    platform.async_register_entity_service(
        "climate_set_screen_display",
        {
            vol.Required("screen_display"): cv.boolean,
        },
        "async_set_screen_display",
    )

    platform.async_register_entity_service(
        "climate_set_echo_mode",
        {
            vol.Required("echo_mode"): cv.boolean,
        },
        "async_set_echo_mode",
    )

    platform.async_register_entity_service(
        "climate_set_rapid_mode",
        {
            vol.Required("rapid_mode"): cv.boolean,
        },
        "async_set_rapid_mode",
    )

    platform.async_register_entity_service(
        "climate_set_silent_mode",
        {
            vol.Required("silent_mode"): cv.boolean,
        },
        "async_set_silent_mode",
    )

    platform.async_register_entity_service(
        "climate_set_wind_direction_vertical",
        {
            vol.Required("value"): cv.positive_int,
        },
        "async_set_wind_direction_vertical",
    )

    platform.async_register_entity_service(
        "climate_set_wind_direction_horizontal",
        {
            vol.Required("value"): cv.positive_int,
        },
        "async_set_wind_direction_horizontal",
    )

    platform.async_register_entity_service(
        "climate_set_eco_pilot_mode",
        {
            vol.Required("value"): cv.positive_int,
        },
        "async_set_eco_pilot_mode",
    )
