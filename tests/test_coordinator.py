"""Tests for the hOn base coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.hon.api.exceptions import HonConnectionError
from custom_components.hon.coordinator import HonBaseCoordinator
from tests.conftest import EMAIL, MAC


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
    """_async_setup loads commands and statistics once."""
    with (
        patch.object(coordinator.device, "load_commands", AsyncMock()) as load_commands,
        patch.object(
            coordinator.device, "load_statistics", AsyncMock()
        ) as load_statistics,
    ):
        await coordinator._async_setup()
    load_commands.assert_awaited_once()
    load_statistics.assert_awaited_once()


async def test_async_set_auth_failed(coordinator) -> None:
    """async_set_auth_failed raises ConfigEntryAuthFailed."""
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator.async_set_auth_failed(HonConnectionError("expired"))
