"""Tests for the hon system health."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch


async def test_system_health_info(hass, mock_connection, config_entry) -> None:
    """System health reports reachability and coordinator status."""
    config_entry.runtime_data = mock_connection
    mock_connection._coordinator_dict = {}

    from custom_components.hon.system_health import system_health_info

    with (
        patch(
            "custom_components.hon.system_health.system_health.async_check_can_reach_url",
            AsyncMock(return_value=True),
        ),
        patch(
            "homeassistant.config_entries.ConfigEntries.async_entries",
            return_value=[config_entry],
        ),
    ):
        result = await system_health_info(hass)

    assert result["can_reach_server"] is True
    assert result["appliances"] == 1
    assert result["all_updates_ok"] is False  # aucun coordinateur


async def test_system_health_no_entry(hass) -> None:
    """System health reports an error without any config entry."""
    from custom_components.hon.system_health import system_health_info

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[],
    ):
        result = await system_health_info(hass)
    assert result == {"error": "No hOn config entries"}
