"""Provide info to system health."""

from __future__ import annotations

from typing import Any

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .const import API_URL, DOMAIN


@callback
def async_register(
    hass: HomeAssistant, register: system_health.SystemHealthRegistration
) -> None:
    """Register system health callbacks."""
    register.async_register_info(system_health_info)


async def system_health_info(hass: HomeAssistant) -> dict[str, Any]:
    """Get info for the info page."""
    entries = hass.config_entries.async_entries(DOMAIN)
    if not entries:
        return {"error": "No hOn config entries"}

    hon = entries[0].runtime_data
    coordinators = list(hon._coordinator_dict.values())

    return {
        "can_reach_server": await system_health.async_check_can_reach_url(
            hass, API_URL
        ),
        "appliances": len(hon.appliances),
        "all_updates_ok": bool(coordinators)
        and all(c.last_update_success for c in coordinators),
    }
