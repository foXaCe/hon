"""
Fichier: custom_components/hon/switch.py

Modifications principales:
1. Optimisation du chargement des entités
2. Mesure de performance
3. Chargement différé des commandes
"""

import logging
import asyncio
from dataclasses import dataclass
from typing import Any


from .const import DOMAIN
from .device import HonDevice
from .parameter import HonParameter, HonParameterFixed, HonParameterEnum, HonParameterRange, HonParameterProgram
from .base import HonBaseCoordinator, HonBaseSwitchEntity


from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.switch import SwitchEntityDescription, SwitchEntity

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True)
class HonControlSwitchEntityDescription(SwitchEntityDescription):
    turn_on_key: str = ""
    turn_off_key: str = ""


@dataclass(frozen=True)
class HonSwitchEntityDescription(SwitchEntityDescription):
    pass



async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    """Configuration des interrupteurs après le chargement d'une entrée."""
    start_time = asyncio.get_event_loop().time()

    hon = hass.data[DOMAIN][entry.unique_id]
    
    # Charger les appareils si nécessaire
    await hon.load_appliances_if_needed()

    appliances = []
    for appliance in hon.appliances:
        # Éviter de configurer à nouveau des appareils déjà configurés
        mac = appliance.get("macAddress", "")
        if mac in hon.configured_devices:
            continue
            
        coordinator = await hon.async_get_coordinator(appliance)
        if not coordinator:
            continue
            
        device = coordinator.device
        
        # Charger le contexte de l'appareil pour détection des caractéristiques
        try:
            if not device.attributes:
                await device.load_context()
        except Exception as e:
            _LOGGER.error(f"Failed to load context for device {mac}: {e}")
            continue

        # Vérifier les caractéristiques disponibles sans nécessairement charger les commandes
        has_sleep_mode = device.has("silentSleepStatus")
        has_screen_display = device.has("screenDisplayStatus")
        has_mute_status = device.has("muteStatus")
        has_echo_status = device.has("echoStatus")
        has_rapid_mode = device.has("rapidMode")
        has_10deg_heating = device.has("10degreeHeatingStatus")
        has_eco_mode = device.has("ecoMode")
        has_health_mode = device.has("healthMode")
        
        # Vérifier si l'appareil a des caractéristiques qui justifient le chargement des commandes
        if any([has_sleep_mode, has_screen_display, has_mute_status, has_echo_status, 
                has_rapid_mode, has_10deg_heating, has_eco_mode, has_health_mode]):
            
            # Charger les commandes si au moins une caractéristique est disponible
            if "settings" in device.commands:
                if has_sleep_mode:
                    description = HonSwitchEntityDescription(
                        key="silentSleepStatus",
                        name="Sleep Mode",
                        icon="mdi:bed",
                        translation_key="sleep_mode",
                    )
                    appliances.append(HonSwitchEntity(hass, coordinator, entry, appliance, description))
                    
                if has_screen_display:
                    description = HonSwitchEntityDescription(
                        key="screenDisplayStatus",
                        name="Screen Display",
                        icon="mdi:monitor-small",
                        translation_key="screen_display_status",
                    )
                    appliances.append(HonSwitchEntity(hass, coordinator, entry, appliance, description))
                    
                if has_mute_status:
                    description = HonSwitchEntityDescription(
                        key="muteStatus",
                        name="Silent Mode",
                        icon="mdi:volume-off",
                        translation_key="silent_mode",
                    )
                    appliances.append(HonSwitchEntity(hass, coordinator, entry, appliance, description))
                    
                if has_echo_status:
                    description = HonSwitchEntityDescription(
                        key="echoStatus",
                        name="Echo",
                        icon="mdi:account-voice",
                        translation_key="echo_status"
                    )
                    appliances.append(HonSwitchEntity(hass, coordinator, entry, appliance, description, True))
                    
                if has_rapid_mode:
                    description = HonSwitchEntityDescription(
                        key="rapidMode",
                        name="Rapid Mode",
                        icon="mdi:car-turbocharger",
                        translation_key="rapid_mode",
                    )
                    appliances.append(HonSwitchEntity(hass, coordinator, entry, appliance, description))
                    
                if has_10deg_heating:
                    description = HonSwitchEntityDescription(
                        key="10degreeHeatingStatus",
                        name="10° Heating",
                        icon="mdi:heat-wave",
                        translation_key="10_degree_heating",
                    )
                    appliances.append(HonSwitchEntity(hass, coordinator, entry, appliance, description))
                    
                if has_eco_mode:
                    description = HonSwitchEntityDescription(
                        key="ecoMode",
                        name="Eco Mode",
                        icon="mdi:sprout",
                        translation_key="eco_mode",
                    )
                    appliances.append(HonSwitchEntity(hass, coordinator, entry, appliance, description))
                    
                if has_health_mode:
                    description = HonSwitchEntityDescription(
                        key="healthMode",
                        name="Health Mode",
                        icon="mdi:heart",
                        translation_key="health_mode",
                    )
                    appliances.append(HonSwitchEntity(hass, coordinator, entry, appliance, description))

    # Ajouter les entités d'un coup
    if appliances:
        async_add_entities(appliances)
        
    end_time = asyncio.get_event_loop().time()
    _LOGGER.debug(f"switch setup took {end_time - start_time:.2f} seconds")


