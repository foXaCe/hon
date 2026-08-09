"""Coordinator for the hOn integration."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import aiohttp
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .devices.device import HonDevice

if TYPE_CHECKING:
    from datetime import timedelta

    from homeassistant.core import HomeAssistant

    from .api.client import HonConnection

_LOGGER = logging.getLogger(__name__)


class HonBaseCoordinator(DataUpdateCoordinator[HonDevice]):
    """Fetch device context from the hOn cloud and expose it to entities.

    Each appliance owned by the account gets its own coordinator. The
    coordinator holds a mutable :class:`HonDevice` instance that entities
    read through :attr:`device` (aliased to :attr:`data` once refreshed).
    """

    def __init__(
        self,
        hass: HomeAssistant,
        hon: HonConnection,
        appliance: dict[str, Any],
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="hOn Device",
            update_interval=update_interval,
        )
        self._hon = hon
        self._appliance = appliance
        self._device = HonDevice(hon, self, appliance)
        self._initial_context_loaded = False

    @property
    def device(self) -> HonDevice:
        """Return the device managed by this coordinator."""
        return self._device

    @property
    def unique_id_prefix(self) -> str:
        """Return the stable per-entry prefix for entity unique ids."""
        if self._hon.entry is not None and self._hon.entry.unique_id:
            return f"{self._hon.entry.unique_id}_{self._device.mac_address}"
        return self._device.mac_address

    async def _async_setup(self) -> None:
        """Load commands, statistics and context once before the first refresh.

        These three requests are independent, so running them concurrently
        replaces three serial round-trips (commands/statistics, then context)
        with a single parallel batch, speeding up the boot.
        """
        await asyncio.gather(
            self._device.load_commands(),
            self._device.load_statistics(),
            self._device.load_context(),
        )
        self._initial_context_loaded = True

    async def _async_update_data(self) -> HonDevice:
        """Refresh the device context and return the device."""
        if self._initial_context_loaded:
            self._initial_context_loaded = False
            return self._device
        try:
            await self._device.load_context()
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Unable to update hOn device context: {err}") from err
        except TimeoutError as err:
            raise UpdateFailed(
                f"Timeout while updating hOn device context: {err}"
            ) from err
        except (KeyError, TypeError) as err:
            _LOGGER.warning("Unexpected hOn device payload: %s", err)
            raise UpdateFailed("Unexpected hOn device payload") from err
        return self._device

    async def async_set(self, parameters: dict[str, str]) -> None:
        """Send a settings update to the cloud."""
        try:
            result = await self._hon.async_set(
                self._device.mac_address, self._device.appliance_type, parameters
            )
        except (TimeoutError, aiohttp.ClientError) as err:
            raise UpdateFailed(f"Unable to send command: {err}") from err
        if not result:
            raise UpdateFailed("hOn command rejected by the cloud")

    async def async_set_auth_failed(self, err: Exception) -> None:
        """Mark authentication as failed so HA triggers the reauth flow."""
        raise ConfigEntryAuthFailed from err
