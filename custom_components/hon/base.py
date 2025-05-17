"""
Fichier: custom_components/hon/base.py
"""
import logging
import re
from datetime import timedelta

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, APPLIANCE_DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)

class HonBaseCoordinator(DataUpdateCoordinator):
    """Coordinateur pour gérer la récupération de données des appareils hOn."""
    
    def __init__(self, hass, connector, appliance) -> None:
        """Initialise le coordinateur."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"hOn {appliance.get('macAddress')}",
            update_interval=timedelta(seconds=30),
        )
        self._connector = connector
        self._appliance = appliance
        self._device = None  # Sera défini plus tard
        self._mac = appliance.get("macAddress")

    async def _async_update_data(self):
        """Récupère les données depuis l'API hOn."""
        try:
            if self._device:
                # Charger le contexte seulement s'il n'est pas déjà chargé
                if not self._device._context_loaded:
                    await self._device.load_context()
                    
                return await self._connector.async_get_state(self._mac, self._device.appliance_type)
        except Exception as err:
            _LOGGER.error(f"Error updating hOn device {self._mac}: {err}")
            return False
            
    async def async_set(self, parameters):
        """Envoie des paramètres à l'appareil."""
        if not self._device:
            _LOGGER.error(f"Device not initialized for coordinator {self._mac}")
            return False
            
        try:
            return await self._connector.async_set(self._mac, self._device.appliance_type, parameters)
        except Exception as err:
            _LOGGER.error(f"Error setting parameters for {self._mac}: {err}")
            return False

class HonBaseBinarySensorEntity:
    """Classe de base pour les capteurs binaires hOn."""
    
    def __init__(self, coordinator, appliance, key, name) -> None:
        """Initialise l'entité."""
        self._coordinator = coordinator
        self._device = coordinator.device
        self._mac = appliance["macAddress"]
        self._type_id = appliance["applianceTypeId"]
        self._name = appliance.get("nickName", APPLIANCE_DEFAULT_NAME.get(str(self._type_id), "Device ID: " + str(self._type_id)))
        self._brand = appliance["brand"]
        self._model = appliance["modelName"]
        self._fw_version = appliance["fwVersion"]
        self._type_name = appliance["applianceTypeName"]
        self._key = key
        self._icon = None
        self._entity_id = None
        self._attr_name = self._name + " " + name
        
        # Génère un ID unique à partir de la clé
        key_formatted = re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower()
        if len(key_formatted) <= 0:
            key_formatted = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        self._attr_unique_id = self._mac + "_" + key_formatted
        
        # Définir l'état initial
        self._attr_is_on = False
        self.coordinator_update()
        
        # S'abonner aux mises à jour du coordinateur
        coordinator.async_add_listener(self._handle_coordinator_update)

    @property
    def device_info(self):
        """Infos sur l'appareil."""
        return {
            "identifiers": {
                (DOMAIN, self._mac, self._type_name)
            },
            "name": self._name,
            "manufacturer": self._brand,
            "model": self._model,
            "sw_version": self._fw_version,
        }

    @property
    def name(self):
        """Nom de l'entité."""
        return self._attr_name

    @property
    def unique_id(self):
        """ID unique de l'entité."""
        return self._attr_unique_id

    @property
    def is_on(self):
        """État actuel."""
        return self._attr_is_on

    @property
    def available(self):
        """Disponibilité de l'entité."""
        return self._coordinator.last_update_success

    @property
    def icon(self):
        """Icône de l'entité."""
        return self._icon

    @callback
    def _handle_coordinator_update(self, update = True) -> None:
        """Gère les mises à jour du coordinateur."""
        if self._coordinator.data is False:
            return
        self.coordinator_update()
        if update:
            self.async_write_ha_state()

    def coordinator_update(self):
        """Met à jour l'état basé sur les données du coordinateur."""
        self._attr_is_on = self._device.get(self._key) == "1"

