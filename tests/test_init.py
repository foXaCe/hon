"""Tests for the hOn integration entry setup/unload/migration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

from custom_components.hon import (
    async_migrate_entry,
    async_remove_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.hon.api.exceptions import (
    HonAuthenticationError,
    HonConnectionError,
)
from custom_components.hon.const import DOMAIN, PLATFORMS
from tests.conftest import EMAIL, MAC, MAC2, build_appliance

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _coordinator_mock() -> MagicMock:
    """Build a coordinator mock with the device hooks setup expects."""
    device = MagicMock()
    device.load_commands = AsyncMock()
    device.load_statistics = AsyncMock()
    coordinator = MagicMock()
    coordinator.device = device
    coordinator.async_config_entry_first_refresh = AsyncMock()
    return coordinator


async def test_async_setup_entry_success(hass, mock_connection, config_entry) -> None:
    """A successful setup stores the connection and forwards platforms."""
    coordinator = _coordinator_mock()
    mock_connection.async_get_coordinator = AsyncMock(return_value=coordinator)

    with (
        patch("custom_components.hon.HonConnection", return_value=mock_connection),
        patch.object(
            hass.config_entries, "async_forward_entry_setups", AsyncMock()
        ) as forward,
    ):
        assert await async_setup_entry(hass, config_entry) is True

    assert config_entry.runtime_data is mock_connection
    forward.assert_awaited_once_with(config_entry, PLATFORMS)
    coordinator.async_config_entry_first_refresh.assert_awaited_once()


async def test_async_setup_entry_auth_failed(
    hass, mock_connection, config_entry
) -> None:
    """An authentication failure raises ConfigEntryAuthFailed."""
    mock_connection.async_restore_or_authorize = AsyncMock(
        side_effect=HonAuthenticationError("bad")
    )
    with (
        patch("custom_components.hon.HonConnection", return_value=mock_connection),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await async_setup_entry(hass, config_entry)


async def test_async_setup_entry_auth_failed_when_not_ok(
    hass, mock_connection, config_entry
) -> None:
    """A falsy authorize result raises ConfigEntryAuthFailed."""
    mock_connection.async_restore_or_authorize = AsyncMock(return_value=False)
    with (
        patch("custom_components.hon.HonConnection", return_value=mock_connection),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await async_setup_entry(hass, config_entry)


async def test_async_setup_entry_not_ready(hass, mock_connection, config_entry) -> None:
    """A connection failure raises ConfigEntryNotReady."""
    mock_connection.async_restore_or_authorize = AsyncMock(
        side_effect=HonConnectionError("down")
    )
    with (
        patch("custom_components.hon.HonConnection", return_value=mock_connection),
        pytest.raises(ConfigEntryNotReady),
    ):
        await async_setup_entry(hass, config_entry)


async def test_async_unload_entry(hass, mock_connection, config_entry) -> None:
    """Unloading returns True and closes the connection."""
    config_entry.runtime_data = mock_connection
    with patch.object(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
    ):
        assert await async_unload_entry(hass, config_entry) is True
    mock_connection.async_close.assert_awaited_once()


async def test_async_unload_entry_failed(hass, mock_connection, config_entry) -> None:
    """A failed platform unload returns False without closing."""
    config_entry.runtime_data = mock_connection
    with patch.object(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=False)
    ):
        assert await async_unload_entry(hass, config_entry) is False
    mock_connection.async_close.assert_not_awaited()


async def test_async_migrate_entry_from_v1(hass, config_entry_v1) -> None:
    """Migration from v1 prefixes entity unique ids with the entry id."""
    registry = er.async_get(hass)
    entity = registry.async_get_or_create(
        "sensor", DOMAIN, "mach_mode", config_entry=config_entry_v1
    )
    entity_id = entity.entity_id

    assert await async_migrate_entry(hass, config_entry_v1) is True
    assert config_entry_v1.version == 2
    assert registry.async_get(entity_id).unique_id == f"{EMAIL}_mach_mode"


async def test_async_migrate_entry_from_v1_preserves_prefix(
    hass, config_entry_v1
) -> None:
    """Entities already carrying the entry prefix are left untouched."""
    registry = er.async_get(hass)
    entity = registry.async_get_or_create(
        "sensor",
        DOMAIN,
        f"{EMAIL}_mach_mode",
        config_entry=config_entry_v1,
    )
    entity_id = entity.entity_id

    assert await async_migrate_entry(hass, config_entry_v1) is True
    assert registry.async_get(entity_id).unique_id == f"{EMAIL}_mach_mode"


async def test_async_migrate_entry_skips_current_version(hass, config_entry) -> None:
    """Entries already on the current version migrate without changes."""
    assert await async_migrate_entry(hass, config_entry) is True
    assert config_entry.version == 2


async def test_async_setup_entry_loads_setup_cache(
    hass, mock_connection, config_entry
) -> None:
    """Setup loads the persisted setup cache before the first refresh."""
    coordinator = _coordinator_mock()
    mock_connection.async_get_coordinator = AsyncMock(return_value=coordinator)

    with (
        patch("custom_components.hon.HonConnection", return_value=mock_connection),
        patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()),
    ):
        assert await async_setup_entry(hass, config_entry) is True

    mock_connection.async_load_setup_cache.assert_awaited_once()


async def test_async_remove_entry_removes_cache(hass, config_entry) -> None:
    """Removing the entry deletes the persisted setup cache."""
    with patch(
        "custom_components.hon.async_remove_setup_cache", AsyncMock()
    ) as remove_cache:
        await async_remove_entry(hass, config_entry)
    remove_cache.assert_awaited_once_with(hass, config_entry.entry_id)


async def test_async_setup_entry_warm_parallel(
    hass, mock_connection, config_entry
) -> None:
    """A warm boot probes the session and loads contexts concurrently."""
    cached = build_appliance()
    fresh = build_appliance(extra={"fwVersion": "6.0.0"})
    mock_connection.get_cached_appliances = MagicMock(return_value=[cached])
    mock_connection.appliances = [fresh]
    coordinator = _coordinator_mock()
    coordinator.device.mac_address = MAC
    mock_connection.async_get_coordinator = AsyncMock(return_value=coordinator)

    with (
        patch("custom_components.hon.HonConnection", return_value=mock_connection),
        patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()),
    ):
        assert await async_setup_entry(hass, config_entry) is True

    mock_connection.async_restore_or_authorize.assert_awaited_once()
    coordinator.async_config_entry_first_refresh.assert_awaited_once()
    coordinator.apply_appliance_update.assert_called_once_with(fresh)
    mock_connection.prune_coordinators.assert_called_once_with({MAC})
    mock_connection.store_cached_appliances.assert_called_once()


async def test_async_setup_entry_warm_removed_appliance_does_not_block(
    hass, mock_connection, config_entry
) -> None:
    """A cached appliance gone from the account must not block the setup."""
    removed = build_appliance(mac=MAC2)
    fresh = build_appliance()
    stale_coordinator = _coordinator_mock()
    stale_coordinator.device.mac_address = MAC2
    stale_coordinator.async_config_entry_first_refresh = AsyncMock(
        side_effect=ConfigEntryNotReady("gone")
    )
    fresh_coordinator = _coordinator_mock()
    fresh_coordinator.device.mac_address = MAC
    mock_connection.get_cached_appliances = MagicMock(return_value=[removed])
    mock_connection.appliances = [fresh]
    mock_connection.async_get_coordinator = AsyncMock(
        side_effect=[stale_coordinator, fresh_coordinator]
    )

    with (
        patch("custom_components.hon.HonConnection", return_value=mock_connection),
        patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()),
    ):
        assert await async_setup_entry(hass, config_entry) is True

    fresh_coordinator.async_config_entry_first_refresh.assert_awaited_once()
    mock_connection.prune_coordinators.assert_called_once_with({MAC})


async def test_async_setup_entry_warm_refresh_failure_still_owned(
    hass, mock_connection, config_entry
) -> None:
    """A refresh failure for an appliance still owned surfaces as not-ready."""
    appliance = build_appliance()
    mock_connection.get_cached_appliances = MagicMock(return_value=[appliance])
    mock_connection.appliances = [appliance]
    coordinator = _coordinator_mock()
    coordinator.device.mac_address = MAC
    coordinator.async_config_entry_first_refresh = AsyncMock(
        side_effect=ConfigEntryNotReady("down")
    )
    mock_connection.async_get_coordinator = AsyncMock(return_value=coordinator)

    with (
        patch("custom_components.hon.HonConnection", return_value=mock_connection),
        pytest.raises(ConfigEntryNotReady),
    ):
        await async_setup_entry(hass, config_entry)


async def test_async_setup_entry_warm_probe_auth_failure(
    hass, mock_connection, config_entry
) -> None:
    """An auth failure during the parallel probe raises ConfigEntryAuthFailed."""
    mock_connection.get_cached_appliances = MagicMock(return_value=[build_appliance()])
    coordinator = _coordinator_mock()
    coordinator.device.mac_address = MAC
    mock_connection.async_get_coordinator = AsyncMock(return_value=coordinator)
    mock_connection.async_restore_or_authorize = AsyncMock(
        side_effect=HonAuthenticationError("bad")
    )

    with (
        patch("custom_components.hon.HonConnection", return_value=mock_connection),
        pytest.raises(ConfigEntryAuthFailed),
    ):
        await async_setup_entry(hass, config_entry)
