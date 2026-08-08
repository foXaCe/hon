import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import (
    CONN_CLASS_LOCAL_POLL,
    ConfigFlowResult,
)
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers import selector

from .const import (
    CONF_COGNITO_TOKEN,
    CONF_FRAMEWORK,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_UPDATE_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .exceptions import HonAuthenticationError, HonConnectionError
from .hon import HonConnection

_LOGGER = logging.getLogger(__name__)


class HonFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = CONN_CLASS_LOCAL_POLL

    def __init__(self):
        self._email = None
        self._password = None

    @staticmethod
    async def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return HonOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow initiated by the user."""
        errors = {}

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_EMAIL): selector.TextSelector(
                            selector.TextSelectorConfig(
                                type=selector.TextSelectorType.EMAIL
                            )
                        ),
                        vol.Required(CONF_PASSWORD): selector.TextSelector(
                            selector.TextSelectorConfig(
                                type=selector.TextSelectorType.PASSWORD
                            )
                        ),
                    }
                ),
            )

        self._email = user_input[CONF_EMAIL]
        self._password = user_input[CONF_PASSWORD]

        # Check if already configured
        await self.async_set_unique_id(self._email)
        self._abort_if_unique_id_configured()

        # Test connection
        hon = HonConnection(None, None, self._email, self._password)
        try:
            auth_ok = await hon.async_authorize()
        except (HonConnectionError, aiohttp.ClientConnectorError):
            errors["base"] = "cannot_connect"
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_EMAIL): str,
                        vol.Required(CONF_PASSWORD): str,
                    }
                ),
                errors=errors,
            )
        except HonAuthenticationError:
            errors["base"] = "invalid_auth"
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_EMAIL): str,
                        vol.Required(CONF_PASSWORD): str,
                    }
                ),
                errors=errors,
            )
        await hon.async_close()
        if not auth_ok:
            errors["base"] = "invalid_auth"
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema(
                    {
                        vol.Required(CONF_EMAIL): str,
                        vol.Required(CONF_PASSWORD): str,
                    }
                ),
                errors=errors,
            )

        return self.async_create_entry(
            title=self._email,
            data={
                CONF_EMAIL: self._email,
                CONF_PASSWORD: self._password,
                CONF_ID_TOKEN: "",
                CONF_FRAMEWORK: "none",
                CONF_COGNITO_TOKEN: "",
                CONF_REFRESH_TOKEN: "",
            },
        )

    async def async_step_import(self, user_input=None):
        """Import a config entry."""
        return await self.async_step_user(user_input)

    async def async_step_reauth(self, user_input: dict[str, Any] | None = None):
        """Handle the reauth flow."""
        errors = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            hon = HonConnection(None, None, entry.unique_id, user_input[CONF_PASSWORD])
            try:
                auth_ok = await hon.async_authorize()
            except (HonConnectionError, aiohttp.ClientConnectorError):
                errors["base"] = "cannot_connect"
                return self.async_show_form(
                    step_id="reauth",
                    data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
                    errors=errors,
                )
            except HonAuthenticationError:
                errors["base"] = "invalid_auth"
                return self.async_show_form(
                    step_id="reauth",
                    data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
                    errors=errors,
                )
            await hon.async_close()
            if not auth_ok:
                errors["base"] = "invalid_auth"
                return self.async_show_form(
                    step_id="reauth",
                    data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
                    errors=errors,
                )

            self.hass.config_entries.async_update_entry(
                entry,
                data={
                    **entry.data,
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_ID_TOKEN: "",
                    CONF_COGNITO_TOKEN: "",
                    CONF_REFRESH_TOKEN: "",
                },
            )
            await self.hass.config_entries.async_reload(entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the reconfiguration flow."""
        if user_input is not None:
            entry_id = self.context["entry_id"]
            config_entry = self.hass.config_entries.async_get_entry(entry_id)

            # Test connection
            hon = HonConnection(
                None, None, config_entry.unique_id, user_input[CONF_PASSWORD]
            )
            try:
                auth_ok = await hon.async_authorize()
            except (HonConnectionError, aiohttp.ClientConnectorError):
                errors = {}
                errors["base"] = "cannot_connect"
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
                    errors=errors,
                )
            except HonAuthenticationError:
                errors = {}
                errors["base"] = "invalid_auth"
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
                    errors=errors,
                )
            await hon.async_close()
            if not auth_ok:
                errors = {}
                errors["base"] = "invalid_auth"
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
                    errors=errors,
                )

            await self.async_set_unique_id(config_entry.unique_id)
            return self.async_update_reload_and_abort(
                entry=config_entry,
                unique_id=config_entry.unique_id,
                data={
                    **config_entry.data,
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_ID_TOKEN: "",
                    CONF_COGNITO_TOKEN: "",
                    CONF_REFRESH_TOKEN: "",
                },
                reason="reconfigure_successful",
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
        )


class HonOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle hOn options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the hOn options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_UPDATE_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_UPDATE_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=30,
                            max=3600,
                            step=30,
                            unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                }
            ),
        )
