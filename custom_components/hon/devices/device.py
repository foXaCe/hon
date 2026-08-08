"""Device model wrapping appliance data and commands."""

from __future__ import annotations

import logging

from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
)

from ..command import HonCommand
from ..const import APPLIANCE_DEFAULT_NAME, DOMAIN
from ..parameter import HonParameterFixed

_LOGGER = logging.getLogger(__name__)


class HonDevice(CoordinatorEntity):
    """Model of a connected appliance: data, attributes, statistics and commands."""

    def __init__(self, hon, coordinator, appliance) -> None:
        """Initialize the device from the appliance payload."""
        super().__init__(coordinator)

        self._hon = hon
        self._coordinator = coordinator
        self._appliance = appliance
        self._brand = appliance["brand"]
        self._type_name = appliance["applianceTypeName"]
        self._type_id = appliance["applianceTypeId"]
        self._name = appliance.get(
            "nickName",
            APPLIANCE_DEFAULT_NAME.get(
                str(self._type_id), "Device ID: " + str(self._type_id)
            ),
        )
        self._mac = appliance["macAddress"]
        self._model = appliance["modelName"]
        self._series = appliance.get("series", "")
        self._model_id = appliance["applianceModelId"]
        self._serial_number = appliance["serialNumber"]
        self._fw_version = appliance["fwVersion"]

        self._commands = {}
        self._appliance_model = {}
        self._attributes = {}
        self._statistics = {}

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
        """Store a value in the device data."""
        if item in self.data:
            self.data[item] = value
        elif item in self.attributes["parameters"]:
            self.attributes["parameters"][item] = value
        else:
            self.appliance[item] = value

    def get(self, item, default=None):
        """Return a device value, or the default when missing."""
        try:
            return self[item]
        except (KeyError, IndexError):
            return default

    def getInt(self, item):
        """Return a device value as an int."""
        return int(self.get(item, 0))

    def getFloat(self, item):
        """Return a device value as a float."""
        return float(self.get(item, 0))

    def has(self, item, default=None):
        """Return whether a device value is present."""
        return self.get(item) != None

    def getProgramName(self):
        """Return the current program name, if any."""
        try:
            # Önce activity.attributes içinde ara
            activity = self._attributes.get("activity", {})
            if activity:
                program_name = activity.get("attributes", {}).get("programName")
                if program_name:
                    _LOGGER.debug(
                        "[%s] Found program name in activity.attributes: %s",
                        self._name,
                        program_name,
                    )
                    name = program_name.lower()
                    parts = name.split(".")
                    if len(parts) == 3:
                        return parts[2]
                    return name

            # Sonra direkt attributes içinde ara
            program_name = self._attributes.get("programName")
            if program_name:
                _LOGGER.debug(
                    "[%s] Found program name in attributes: %s",
                    self._name,
                    program_name,
                )
                name = program_name.lower()
                parts = name.split(".")
                if len(parts) == 3:
                    return parts[2]
                return name

            # Sonra commandHistory içinde ara
            command_history = self._attributes.get("commandHistory", {})
            if command_history:
                command = command_history.get("command", {})
                program_name = command.get("programName")
                if program_name:
                    _LOGGER.debug(
                        "[%s] Found program name in commandHistory: %s",
                        self._name,
                        program_name,
                    )
                    name = program_name.lower()
                    parts = name.split(".")
                    if len(parts) == 3:
                        return parts[2]
                    return name

            _LOGGER.debug("[%s] Program name not found in any location", self._name)

        except Exception as e:
            _LOGGER.warning("[%s] Failed to get program name: %s", self._name, e)

        return None

    async def load_context(self):
        """Fetch the latest device context from the cloud."""
        data = await self._hon.async_get_context(self)
        self._attributes = data or {}

        shadow = self._attributes.pop("shadow", None)
        if not shadow:
            _LOGGER.warning(
                "Unable to get device context: no shadow data in: %s", self._attributes
            )
            return

        parameters = shadow.get("parameters")
        if not parameters:
            _LOGGER.warning(
                "Unable to get device context: no parameters in shadow data. %s",
                self._attributes,
            )
            return

        for name, values in parameters.items():
            self._attributes.setdefault("parameters", {})[name] = values.get(
                "parNewVal"
            )

    @property
    def data(self):
        """Return the combined device data."""
        return {
            "attributes": self.attributes,
            "appliance": self.appliance,
            "statistics": self.statistics,
            **self.parameters,
        }

    @property
    def appliance_type(self):
        """Return the appliance type name."""
        return self._appliance.get("applianceTypeName")

    @property
    def mac_address(self):
        """Return the device MAC address."""
        return self._appliance.get("macAddress")

    @property
    def model_name(self):
        """Return the device model name."""
        return self._appliance.get("modelName")

    @property
    def name(self):
        """Return the device display name."""
        return self._name

    @property
    def commands_options(self):
        """Return the command options from the appliance model."""
        return self._appliance_model.get("options")

    @property
    def commands(self):
        """Return the loaded commands."""
        return self._commands

    @property
    def attributes(self):
        """Return the device attributes."""
        return self._attributes

    @property
    def statistics(self):
        """Return the device statistics."""
        return self._statistics

    @property
    def appliance(self):
        """Return the raw appliance payload."""
        return self._appliance

    @property
    def settings(self):
        """Return all command settings."""
        result = {}
        for name, command in self._commands.items():
            for key, setting in command.settings.items():
                result[f"{name}.{key}"] = setting
        return result

    @property
    def parameters(self):
        """Return the current parameter values per command."""
        result = {}
        for name, command in self._commands.items():
            for key, parameter in command.parameters.items():
                result.setdefault(name, {})[key] = parameter.value
        return result

    def update_command(self, command, parameters):
        """Apply new values to a command's parameters."""
        for key in command.parameters.keys():
            param = command.parameters.get(key)

            if key not in parameters or isinstance(param, HonParameterFixed):
                continue

            new_val = parameters.get(key)
            if param.value == new_val:
                continue

            try:
                param.value = new_val

            except Exception as e:
                _LOGGER.warning("Update_command: Invalid %s=%s (%s)", key, new_val, e)

                # 👉 fallback intelligent
                if hasattr(param, "default"):
                    try:
                        param.value = param.default
                        _LOGGER.warning(
                            "Update_command: Use Fallback %s -> default %s",
                            key,
                            param.default,
                        )
                    except Exception:
                        pass

    def settings_command(self, parameters={}):
        """Prepare the settings command with the given parameters."""
        if "settings" not in self._commands:
            raise ValueError("No command to update settings of the device")
        command = self._commands.get("settings")
        self.update_command(command, self.attributes.get("parameters", {}))
        self.update_command(command, parameters)

        # Update for next command (in case no refresh happens yet)
        for key in command.parameters.keys():
            self.attributes.setdefault("parameters", {})[key] = command.parameters.get(
                key
            ).value

        return command

    def start_command(self, program=None, parameters={}):
        """Prepare the start program command with the given parameters."""
        if "startProgram" not in self._commands:
            raise ValueError("No command to start the device")
        command = self._commands.get("startProgram")
        if program is not None:
            command.set_program(program)
        # Return the new default command
        command = self._commands.get("startProgram")
        self.update_command(command, self.attributes.get("parameters", {}))
        self.update_command(command, parameters)

        # Update for next command (in case no refresh happens yet)
        for key in command.parameters.keys():
            self.attributes.setdefault("parameters", {})[key] = command.parameters.get(
                key
            ).value

        return command

    def get_setting(self, setting_key):
        """Return a setting parameter for a dotted key."""
        command_name, parameter_key = setting_key.split(".", 1)
        command = self._commands.get(command_name)
        if command is None:
            return None
        return command.settings.get(parameter_key)

    def has_current_setting(self, setting_key):
        """Return whether a dotted key maps to a parameter."""
        command_name, parameter_key = setting_key.split(".", 1)
        command = self._commands.get(command_name)
        if command is None:
            return False
        return parameter_key in command.parameters

    def stop_command(self, parameters={}):
        """Prepare the stop program command with the given parameters."""
        if "stopProgram" in self._commands:
            command = self._commands.get("stopProgram")
            self.update_command(command, self.attributes["parameters"])
            self.update_command(command, parameters)
            return command
        raise ValueError("No command to stop the device")

    async def load_commands(self):
        """Load the command catalogue from the cloud."""
        commands = await self._hon.load_commands(self._appliance)

        try:
            self._appliance_model = commands.pop("applianceModel")
        except:
            _LOGGER.error(
                f"Unable to load device commands. Please try to restart. Current value: [{commands}]"
            )
            return

        for item in ["options", "dictionaryId"]:
            commands.pop(item)

        for command, attr in commands.items():
            if "parameters" in attr:
                self._commands[command] = HonCommand(command, attr, self._hon, self)
            if "setParameters" in attr and "parameters" in attr[list(attr)[0]]:
                self._commands[command] = HonCommand(
                    command, attr.get("setParameters"), self._hon, self
                )
            elif "parameters" in attr[list(attr)[0]]:
                multi = {}
                for program, attr2 in attr.items():
                    program = program.split(".")[-1].lower()
                    cmd = HonCommand(
                        command, attr2, self._hon, self, multi=multi, program=program
                    )
                    multi[program] = cmd
                    self._commands[command] = cmd

    async def load_statistics(self):
        """Load the lifetime statistics from the cloud."""
        self._statistics = await self._hon.load_statistics(self)

    @property
    def device_info(self):
        """Return the device registry info."""
        return {
            "identifiers": {(DOMAIN, self._mac, self._type_name)},
            "name": self._name,
            "manufacturer": self._brand,
            "model": self._model,
            "sw_version": self._fw_version,
        }
