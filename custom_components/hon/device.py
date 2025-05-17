import logging

from homeassistant.helpers.update_coordinator import (DataUpdateCoordinator,CoordinatorEntity)

from .const import DOMAIN, APPLIANCE_DEFAULT_NAME
from .command import HonCommand
from .parameter import HonParameterFixed, HonParameterEnum

_LOGGER = logging.getLogger(__name__)

class HonDevice(CoordinatorEntity):
    def __init__(self, hon, coordinator, appliance) -> None:
        super().__init__(coordinator)

        self._hon           = hon
        self._coordinator   = coordinator
        self._appliance     = appliance
        self._brand         = appliance["brand"]
        self._type_name     = appliance["applianceTypeName"]
        self._type_id       = appliance["applianceTypeId"]
        self._name          = appliance.get("nickName", APPLIANCE_DEFAULT_NAME.get(str(self._type_id), "Device ID: " + str(self._type_id)))
        self._mac           = appliance["macAddress"]
        self._model         = appliance["modelName"]
        self._series        = appliance["series"]
        self._model_id      = appliance["applianceModelId"]
        self._serial_number = appliance["serialNumber"]
        self._fw_version    = appliance["fwVersion"]

        self._commands              = {}
        self._appliance_model       = {}
        self._attributes            = {}
        self._statistics            = {}
        self._commands_loaded       = False
        self._context_loaded        = False
        self._statistics_loaded     = False


    def __getitem__(self, item):
        if "." in item:
            result = self.data
            for key in item.split("."):
                if all([k in "0123456789" for k in key]) and type(result) is list:
                    result = result[int(key)]
                else:
                    result = result[key]
            return result
        else:
            if item in self.data:
                return self.data[item]
            if item in self.attributes["parameters"]:
                return self.attributes["parameters"].get(item)
            return self.appliance[item]

    def set(self, item, value):
        if item in self.data:
            self.data[item] = value
        elif item in self.attributes["parameters"]:
            self.attributes["parameters"][item] = value
        else: 
            self.appliance[item] = value
    
    def get(self, item, default=None):
        try:
            return self[item]
        except (KeyError, IndexError):
            return default
    
    def getInt(self, item):
        return int(self.get(item,0))

    def getFloat(self, item):
        return float(self.get(item,0))

    def has(self, item, default=None):
        """Vérifie si une propriété est disponible sans la charger"""
        # Vérifier dans les données déjà chargées
        if self.get(item) is not None:
            return True
            
        # Si le contexte a été chargé, vérifier dans les paramètres
        if self._context_loaded and "parameters" in self._attributes:
            return item in self._attributes["parameters"]
            
        return False

    def getProgramName(self):
        try:
            name = self._attributes["commandHistory"]["command"]["programName"].lower()
            parts = name.split('.')
            if( len(parts) == 3 ):
                name = parts[2]
            return name
        except (KeyError, IndexError):
            return None

    async def load_context(self):
        """Charge le contexte de l'appareil si nécessaire"""
        if not self._context_loaded:
            data = await self._hon.async_get_context(self)
            self._attributes = data
            for name, values in self._attributes.pop("shadow", {'NA': 0}).get("parameters", {}).items():
                self._attributes.setdefault("parameters", {})[name] = values["parNewVal"]
            self._context_loaded = True

    @property
    def data(self):
        return {"attributes": self.attributes, "appliance": self.appliance, "statistics": self.statistics, **self.parameters}

    @property
    def appliance_type(self):
        return self._appliance.get("applianceTypeName")

    @property
    def mac_address(self):
        return self._appliance.get("macAddress")

    @property
    def model_name(self):
        return self._appliance.get("modelName")

    @property
    def name(self):
        return self._name

    @property
    def commands_options(self):
        return self._appliance_model.get("options")

    @property
    def commands(self):
        return self._commands
    
    @property
    def attributes(self):
        """Retourne les attributs et charge le contexte si nécessaire"""
        if not self._attributes and not self._context_loaded:
            # Ne pas charger automatiquement le contexte, juste retourner un dict vide
            return {"parameters": {}}
        return self._attributes

    @property
    def statistics(self):
        return self._statistics

    @property
    def appliance(self):
        return self._appliance

    @property
    def settings(self):
        result = {}
        for name, command in self._commands.items():
            for key, setting in command.settings.items():
                result[f"{name}.{key}"] = setting
        return result

    @property
    def parameters(self):
        result = {}
        for name, command in self._commands.items():
            for key, parameter in command.parameters.items():
                result.setdefault(name, {})[key] = parameter.value
        return result
        

    def update_command(self, command, parameters):
        for key in command.parameters.keys():
            if( key in parameters 
                and command.parameters.get(key).value != parameters.get(key) 
                and not isinstance(command.parameters.get(key), HonParameterFixed)):

                if( isinstance(command.parameters.get(key), HonParameterEnum) and parameters.get(key) not in command.parameters.get(key).values): 
                    _LOGGER.warning(f"Unable to update parameter [{key}] with value [{parameters.get(key)}] because not in range {command.parameters.get(key).values}. Use default instead.")
                else:
                    command.parameters.get(key).value = parameters.get(key)

    def settings_command(self, parameters = {}):
        """Retourne une commande pour mettre à jour les paramètres de l'appareil"""
        # Charger les commandes si nécessaire
        if not self._commands_loaded or "settings" not in self._commands:
            raise ValueError("No command to update settings of the device")
            
        command = self._commands.get("settings")
        self.update_command(command, self.attributes["parameters"])
        self.update_command(command, parameters)

        # Mise à jour pour la prochaine commande (au cas où aucun rafraîchissement n'a encore lieu)
        for key in command.parameters.keys():
            self.attributes["parameters"][key] = command.parameters.get(key).value

        return command

    def start_command(self, program = None, parameters = {}):
        """Prépare une commande pour démarrer un programme"""
        # Charger les commandes si nécessaire
        if not self._commands_loaded or "startProgram" not in self._commands:
            raise ValueError("No command to start the device")
            
        command = self._commands.get("startProgram")
        command.set_program(program)
        # Récupérer la nouvelle commande par défaut
        command = self._commands.get("startProgram")
        self.update_command(command, self.attributes["parameters"])
        self.update_command(command, parameters)
    
        # Mise à jour pour la prochaine commande (au cas où aucun rafraîchissement n'a encore lieu)
        for key in command.parameters.keys():
            self.attributes["parameters"][key] = command.parameters.get(key).value

        return command

    def stop_command(self, parameters = {}):
        """Prépare une commande pour arrêter un programme"""
        # Charger les commandes si nécessaire
        if not self._commands_loaded or "stopProgram" not in self._commands:
            raise ValueError("No command to stop the device")
            
        command = self._commands.get("stopProgram")
        self.update_command(command, self.attributes["parameters"])
        self.update_command(command, parameters)
        return command

    async def load_commands(self):
        """Charge les commandes de l'appareil"""
        if self._commands_loaded:
            return
            
        commands = await self._hon.load_commands(self._appliance)
    
        try:
            self._appliance_model = commands.pop("applianceModel")
        except:
            _LOGGER.error(f"Unable to load device commands. Please try to restart. Current value: [{commands}]")
            return

        for item in ["options", "dictionaryId"]:
            if item in commands:
                commands.pop(item)

        for command, attr in commands.items():
            if "parameters" in attr:
                self._commands[command] = HonCommand(command, attr, self._hon, self)
            if "setParameters" in attr and "parameters" in attr[list(attr)[0]]:
                self._commands[command] = HonCommand(command, attr.get("setParameters"), self._hon, self)
            elif "parameters" in attr[list(attr)[0]]:
                multi = {}
                for program, attr2 in attr.items():
                    program = program.split(".")[-1].lower()
                    cmd = HonCommand(command, attr2, self._hon, self, multi=multi, program=program)
                    multi[program] = cmd
                    self._commands[command] = cmd
                    
        self._commands_loaded = True
        _LOGGER.debug(f"Commands loaded for device {self._mac}")

    async def load_commands_if_needed(self):
        """Charge les commandes si nécessaire"""
        if not self._commands_loaded:
            await self.load_commands()

    async def load_statistics(self):
        """Charge les statistiques de l'appareil"""
        if not self._statistics_loaded:
            self._statistics = await self._hon.load_statistics(self)
            self._statistics_loaded = True
            _LOGGER.debug(f"Statistics loaded for device {self._mac}")

    async def load_statistics_if_needed(self):
        """Charge les statistiques si nécessaire"""
        if not self._statistics_loaded:
            await self.load_statistics()

    @property
    def device_info(self):
        return {
            "identifiers": {
                (DOMAIN, self._mac, self._type_name)
            },
            "name": self._name,
            "manufacturer": self._brand,
            "model": self._model,
            "sw_version": self._fw_version,
        }
