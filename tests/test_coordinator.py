"""Tests for the hOn base coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.hon.api.exceptions import HonConnectionError
from custom_components.hon.coordinator import HonBaseCoordinator
from tests.conftest import EMAIL, MAC, build_appliance


@pytest.fixture
def coordinator(hass, mock_connection, appliance) -> HonBaseCoordinator:
    """A coordinator wired to the mocked connection."""
    return HonBaseCoordinator(hass, mock_connection, appliance, timedelta(seconds=60))


async def test_async_update_data_success(coordinator) -> None:
    """A successful refresh returns the device."""
    device = coordinator.device
    result = await coordinator._async_update_data()
    assert result is device


@pytest.mark.parametrize(
    "exc",
    [
        aiohttp.ClientError("boom"),
        TimeoutError("timeout"),
        KeyError("missing"),
        TypeError("bad"),
    ],
)
async def test_async_update_data_failures(
    coordinator, mock_connection, exc: Exception
) -> None:
    """Transport and payload failures surface as UpdateFailed."""
    mock_connection.async_get_context = AsyncMock(side_effect=exc)
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_async_set_success(coordinator, mock_connection) -> None:
    """async_set forwards the parameters to the connection."""
    await coordinator.async_set({"onOffStatus": "1"})
    mock_connection.async_set.assert_awaited_once_with(MAC, "WM", {"onOffStatus": "1"})


async def test_async_set_rejected(coordinator, mock_connection) -> None:
    """A rejected command surfaces as UpdateFailed."""
    mock_connection.async_set = AsyncMock(return_value=False)
    with pytest.raises(UpdateFailed):
        await coordinator.async_set({"onOffStatus": "1"})


@pytest.mark.parametrize("exc", [TimeoutError("timeout"), aiohttp.ClientError("boom")])
async def test_async_set_transport_error(
    coordinator, mock_connection, exc: Exception
) -> None:
    """A transport failure while sending surfaces as UpdateFailed."""
    mock_connection.async_set = AsyncMock(side_effect=exc)
    with pytest.raises(UpdateFailed):
        await coordinator.async_set({"onOffStatus": "1"})


def test_unique_id_prefix_without_entry(hass, mock_connection, appliance) -> None:
    """Without an entry the prefix is the bare MAC address."""
    coord = HonBaseCoordinator(hass, mock_connection, appliance, timedelta(seconds=60))
    assert coord.unique_id_prefix == MAC


def test_unique_id_prefix_with_entry(
    hass, mock_connection, appliance, config_entry
) -> None:
    """With an entry the prefix is namespaced by the entry unique id."""
    mock_connection.entry = config_entry
    coord = HonBaseCoordinator(hass, mock_connection, appliance, timedelta(seconds=60))
    assert coord.unique_id_prefix == f"{EMAIL}_{MAC}"


async def test_async_setup(coordinator) -> None:
    """_async_setup loads commands, statistics and context once."""
    with (
        patch.object(coordinator.device, "load_commands", AsyncMock()) as load_commands,
        patch.object(
            coordinator.device, "load_statistics", AsyncMock()
        ) as load_statistics,
        patch.object(coordinator.device, "load_context", AsyncMock()) as load_context,
    ):
        await coordinator._async_setup()
    load_commands.assert_awaited_once()
    load_statistics.assert_awaited_once()
    load_context.assert_awaited_once()


async def test_async_update_data_skips_first_context(coordinator) -> None:
    """The first update after _async_setup returns the device without refetch."""
    with (
        patch.object(coordinator.device, "load_commands", AsyncMock()),
        patch.object(coordinator.device, "load_statistics", AsyncMock()),
        patch.object(coordinator.device, "load_context", AsyncMock()) as load_context,
    ):
        await coordinator._async_setup()
        result = await coordinator._async_update_data()
    assert result is coordinator.device
    load_context.assert_awaited_once()  # only from _async_setup


async def test_async_set_auth_failed(coordinator) -> None:
    """async_set_auth_failed raises ConfigEntryAuthFailed."""
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator.async_set_auth_failed(HonConnectionError("expired"))


async def test_async_setup_cold_persists_cache(coordinator, mock_connection) -> None:
    """A cold boot fetches everything and persists the payloads."""
    commands_payload = {"applianceModel": {}}
    statistics_payload = {"programsCounter": 3}
    with (
        patch.object(
            coordinator.device,
            "load_commands",
            AsyncMock(return_value=commands_payload),
        ),
        patch.object(
            coordinator.device,
            "load_statistics",
            AsyncMock(return_value=statistics_payload),
        ),
        patch.object(coordinator.device, "load_context", AsyncMock()),
    ):
        await coordinator._async_setup()
    mock_connection.store_setup_cache.assert_called_once_with(
        MAC, "5.30.0", commands_payload, statistics_payload
    )


async def test_async_setup_warm_uses_cache(
    hass, mock_connection, appliance, config_entry
) -> None:
    """A warm boot applies the cached payloads and refreshes them behind."""
    mock_connection.entry = config_entry
    mock_connection.get_cached_setup = MagicMock(
        return_value={
            "fw_version": "5.30.0",
            "app_version": "app",
            "commands": {"c": 1},
            "statistics": {"s": 2},
        }
    )
    coordinator = HonBaseCoordinator(
        hass, mock_connection, appliance, timedelta(seconds=60)
    )
    with (
        patch.object(coordinator.device, "load_commands", AsyncMock()) as load_commands,
        patch.object(
            coordinator.device, "load_statistics", AsyncMock()
        ) as load_statistics,
        patch.object(coordinator.device, "load_context", AsyncMock()) as load_context,
    ):
        await coordinator._async_setup()
        load_commands.assert_awaited_once_with({"c": 1})
        load_statistics.assert_awaited_once_with({"s": 2})
        load_context.assert_awaited_once()
        mock_connection.store_setup_cache.assert_not_called()
        await hass.async_block_till_done(wait_background_tasks=True)
    # The deferred refresh re-fetched the live payloads and persisted them.
    assert load_commands.await_count == 2
    assert load_commands.await_args.args == ()
    mock_connection.store_setup_cache.assert_called_once()


async def test_async_setup_warm_without_entry_skips_refresh(
    hass, mock_connection, appliance
) -> None:
    """Without a config entry the warm boot skips the background refresh."""
    mock_connection.get_cached_setup = MagicMock(
        return_value={
            "fw_version": "5.30.0",
            "app_version": "app",
            "commands": {},
            "statistics": {},
        }
    )
    coordinator = HonBaseCoordinator(
        hass, mock_connection, appliance, timedelta(seconds=60)
    )
    with (
        patch.object(coordinator.device, "load_commands", AsyncMock()) as load_commands,
        patch.object(coordinator.device, "load_statistics", AsyncMock()),
        patch.object(coordinator.device, "load_context", AsyncMock()),
    ):
        await coordinator._async_setup()
        await hass.async_block_till_done(wait_background_tasks=True)
    load_commands.assert_awaited_once()


@pytest.mark.parametrize(
    "exc",
    [
        HonConnectionError("down"),
        aiohttp.ClientError("boom"),
        TimeoutError("timeout"),
    ],
)
async def test_deferred_refresh_failure_keeps_cache(
    coordinator, mock_connection, exc: Exception
) -> None:
    """A failed deferred refresh leaves the cached payloads untouched."""
    with (
        patch.object(coordinator.device, "load_commands", AsyncMock(side_effect=exc)),
        patch.object(coordinator.device, "load_statistics", AsyncMock()),
    ):
        await coordinator._async_refresh_setup_cache()
    mock_connection.store_setup_cache.assert_not_called()


def test_apply_appliance_update(coordinator) -> None:
    """The fresh appliance payload replaces the cached one in place."""
    fresh = build_appliance(extra={"fwVersion": "9.9.9"})
    coordinator.apply_appliance_update(fresh)
    assert coordinator.device.appliance["fwVersion"] == "9.9.9"
    assert coordinator.device.appliance is coordinator._appliance