class HonSwitchEntity(HonBaseSwitchEntity):
    entity_description: HonSwitchEntityDescription

    def __init__(self, hass, coordinator, entry, appliance, entity_description, invert = False) -> None:
        super().__init__(coordinator, appliance, entity_description)
        self.invert = invert

    @property
    def is_on(self) -> bool | None:
        """Return True if entity is on."""
        if self.invert:
            return self._device.get(self.entity_description.key, "1") == "0"
        return self._device.get(self.entity_description.key, "0") == "1"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Allumer l'entité avec chargement différé des commandes si nécessaire"""
        # S'assurer que les commandes sont chargées
        if not self._device.commands or not "settings" in self._device.commands:
            await self._device.load_commands()
            
        setting = self._device.settings.get(f"settings.{self.entity_description.key}")
        if not setting:
            _LOGGER.error(f"Setting not found: settings.{self.entity_description.key}")
            return
            
        if type(setting) == HonParameter:
            return
            
        if self.invert:
            setting.value = setting.min if isinstance(setting, HonParameterRange) else 0
        else:
            setting.value = setting.max if isinstance(setting, HonParameterRange) else 1
            
        await self._device.commands["settings"].send()
        self._device.set(self.entity_description.key, str(setting.value))
        self.async_write_ha_state()
        self.coordinator.async_set_updated_data({})

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Éteindre l'entité avec chargement différé des commandes si nécessaire"""
        # S'assurer que les commandes sont chargées
        if not self._device.commands or not "settings" in self._device.commands:
            await self._device.load_commands()
            
        setting = self._device.settings.get(f"settings.{self.entity_description.key}")
        if not setting:
            _LOGGER.error(f"Setting not found: settings.{self.entity_description.key}")
            return
            
        if type(setting) == HonParameter:
            return
            
        if self.invert:
            setting.value = setting.max if isinstance(setting, HonParameterRange) else 1
        else:
            setting.value = setting.min if isinstance(setting, HonParameterRange) else 0

        await self._device.commands["settings"].send()
        self._device.set(self.entity_description.key, str(setting.value))
        self.async_write_ha_state()
        self.coordinator.async_set_updated_data({})

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if not super().available:
            _LOGGER.warning("HonSwitchEntity not available: super() is not")
            return False
        if not self._device.get("remoteCtrValid", "1") == "1":
            _LOGGER.warning("HonSwitchEntity not available: remoteCtrValid==1")
            return False
        if self._device.get("attributes.lastConnEvent.category") == "DISCONNECTED":
            _LOGGER.warning("HonSwitchEntity not available: DISCONNECTED")
            return False
        
        # Vérifier si les paramètres de l'entité sont disponibles sans forcer le chargement des commandes
        if not self._device.commands or not "settings" in self._device.commands:
            # Ne pas forcer le chargement des commandes lors de la vérification
            # La commande sera chargée à la demande lors des actions
            return True
            
        setting_key = f"settings.{self.entity_description.key}"
        setting = self._device.settings.get(setting_key, None)

        if setting is None:
            _LOGGER.warning("HonSwitchEntity not available: Key not found: %s", setting_key)
            return False

        return True

    @callback
    def _handle_coordinator_update(self, update: bool = True) -> None:
        self._attr_is_on = self.is_on
        if update:
            self.async_write_ha_state()
