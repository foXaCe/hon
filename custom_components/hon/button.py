"""
Fichier: custom_components/hon/button.py

Modifications principales:
1. Optimisation du chargement des entités
2. Mesure de performance
"""

import logging
import asyncio
from .const import DOMAIN
from homeassistant.config_entries import ConfigEntry

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.components.persistent_notification import create
from homeassistant.helpers.template import device_id as get_device_id

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities) -> None:
    """Configurer les boutons après avoir chargé une entrée."""
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
        
        # Charger les commandes ici si nécessaire
        if not hasattr(device, '_commands_loaded') or not device._commands_loaded:
            try:
                await device.load_commands()
            except Exception as e:
                _LOGGER.error(f"Failed to load commands for device {mac}: {e}")
                continue
                
        appliances.extend([HonBaseButtonEntity(coordinator, appliance)])
        if "settings" in device.commands:
            appliances.extend([HonBaseSettingsButtonEntity(coordinator, appliance)])
    
    if appliances:
        async_add_entities(appliances)
        
    end_time = asyncio.get_event_loop().time()
    _LOGGER.debug(f"button setup took {end_time - start_time:.2f} seconds")



class HonBaseButtonEntity(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, appliance) -> None:
        super().__init__(coordinator)
        self._coordinator   = coordinator
        self._device        = coordinator.device

        self._attr_unique_id = self._device.mac_address + "_start_button"
        self._attr_name = self._device.name + " Get programs details"

    @property
    def device_info(self):
        return self._device.device_info

    async def async_press(self) -> None:
        """Handle the button press."""
        # Vérifiez que les commandes sont chargées
        if not self._device.commands or not "startProgram" in self._device.commands:
            await self._device.load_commands()
            
        command = self._device.commands.get("startProgram")
        programs = command.get_programs()
        device_id = get_device_id(self._coordinator.hass, self.entity_id)

        for program in programs.keys():
            command.set_program(program)
            command = self._device.commands.get("startProgram")
            alert_text, example = command.dump()

            text = f"""#### Parameters:
{alert_text}
#### Start this program with default parameters:
    service: hon.start_program
    data:
      program: {program}
    target:
      device_id: {device_id}

#### Start this program with customized parameters:
    service: hon.start_program
    data:
      program: {program}
      parameters: >-
        {example}
    target:
      device_id: {device_id}
"""
            create(self._coordinator.hass, text, "Program ["+program+"]")



class HonBaseSettingsButtonEntity(CoordinatorEntity, ButtonEntity):
    def __init__(self, coordinator, appliance) -> None:
        super().__init__(coordinator)
        self._coordinator   = coordinator
        self._device        = coordinator.device

        self._attr_unique_id = self._device.mac_address + "_settings_button"
        self._attr_name = self._device.name + " Get settings details"

    @property
    def device_info(self):
        return self._device.device_info

    async def async_press(self) -> None:
        """Handle the button press."""
        # Vérifiez que les commandes sont chargées
        if not self._device.commands or not "settings" in self._device.commands:
            await self._device.load_commands()
            
        device_id = get_device_id(self._coordinator.hass, self.entity_id)
        command = self._device.commands.get("settings")
        alert_text, example = command.dump()

        text = f"""#### Parameters:
{alert_text}
#### Update settings:
    service: hon.update_settings
    data:
      parameters: >-
        {example}
    target:
      device_id: {device_id}
"""
        create(self._coordinator.hass, text, "Get all settings")