class HonBaseSensorEntity:
    """Classe de base pour les capteurs hOn."""
    
    def __init__(self, coordinator, appliance, key, name) -> None:
        """Initialise l'entité."""
        self._coordinator = coordinator
        self._device = coordinator.device
        self._mac = appliance["macAddress"]
        self._type_id = appliance["applianceTypeId"]
        self._name = appliance.get("nickName", APPLIANCE_DEFAULT_NAME.get(str(self._type_id), "Device ID: " + str(self._type_id)))
        self._brand = appliance["brand"]
        self._model = appliance["modelName"]
        self._fw_version = appliance["fwVersion"]
        self._type_name = appliance["applianceTypeName"]
        self._key = key
        self._icon = None
        self.translation_key = None
        self._attr_name = self._name + " " + name
        
        # Génère un ID unique à partir de la clé
        key_formatted = re.sub(r'(?<!^)(?=[A-Z])', '_', key).lower()
        if len(key_formatted) <= 0:
            key_formatted = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
        self._attr_unique_id = self._mac + "_" + key_formatted
        
        # Définir l'état initial
        self._attr_native_value = None
        self.coordinator_update()
        
        # S'abonner aux mises à jour du coordinateur
        coordinator.async_add_listener(self._handle_coordinator_update)

    @property
    def device_info(self):
        """Infos sur l'appareil."""
        return {
            "identifiers": {
                (DOMAIN, self._mac, self._type_name)
            },
            "name": self._name,
            "manufacturer": self._brand,
            "model": self._model,
            "sw_version": self._fw_version,
        }

    @property
    def name(self):
        """Nom de l'entité."""
        return self._attr_name

    @property
    def unique_id(self):
        """ID unique de l'entité."""
        return self._attr_unique_id

    @property
    def available(self):
        """Disponibilité de l'entité."""
        return self._coordinator.last_update_success

    @property
    def icon(self):
        """Icône de l'entité."""
        return self._icon

    @callback
    def _handle_coordinator_update(self, update = True) -> None:
        """Gère les mises à jour du coordinateur."""
        if self._coordinator.data is False:
            return
        self.coordinator_update()
        if update:
            self.async_write_ha_state()

    def coordinator_update(self):
        """Met à jour l'état basé sur les données du coordinateur."""
        self._attr_native_value = self._device.get(self._key)

class HonBaseSwitchEntity:
    """Classe de base pour les interrupteurs hOn."""
    
    def __init__(self, coordinator, appliance, entity_description) -> None:
        """Initialise l'entité."""
        self._coordinator = coordinator
        self._device = coordinator.device
        self._mac = appliance["macAddress"]
        self._type_id = appliance["applianceTypeId"]
        self._name = appliance.get("nickName", APPLIANCE_DEFAULT_NAME.get(str(self._type_id), "Device ID: " + str(self._type_id)))
        self._brand = appliance["brand"]
        self._model = appliance["modelName"]
        self._fw_version = appliance["fwVersion"]
        self._type_name = appliance["applianceTypeName"]
        self.entity_description = entity_description
        
        # Génère un ID unique à partir de la clé
        self._attr_unique_id = f"{self._mac}_{entity_description.key.lower()}"
        self._attr_name = f"{self._name} {entity_description.name}"
        
        # Définir l'état initial
        self._attr_is_on = False
        self.coordinator_update()
        
        # S'abonner aux mises à jour du coordinateur
        coordinator.async_add_listener(self._handle_coordinator_update)

    @property
    def device_info(self):
        """Infos sur l'appareil."""
        return {
            "identifiers": {
                (DOMAIN, self._mac, self._type_name)
            },
            "name": self._name,
            "manufacturer": self._brand,
            "model": self._model,
            "sw_version": self._fw_version,
        }

    @property
    def name(self):
        """Nom de l'entité."""
        return self._attr_name

    @property
    def unique_id(self):
        """ID unique de l'entité."""
        return self._attr_unique_id

    @property
    def available(self):
        """Disponibilité de l'entité."""
        return self._coordinator.last_update_success

    @property
    def icon(self):
        """Icône de l'entité."""
        return self.entity_description.icon

    @callback
    def _handle_coordinator_update(self, update = True) -> None:
        """Gère les mises à jour du coordinateur."""
        if not self._coordinator.last_update_success:
            return
        self.coordinator_update()
        if update:
            self.async_write_ha_state()

    def coordinator_update(self):
        """Met à jour l'état basé sur les données du coordinateur."""
        self._attr_is_on = self._device.get(self.entity_description.key) == "1"
