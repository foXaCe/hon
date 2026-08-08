"""Tests for the helper utilities and listener in the hOn integration module."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from custom_components.hon import (
    SERVICE_REGISTRY,
    _minutes_until,
    async_setup_entry,
    get_device_ids,
    get_parameters,
    update_sensor,
)
from custom_components.hon.const import DOMAIN
from tests.conftest import MAC


async def test_update_sensor(hass, mock_connection, config_entry) -> None:
    """update_sensor writes the new state on the matching entity."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, MAC)},
    )
    registry = er.async_get(hass)
    entity = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{config_entry.unique_id}_{MAC}_light_status",
        config_entry=config_entry,
        device_id=device.id,
        suggested_object_id="hon_light_status",
    )
    entity_id = entity.entity_id
    hass.states.async_set(entity_id, "off", {"friendly_name": "Light"})

    update_sensor(hass, device.id, MAC, "light_status", "on")

    assert hass.states.get(entity_id).state == "on"
    assert hass.states.get(entity_id).attributes["friendly_name"] == "Light"


def test_get_parameters_dict() -> None:
    """get_parameters parses a dict payload."""
    call = MagicMock()
    call.data = {"parameters": {"onOffStatus": "1"}}
    assert get_parameters(call) == {"onOffStatus": "1"}


def test_get_parameters_string() -> None:
    """get_parameters parses a stringified payload."""
    call = MagicMock()
    call.data = {"parameters": "{'machMode': '2'}"}
    assert get_parameters(call) == {"machMode": "2"}


def test_get_parameters_default() -> None:
    """get_parameters falls back to an empty object."""
    call = MagicMock()
    call.data = {}
    assert get_parameters(call) == {}


def test_get_device_ids() -> None:
    """get_device_ids merges device and entity ids."""
    call = MagicMock()
    call.data = {"device_id": ["device-a"], "entity_id": []}
    assert get_device_ids(MagicMock(), call) == ["device-a"]


async def test_get_device_ids_from_entity(hass, config_entry) -> None:
    """get_device_ids resolves device ids from entity ids."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, MAC)},
    )
    entity = er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        "unique",
        config_entry=config_entry,
        device_id=device.id,
    )
    call = MagicMock()
    call.data = {"device_id": [], "entity_id": [entity.entity_id]}
    assert get_device_ids(hass, call) == [device.id]


def test_minutes_until() -> None:
    """_minutes_until computes whole minutes until the target."""
    now = datetime(2026, 1, 1, 10, 0, 0)
    assert _minutes_until(now + timedelta(minutes=15), now) == 15
    assert _minutes_until(now - timedelta(minutes=5), now) == 0


async def test_update_listener_reloads(hass, mock_connection, config_entry) -> None:
    """The registered update listener reloads the entry."""
    coordinator = MagicMock()
    coordinator.device = MagicMock()
    coordinator.device.load_commands = AsyncMock()
    coordinator.device.load_statistics = AsyncMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    mock_connection.async_get_coordinator = AsyncMock(return_value=coordinator)

    with (
        patch("custom_components.hon.HonConnection", return_value=mock_connection),
        patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()),
    ):
        assert await async_setup_entry(hass, config_entry) is True

    listener = next(iter(config_entry.update_listeners))
    with patch.object(hass.config_entries, "async_reload", AsyncMock()) as reload_mock:
        await listener(hass, config_entry)
    reload_mock.assert_awaited_once_with(config_entry.entry_id)


async def test_setup_twice_skips_registration(
    hass, mock_connection, config_entry
) -> None:
    """A second setup skips re-registering the services."""
    coordinator = MagicMock()
    coordinator.device = MagicMock()
    coordinator.device.load_commands = AsyncMock()
    coordinator.device.load_statistics = AsyncMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()
    mock_connection.async_get_coordinator = AsyncMock(return_value=coordinator)

    with (
        patch("custom_components.hon.HonConnection", return_value=mock_connection),
        patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()),
    ):
        assert await async_setup_entry(hass, config_entry) is True
        assert await async_setup_entry(hass, config_entry) is True

    registry = hass.data[DOMAIN][SERVICE_REGISTRY]
    assert "turn_on_purifier" in registry
    assert "start_program" in registry
