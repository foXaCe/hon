"""
Suite du fichier: custom_components/hon/command.py
"""
                value for name, parameter in self._parameters.items()}
                return await self._connector.send_command(self._device, self._name, parameters, self.ancillary_parameters)
            except Exception as retry_err:
                _LOGGER.error(f"Failed retry for command {self._name} after reconnection: {retry_err}")
                return False

    def get_programs(self):
        return self._multi

    def set_program(self, program):
        self._multi[program]._multi = self._multi
        self._device.commands[self._name] = self._multi[program]
    
    def _get_settings_keys(self, command=None):
        command = command or self
        keys = []
        for key, parameter in command._parameters.items():
            if isinstance(parameter, HonParameterFixed):
                continue
            if key not in keys:
                keys.append(key)
        return keys

    @property
    def setting_keys(self):
        """Obtient les clés de paramètres avec mise en cache"""
        if self._settings_keys_cache is not None:
            return self._settings_keys_cache
            
        if not self._multi:
            self._settings_keys_cache = self._get_settings_keys()
            return self._settings_keys_cache
            
        result = [key for cmd in self._multi.values() for key in self._get_settings_keys(cmd)]
        self._settings_keys_cache = list(set(result + ["program"]))
        return self._settings_keys_cache

    @property
    def settings(self):
        """Parameters with typology enum and range"""
        return {s: self._parameters.get(s) for s in self.setting_keys if self._parameters.get(s) is not None}

    def dump(self):
        """Génère le texte et l'exemple pour l'affichage des commandes"""
        text = ""
        example = "{"
        for key, parameter in self._parameters.items():
            if isinstance(parameter, HonParameterFixed) or key == "program":
                continue
            text += f"""{parameter.dump()}
"""
            example += f"\'{key}\':{parameter.default},"
        example = example[:-1] + "}"
        return text, example
