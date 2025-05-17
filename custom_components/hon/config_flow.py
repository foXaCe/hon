from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
import voluptuous as vol

from .hon import HonConnection
from .const import DOMAIN, CONF_ID_TOKEN, CONF_FRAMEWORK, CONF_COGNITO_TOKEN, CONF_REFRESH_TOKEN

class HonFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Gérer le flux de configuration pour l'intégration hOn."""
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    def __init__(self):
        """Initialiser."""
        self._email = None
        self._password = None

    async def async_step_user(self, user_input=None):
        """Gérer une étape initiée par l'utilisateur."""
        errors = {}

        if user_input is None:
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str
                })
            )

        self._email = user_input[CONF_EMAIL]
        self._password = user_input[CONF_PASSWORD]

        # Vérifier si déjà configuré
        await self.async_set_unique_id(self._email)
        self._abort_if_unique_id_configured()

        # Tester la connexion
        hon = HonConnection(None, None, self._email, self._password)
        if await hon.async_authorize() == False:
            errors["base"] = "auth_error"
            await hon.async_close()
            return self.async_show_form(
                step_id="user",
                data_schema=vol.Schema({
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str
                }),
                errors=errors
            )
        await hon.async_close()

        return self.async_create_entry(
            title=self._email,
            data={
                CONF_EMAIL: self._email,
                CONF_PASSWORD: self._password,
                CONF_ID_TOKEN: "",
                CONF_FRAMEWORK: "none",
                CONF_COGNITO_TOKEN: "",
                CONF_REFRESH_TOKEN: ""
            },
        )

    async def async_step_import(self, user_input=None):
        """Importer une entrée de configuration."""
        return await self.async_step_user(user_input)

    async def async_step_reconfigure(self, user_input=None):
        """Gérer la reconfiguration."""
        if user_input is not None:
            entry_id = self.context["entry_id"]
            config_entry = self.hass.config_entries.async_get_entry(entry_id)
            
            # Tester la connexion
            hon = HonConnection(None, None, config_entry.unique_id, user_input[CONF_PASSWORD])
            if await hon.async_authorize() == False:
                errors = {}
                errors["base"] = "auth_error"
                await hon.async_close()
                return self.async_show_form(
                    step_id="reconfigure",
                    data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}), 
                    errors=errors
                )
            await hon.async_close()

            await self.async_set_unique_id(config_entry.unique_id)

            return self.async_update_reload_and_abort(
                entry=config_entry,
                unique_id=config_entry.unique_id,
                data={
                    CONF_EMAIL: config_entry.unique_id,
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_ID_TOKEN: "",
                    CONF_FRAMEWORK: "none",
                    CONF_COGNITO_TOKEN: "",
                    CONF_REFRESH_TOKEN: ""
                },
                reason="reconfigure_successful"
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
        )
