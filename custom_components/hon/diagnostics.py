"""Diagnostics support for the hOn integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN
from .coordinator import HonBaseCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

TO_REDACT = {
    "password",
    "id_token",
    "cognito_token",
    "refresh_token",
    "email",
    "serialNumber",
    "serial_number",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry.

    Exposes the raw entry data (redacted), the appliances (redacted) and a
    snapshot of every device context — redacting tokens, credentials and
    serial numbers.
    """
    hon = entry.runtime_data

    coordinators: dict[str, dict[str, Any]] = {}
    for coordinator in hon._coordinator_dict.values():
        if not isinstance(coordinator, HonBaseCoordinator):
            continue
        coordinators[coordinator.device.mac_address] = {
            "last_update_success": coordinator.last_update_success,
            "data": coordinator.device.attributes,
        }

    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    registry_entities = [
        {
            "entity_id": entity.entity_id,
            "platform": entity.platform,
            "unique_id": entity.unique_id,
            "device_id": entity.device_id,
            "disabled_by": entity.disabled_by,
        }
        for entity in entity_registry.entities.values()
        if entity.config_entry_id == entry.entry_id
    ]

    return {
        "entry": async_redact_data(entry.data, TO_REDACT),
        "options": async_redact_data(entry.options, TO_REDACT),
        "appliances": async_redact_data(hon.appliances, TO_REDACT),
        "coordinators": async_redact_data(coordinators, TO_REDACT),
        "entities": registry_entities,
        "devices": [
            async_redact_data(
                {
                    "id": device.id,
                    "name": device.name,
                    "identifiers": list(device.identifiers),
                    "manufacturer": device.manufacturer,
                    "model": device.model,
                    "sw_version": device.sw_version,
                },
                TO_REDACT,
            )
            for device in device_registry.devices.values()
            if entry.entry_id in device.config_entry_id
        ],
    }
