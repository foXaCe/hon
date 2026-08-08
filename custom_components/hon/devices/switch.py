"""Switch entity classes for hOn devices."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.core import callback

from ..parameter import HonParameter, HonParameterRange
from .base import HonBaseSwitchEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class HonControlSwitchEntityDescription(SwitchEntityDescription):
    """Switch description with dedicated turn on/off keys."""

    turn_on_key: str | None = None
    turn_off_key: str | None = None


@dataclass(frozen=True)
class HonSwitchEntityDescription(SwitchEntityDescription):
    """Switch entity description."""


class HonSwitchEntity(HonBaseSwitchEntity):
    """Switch entity controlling a settings parameter."""

    entity_description: HonSwitchEntityDescription

    def __init__(
        self, hass, coordinator, entry, appliance, entity_description, invert=False
    ) -> None:
        """Initialize the switch entity."""
        super().__init__(coordinator, appliance, entity_description)
        self.invert = invert

    def _setting_key(self) -> str:
        return f"settings.{self.entity_description.key}"

    def _setting(self):
        return self._device.settings.get(self._setting_key())

    def _target_value(self, turn_on: bool) -> str:
        value = "1" if turn_on else "0"
        if self.invert:
            value = "0" if turn_on else "1"
        return value

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        if self.invert == True:
            return self._device.get(self.entity_description.key, "1") == "0"
        return self._device.get(self.entity_description.key, "0") == "1"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        setting = self._setting()
        if setting is not None:
            if type(setting) == HonParameter:
                return
            if self.invert:
                setting.value = (
                    setting.min if isinstance(setting, HonParameterRange) else 0
                )
            else:
                setting.value = (
                    setting.max if isinstance(setting, HonParameterRange) else 1
                )
            await self._device.commands["settings"].send()
            value = str(setting.value)
        else:
            value = self._target_value(True)
            await self.coordinator.async_set({self.entity_description.key: value})

        self._device.set(self.entity_description.key, value)
        self.async_write_ha_state()
        self.coordinator.async_set_updated_data({})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        setting = self._setting()
        if setting is not None:
            if type(setting) == HonParameter:
                return
            if self.invert:
                setting.value = (
                    setting.max if isinstance(setting, HonParameterRange) else 1
                )
            else:
                setting.value = (
                    setting.min if isinstance(setting, HonParameterRange) else 0
                )
            await self._device.commands["settings"].send()
            value = str(setting.value)
        else:
            value = self._target_value(False)
            await self.coordinator.async_set({self.entity_description.key: value})

        self._device.set(self.entity_description.key, value)
        self.async_write_ha_state()
        self.coordinator.async_set_updated_data({})

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not super().available:
            _LOGGER.debug("HonSwitchEntity not available: coordinator update failed")
            return False
        if not self._device.get("remoteCtrValid", "1") == "1":
            _LOGGER.debug("HonSwitchEntity not available: remoteCtrValid")
            return False
        if self._device.get("attributes.lastConnEvent.category") == "DISCONNECTED":
            _LOGGER.debug("HonSwitchEntity not available: device DISCONNECTED")
            return False

        setting = self._setting()

        if setting is None:
            return self._device.get(self.entity_description.key, None) is not None

        # _LOGGER.warning(setting)
        # if isinstance(setting, HonParameterRange) and len(setting.values) < 2:
        #    return False
        return True

    @callback
    def _handle_coordinator_update(self, update: bool = True) -> None:
        # if( self._key == "screenDisplayStatus" ):
        #    _LOGGER.warning(f"HonSwitchEntity screenDisplayStatus value {self._device.get(self._key)}" )
        # if( self._key == "echoStatus" ):
        #    _LOGGER.warning(f"HonSwitchEntity echoStatus value {self._device.get(self._key)}" )
        self._attr_is_on = self.is_on
        if update:
            self.async_write_ha_state()
