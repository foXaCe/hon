"""Select platform for the hOn integration."""

from __future__ import annotations

import logging

from homeassistant.components.select import SelectEntityDescription
from homeassistant.helpers import translation
from homeassistant.helpers.entity import EntityCategory

from .devices.select import HonSelect, default_values
from .parameter import HonParameterEnum, HonParameterProgram

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities) -> None:
    hon = entry.runtime_data
    translations = await translation.async_get_translations(
        hass, hass.config.language, "entity"
    )

    appliances = []
    for appliance in hon.appliances:
        coordinator = await hon.async_get_coordinator(appliance)

        for key, parameter in coordinator.device.settings.items():
            if not isinstance(parameter, (HonParameterEnum, HonParameterProgram)):
                continue
            if key.startswith("settings.") and set(parameter.values) == {"0", "1"}:
                continue

            default_value = default_values.get(parameter.key, {})
            translation_key = (
                coordinator.device.appliance_type.lower() + "_" + parameter.key.lower()
            )

            description = SelectEntityDescription(
                key=key,
                name=translations.get(
                    f"component.hon.entity.select.{translation_key}.name", parameter.key
                ),
                entity_category=EntityCategory.CONFIG,
                translation_key=translation_key,
                icon=default_value.get("icon"),
            )
            appliances.append(HonSelect(hon, coordinator, appliance, description))

    async_add_entities(appliances)
