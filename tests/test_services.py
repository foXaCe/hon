"""Tests for the hon service handlers registered in __init__."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from custom_components.hon.const import DOMAIN
from custom_components.hon.devices.device import HonDevice
from tests.conftest import MAC

DEVICE_ID = "device-1"

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


@pytest.fixture
async def setup_hon(hass: HomeAssistant, mock_connection, config_entry):
    """Set up the integration with a mocked connection and a registry device."""
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, MAC, "WM")},
        name="Lave-linge",
    )

    coordinator = MagicMock()
    coordinator.device = MagicMock(spec=HonDevice)
    coordinator.device.get = MagicMock(return_value="CONNECTED")
    coordinator.device.load_commands = AsyncMock()
    coordinator.device.load_statistics = AsyncMock()
    coordinator.async_set = AsyncMock()
    coordinator.async_request_refresh = AsyncMock()
    coordinator.async_config_entry_first_refresh = AsyncMock()

    async def fake_get_coordinator(appliance):
        return coordinator

    async def fake_get_existing(mac):
        return coordinator

    mock_connection.async_get_coordinator = fake_get_coordinator
    mock_connection.async_get_existing_coordinator = fake_get_existing
    mock_connection.get_device = MagicMock(return_value=coordinator.device)
    mock_connection.async_set = AsyncMock(return_value=True)

    with (
        patch("custom_components.hon.HonConnection", return_value=mock_connection),
        patch("custom_components.hon.get_hOn_mac", return_value=MAC),
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        yield config_entry, coordinator, mock_connection


async def test_service_turn_on_purifier(hass, setup_hon) -> None:
    """turn_on_purifier sends the purifier start command."""
    _entry, coordinator, connection = setup_hon
    await hass.services.async_call(
        DOMAIN,
        "turn_on_purifier",
        {"device": DEVICE_ID},
        blocking=True,
    )
    connection.async_set.assert_awaited()
    assert connection.async_set.call_args[0][0] == MAC
    assert connection.async_set.call_args[0][1] == "AP"


async def test_service_set_mode_purifier(hass, setup_hon) -> None:
    """set_mode routes through the coordinator."""
    _entry, coordinator, connection = setup_hon
    await hass.services.async_call(
        DOMAIN, "set_mode", {"device": DEVICE_ID, "mode": "2"}, blocking=True
    )
    coordinator.async_set.assert_awaited()


async def test_service_turn_off(hass, setup_hon) -> None:
    """turn_off sends onOffStatus 0 through the coordinator."""
    _entry, coordinator, connection = setup_hon
    await hass.services.async_call(
        DOMAIN, "turn_off", {"device": DEVICE_ID}, blocking=True
    )
    coordinator.async_set.assert_awaited()
    params = coordinator.async_set.call_args[0][0]
    assert params["onOffStatus"] == "0"


async def test_service_turn_off_purifier(hass, setup_hon) -> None:
    """turn_off_purifier sends the purifier off command."""
    _entry, _coordinator, connection = setup_hon
    await hass.services.async_call(
        DOMAIN, "turn_off_purifier", {"device": DEVICE_ID}, blocking=True
    )
    connection.async_set.assert_awaited()
    assert connection.async_set.call_args[0][1] == "AP"


async def test_service_turn_off_oven(hass, setup_hon) -> None:
    """turn_off_oven sends the oven off command."""
    _entry, _coordinator, connection = setup_hon
    await hass.services.async_call(
        DOMAIN, "turn_off_oven", {"device": DEVICE_ID}, blocking=True
    )
    connection.async_set.assert_awaited()
    assert connection.async_set.call_args[0][1] == "OV"


async def test_service_turn_off_washingmachine(hass, setup_hon) -> None:
    """turn_off_washingmachine sends the washer off command."""
    _entry, _coordinator, connection = setup_hon
    await hass.services.async_call(
        DOMAIN,
        "turn_off_washingmachine",
        {"device": DEVICE_ID},
        blocking=True,
    )
    connection.async_set.assert_awaited()
    assert connection.async_set.call_args[0][1] == "WM"


async def test_service_set_auto_mode_purifier(hass, setup_hon) -> None:
    """set_auto_mode_purifier sends machMode 2."""
    _entry, _coordinator, connection = setup_hon
    await hass.services.async_call(
        DOMAIN, "set_auto_mode_purifier", {"device": DEVICE_ID}, blocking=True
    )
    connection.async_set.assert_awaited()
    assert connection.async_set.call_args[0][1] == "AP"
