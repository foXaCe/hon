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

from .api.exceptions import HonError
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
            config_entry=hon.entry,
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

        On a warm boot the command catalogue and statistics come from the
        persisted setup cache, so only the live context blocks the setup; the
        cached payloads are then re-fetched in the background. On a cold boot
        (or after a firmware change) the three independent requests run as a
        single parallel batch and the results are persisted for the next boot.
        """
        device = self._device
        cached = self._hon.get_cached_setup(
            device.mac_address, self._appliance.get("fwVersion")
        )
        if cached is not None:
            await device.load_commands(cached["commands"])
            await device.load_statistics(cached["statistics"])
            await device.load_context()
            if self.config_entry is not None:
                self.config_entry.async_create_background_task(
                    self.hass,
                    self._async_refresh_setup_cache(),
                    f"hon deferred setup refresh {device.mac_address}",
                )
        else:
            commands, statistics, _ = await asyncio.gather(
                device.load_commands(),
                device.load_statistics(),
                device.load_context(),
            )
            self._hon.store_setup_cache(
                device.mac_address,
                self._appliance.get("fwVersion"),
                commands,
                statistics,
            )
        self._initial_context_loaded = True

    async def _async_refresh_setup_cache(self) -> None:
        """Re-fetch the catalogue and statistics that a warm boot served stale.

        Runs in the background after a cache-backed setup: statistics evolve
        over time and the catalogue can change server-side, so the live
        payloads replace the cached ones and are persisted for the next boot.
        A failure here is harmless — the cached data stays in place.
        """
        device = self._device
        try:
            commands, statistics = await asyncio.gather(
                device.load_commands(),
                device.load_statistics(),
            )
        except (aiohttp.ClientError, TimeoutError, HonError) as err:
            _LOGGER.debug(
                "Deferred setup refresh failed for %s: %s", device.mac_address, err
            )
            return
        self._hon.store_setup_cache(
            device.mac_address,
            self._appliance.get("fwVersion"),
            commands,
            statistics,
        )
        self.async_update_listeners()

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
