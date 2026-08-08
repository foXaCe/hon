"""Number platform for the hOn integration."""

from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntityDescription
from homeassistant.helpers import translation
from homeassistant.helpers.entity import EntityCategory

from .devices.number import HonNumber, default_values
from .parameter import HonParameterRange

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    hon = entry.runtime_data
    translations = await translation.async_get_translations(
        hass, hass.config.language, "entity"
    )

    appliances = []
    for appliance in hon.appliances:
        coordinator = await hon.async_get_coordinator(appliance)
        device = coordinator.device

        for key, parameter in coordinator.device.settings.items():
            if not isinstance(parameter, HonParameterRange):
                continue

            default_value = default_values.get(parameter.key, {})
            translation_key = (
                coordinator.device.appliance_type.lower() + "_" + parameter.key.lower()
            )

            description = NumberEntityDescription(
                key=key,
                name=translations.get(
                    f"component.hon.entity.number.{translation_key}.name", parameter.key
                ),
                entity_category=EntityCategory.CONFIG,
                translation_key=translation_key,
                icon=default_value.get("icon"),
                native_unit_of_measurement=default_value.get(
                    "native_unit_of_measurement"
                ),
            )
            appliances.append(HonNumber(hon, coordinator, appliance, description))

    async_add_entities(appliances)
