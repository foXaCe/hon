import asyncio
import logging
import voluptuous as vol
import aiohttp
import asyncio
import secrets
import json
import re
import ast
import time
import urllib.parse
from urllib.parse import quote
from datetime import datetime, timezone, timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD

from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr


from .const import (
    DOMAIN,
    CONF_ID_TOKEN,
    CONF_FRAMEWORK,
    CONF_COGNITO_TOKEN,
    CONF_REFRESH_TOKEN,
    AUTH_API,
    API_URL,
    APP_VERSION,
    OS_VERSION,
    OS,
    DEVICE_MODEL,
    SESSION_TIMEOUT,
    SESSION_PROACTIVE_REFRESH,
    CONTEXT_CACHE_TIMEOUT,
    STATISTICS_CACHE_TIMEOUT,
)

from .base import HonBaseCoordinator


class HonConnection:
    def __init__(self, hass, entry, email = None, password = None) -> None:
        self._hass = hass
        self._entry = entry
        self._coordinator_dict = {}
        self._configured_devices = set()  # Pour suivre les appareils déjà configurés
        self._mobile_id = secrets.token_hex(8)
        self._auth_lock = asyncio.Lock()
        
        # Cache pour réduire les appels API
        self._cache = {}
        self._cache_timestamps = {}

        # Uniquement utilisé pendant l'enregistrement (vérification identifiant/mot de passe)
        if email is not None and password is not None:
            self._email = email
            self._password = password
            self._framework = "None"
        else:
            self._email = entry.data[CONF_EMAIL]
            self._password = entry.data[CONF_PASSWORD]
            self._framework = entry.data.get(CONF_FRAMEWORK, "")
            self._id_token = entry.data.get(CONF_ID_TOKEN, "")
            self._refresh_token = entry.data.get(CONF_REFRESH_TOKEN, "")
            self._cognitoToken = entry.data.get(CONF_COGNITO_TOKEN, "")

        self._frontdoor_url = ""
        self._session_start_time = 0
        self._appliances_loaded = False

        self._header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"
        }
        self._session = aiohttp.ClientSession(headers=self._header, connector=aiohttp.TCPConnector(ssl=False))
        self._appliances = []

    @property
    def configured_devices(self):
        """Retourne la liste des appareils déjà configurés"""
        return self._configured_devices

    async def async_close(self):
        await self._session.close()

    @property
    def appliances(self):
        return self._appliances

    def _is_session_valid(self):
        """Vérifie si la session actuelle est valide avec une marge de sécurité"""
        if not self._session_start_time:
            return False
        return (time.time() - self._session_start_time) < (SESSION_TIMEOUT - SESSION_PROACTIVE_REFRESH)

    async def load_appliances_if_needed(self):
        """Charge les appareils si ce n'est pas déjà fait"""
        if self._appliances_loaded:
            return
            
        if not self._is_session_valid():
            await self.async_authorize()
            
        # Si les appareils ne sont pas encore chargés, les récupérer
        if not self._appliances:
            await self._load_appliances()
            
        self._appliances_loaded = True

    async def _load_appliances(self):
        """Charge la liste des appareils depuis l'API"""
        url = f"{API_URL}/commands/v1/appliance"
        async with self._session.get(url, headers=self._headers) as resp:
            try:
                json_data = await resp.json()
            except:
                _LOGGER.error(f"hOn Invalid Data [cannot parse JSON] after GET [" + url + "]")
                return False

            self._appliances = json_data["payload"]["appliances"]
            _LOGGER.debug(f"All appliances (count: {len(self._appliances)})")

            # Supprimer les appareils sans mac
            self._appliances = [appliance for appliance in self._appliances if "macAddress" in appliance]

            # Supprimer les appareils sans applianceTypeId
            self._appliances = [appliance for appliance in self._appliances if "applianceTypeId" in appliance]
            
            _LOGGER.debug(f"Valid appliances (count: {len(self._appliances)})")
            return True

    async def async_get_existing_coordinator(self, mac):
        """Récupère un coordinateur existant s'il existe"""
        if mac in self._coordinator_dict:
            return self._coordinator_dict[mac]
        return None
        
    async def async_get_coordinator(self, appliance):
        """Récupère ou crée un coordinateur pour un appareil"""
        mac = appliance.get("macAddress", "")
        if mac in self._coordinator_dict:
            return self._coordinator_dict[mac]
        coordinator = HonBaseCoordinator(self._hass, self, appliance)
        self._coordinator_dict[mac] = coordinator
        return coordinator


    async def async_get_frontdoor_url(self, error_code=0):
        """Obtient l'URL de frontdoor pour l'authentification"""
        data = (
            "message=%7B%22actions%22%3A%5B%7B%22id%22%3A%2279%3Ba%22%2C%22descriptor%22%3A%22apex%3A%2F%2FLightningLoginCustomController%2FACTION%24login%22%2C%22callingDescriptor%22%3A%22markup%3A%2F%2Fc%3AloginForm%22%2C%22params%22%3A%7B%22username%22%3A%22"
            + urllib.parse.quote(self._email)
            + "%22%2C%22password%22%3A%22"
            + urllib.parse.quote(self._password)
            + "%22%2C%22startUrl%22%3A%22%22%7D%7D%5D%7D&aura.context=%7B%22mode%22%3A%22PROD%22%2C%22fwuid%22%3A%22"
            + urllib.parse.quote(self._framework)
            + "%22%2C%22app%22%3A%22siteforce%3AloginApp2%22%2C%22loaded%22%3A%7B%22APPLICATION%40markup%3A%2F%2Fsiteforce%3AloginApp2%22%3A%22YtNc5oyHTOvavSB9Q4rtag%22%7D%2C%22dn%22%3A%5B%5D%2C%22globals%22%3A%7B%7D%2C%22uad%22%3Afalse%7D&aura.pageURI=%2FSmartHome%2Fs%2Flogin%2F%3Flanguage%3Dfr&aura.token=null"
        )

        async with self._session.post(
            f"{AUTH_API}/s/sfsites/aura?r=3&other.LightningLoginCustom.login=1",
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
            data=data
        ) as resp:
            if resp.status != 200:
                _LOGGER.error("Unable to connect to the login service: " + str(resp.status))
                return False

            text = await resp.text()
            try:
                json_data = json.loads(text)
                self._frontdoor_url = json_data["events"][0]["attributes"]["values"]["url"]
            except:
                # Le framework doit être mis à jour
                if text.find("clientOutOfSync") > 0 and error_code != 2:
                    start = text.find("Expected: ") + 10
                    end = text.find(" ", start)
                    _LOGGER.debug("Framework update from ["+ self._framework+ "] to ["+ text[start:end]+ "]")
                    self._framework = text[start:end]
                    return await self.async_get_frontdoor_url(2)
                _LOGGER.error("Unable to retreive the frontdoor URL. Message: " + text)
                return 1

        if error_code == 2 and self._entry != None:
            # Mise à jour du framework
            data = {**self._entry.data}
            data[CONF_FRAMEWORK] = self._framework
            self._hass.config_entries.async_update_entry(self._entry, data=data)

        return 0

    async def async_authorize(self):
        """Authentifie auprès de l'API hOn"""
        async with self._auth_lock:
            # Vérifier si la session est encore valide après avoir acquis le verrou
            if self._is_session_valid():
                return True
                
            _LOGGER.debug("Authenticating with hOn API")
            if await self.async_get_frontdoor_url(0) == 1:
                return False

            async with self._session.get(self._frontdoor_url) as resp:
                if resp.status != 200:
                    _LOGGER.error("Unable to connect to the login service: " + str(resp.status))
                    return False
                await resp.text()

            url = f"{AUTH_API}/apex/ProgressiveLogin?retURL=%2FSmartHome%2Fapex%2FCustomCommunitiesLanding"
            async with self._session.get(url) as resp:
                await resp.text()
                
            url = f"{AUTH_API}/services/oauth2/authorize?response_type=token+id_token&client_id=3MVG9QDx8IX8nP5T2Ha8ofvlmjLZl5L_gvfbT9.HJvpHGKoAS_dcMN8LYpTSYeVFCraUnV.2Ag1Ki7m4znVO6&redirect_uri=hon%3A%2F%2Fmobilesdk%2Fdetect%2Foauth%2Fdone&display=touch&scope=api%20openid%20refresh_token%20web&nonce=82e9f4d1-140e-4872-9fad-15e25fbf2b7c"
            async with self._session.get(url) as resp:
                text = await resp.text()
                array = []
                try:
                    array = text.split("'", 2)

                    if( len(array) == 1 ):
                        #Implementation d'une seconde méthode pour obtenir la valeur du token
                        m = re.search('id_token\\=(.+?)&', text)
                        if m:
                            self._id_token = m.group(1)
                        else:
                            _LOGGER.error("Unable to get [id_token] during authorization process (tried both options). Full response [" + text + "]")
                            return False
                    else:
                        params = urllib.parse.parse_qs(array[1])
                        self._id_token = params["id_token"][0]
                except:
                    if "ChangePassword" not in text:
                        _LOGGER.error("Unable to get [id_token] during authorization process. Full response [" + text + "]")
                    else:
                        _LOGGER.error("Unable to get connect. You need to change your password on the hOn app")
                    return False

            post_headers = {"id-token": self._id_token}
            data = {"appVersion": APP_VERSION,
                    "mobileId": self._mobile_id,
                    "os": OS,
                    "osVersion": OS_VERSION,
                    "deviceModel": DEVICE_MODEL}

            async with self._session.post(f"{API_URL}/auth/v1/login", headers=post_headers, json=data) as resp:
                try:
                    json_data = await resp.json()
                    self._cognitoToken = json_data["cognitoUser"]["Token"]
                except:
                    text = await resp.text()
                    _LOGGER.error("hOn Invalid Data [cannot parse JSON] after sending command ["+ str(data)+ "] with headers [" + str(post_headers) + "]. Response: " + text)
                    return False

            # Mettre à jour l'horodatage de démarrage de la session
            self._session_start_time = time.time()
            _LOGGER.debug(f"Authentication successful, session valid until {datetime.fromtimestamp(self._session_start_time + SESSION_TIMEOUT)}")
            
            # La connexion a réussi, mais nous n'avons pas encore chargé les appareils
            # pour accélérer le démarrage
            self._appliances_loaded = False
            return True

    async def load_commands(self, appliance):
        """Charge les commandes disponibles pour un appareil"""
        # Vérifier le cache d'abord
        cache_key = f"commands_{appliance['macAddress']}"
        if cache_key in self._cache and time.time() - self._cache_timestamps.get(cache_key, 0) < CONTEXT_CACHE_TIMEOUT:
            return self._cache[cache_key]
            
        # Vérifier si la session est encore valide
        if not self._is_session_valid():
            await self.async_authorize()
            
        params = {
            "applianceType": appliance["applianceTypeId"],
            "code": appliance["code"],
            "applianceModelId": appliance["applianceModelId"],
            "firmwareId": appliance["eepromId"],
            "macAddress": appliance["macAddress"],
            "fwVersion": appliance["fwVersion"],
            "os": OS,
            "appVersion": APP_VERSION,
            "series": appliance["series"],
        }
        url = f"{API_URL}/commands/v1/retrieve"
        async with self._session.get(url, params=params, headers=self._headers) as resp:
            result = (await resp.json()).get("payload", {})
            if not result or result.pop("resultCode") != "0":
                return {}
                
            # Mise en cache du résultat
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = time.time()
            
            _LOGGER.debug(f"Commands loaded for device {appliance['macAddress']}")
            return result

    async def async_get_context(self, device):
        """Récupère le contexte d'un appareil avec mise en cache"""
        # Vérifier le cache d'abord
        cache_key = f"context_{device.mac_address}"
        if cache_key in self._cache and time.time() - self._cache_timestamps.get(cache_key, 0) < CONTEXT_CACHE_TIMEOUT:
            return self._cache[cache_key]

        # Créer une nouvelle session hOn pour éviter d'atteindre l'expiration
        if not self._is_session_valid():
            await self.async_authorize()

        params = {
            "macAddress": device.mac_address,
            "applianceType": device.appliance_type,
            "category": "CYCLE"
        }
        url = f"{API_URL}/commands/v1/context"
        async with self._session.get(url, params=params, headers=self._headers) as response:
            data = await response.json()
            result = data.get("payload", {})
            
            # Mise en cache du résultat
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = time.time()
            
            return result

    async def load_statistics(self, device):
        """Charge les statistiques d'un appareil avec mise en cache"""
        # Vérifier le cache d'abord
        cache_key = f"statistics_{device.mac_address}"
        if cache_key in self._cache and time.time() - self._cache_timestamps.get(cache_key, 0) < STATISTICS_CACHE_TIMEOUT:
            return self._cache[cache_key]
        
        # Vérifier si la session est encore valide
        if not self._is_session_valid():
            await self.async_authorize()
            
        params = {
            "macAddress": device.mac_address,
            "applianceType": device.appliance_type
        }
        url = f"{API_URL}/commands/v1/statistics"
        async with self._session.get(url, params=params, headers=self._headers) as response:
            data = await response.json()
            result = data.get("payload", {})
            
            # Mise en cache du résultat
            self._cache[cache_key] = result
            self._cache_timestamps[cache_key] = time.time()
            
            return result

    async def async_get_state(self, mac, appliance_type):
        """Récupère l'état actuel d'un appareil"""
        # Vérifier si la session est encore valide
        if not self._is_session_valid():
            await self.async_authorize()
            
        params = {
            "macAddress": mac,
            "applianceType": appliance_type,
        }
        url = f"{API_URL}/commands/v1/appliance/status"
        async with self._session.get(url, params=params, headers=self._headers) as response:
            data = await response.json()
            return data.get("payload", {"category": "DISCONNECTED"})

    @property
    def _headers(self):
        return {
            "Content-Type": "application/json",
            "cognito-token": self._cognitoToken,
            "id-token": self._id_token,
        }

    async def async_set(self, mac, typeName, parameters):
        """Envoie une commande à un appareil"""
        # Vérifier si la session est encore valide
        if not self._is_session_valid():
            await self.async_authorize()

        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        command = json.loads("{}")
        command["macAddress"] = mac
        command["commandName"] = "startProgram"
        command["applianceOptions"] = json.loads("{}")
        command["programName"] = "PROGRAMS." + typeName + ".HOME_ASSISTANT"
        command["ancillaryParameters"] = json.loads(
            '{"programFamily":"[standard]", "remoteActionable": "1", "remoteVisible": "1"}'
        )
        command["applianceType"] = typeName
        command["attributes"] = json.loads(
            '{"prStr":"HOME_ASSISTANT", "channel":"googleHome", "origin": "conversationalVoice"}'
        )
        if typeName == "WM":
            command["attributes"] = json.loads(
            '{"prStr":"HOME_ASSISTANT", "channel":"googleHome", "origin": "conversationalVoice", "energyLabel": "0"}'
        )
        command["device"] = json.loads(
            '{"mobileId":"xxxxxxxxxxxxxxxxxxx", "mobileOs": "android", "osVersion": "31", "appVersion": "1.53.4", "deviceModel": "lito"}'
        )
        command["parameters"] = parameters
        command["timestamp"] = timestamp
        command["transactionId"] = mac + "_" + command["timestamp"]
        _LOGGER.debug((f"Command sent (async_set): {command}"))

        async with self._session.post(f"{API_URL}/commands/v1/send",headers=self._headers,json=command,) as resp:
            try:
                data = await resp.json()
                _LOGGER.debug((f"Command result (async_set): {data}"))
            except json.JSONDecodeError:
                _LOGGER.error("hOn Invalid Data [cannot parse JSON] after sending command ["+ str(command)+ "]")
                return False
            if data["payload"]["resultCode"] == "0":
                # Invalider le cache pour forcer un rechargement
                self._invalidate_device_cache(mac)
                return True
            _LOGGER.error("hOn command has been rejected. Error message ["+ str(data) + "] sent command ["+ str(command)+ "]")
        return False
        
    def _invalidate_device_cache(self, mac):
        """Invalide le cache pour un appareil spécifique"""
        for key in list(self._cache.keys()):
            if mac in key:
                del self._cache[key]
                if key in self._cache_timestamps:
                    del self._cache_timestamps[key]


    async def send_command(self, device, command, parameters, ancillary_parameters):
        """Envoie une commande à un appareil"""
        # Vérifier si la session est encore valide
        if not self._is_session_valid():
            await self.async_authorize()
            
        now = datetime.utcnow().isoformat()
        command_data = {
            "macAddress": device.mac_address,
            "timestamp": f"{now[:-3]}Z",
            "commandName": command,
            "transactionId": f"{device.mac_address}_{now[:-3]}Z",
            "applianceOptions": device.commands_options,
            "device": {
                "mobileId": self._mobile_id,
                "mobileOs": OS,
                "osVersion": OS_VERSION,
                "appVersion": APP_VERSION,
                "deviceModel": DEVICE_MODEL
            },
            "attributes": {
                "channel": "mobileApp",
                "origin": "standardProgram",
                "energyLabel": "0"
            },
            "ancillaryParameters": ancillary_parameters,
            "parameters": parameters,
            "applianceType": device.appliance_type
        }
        _LOGGER.debug((f"Command sent (send_command): {command_data}"))

        url = f"{API_URL}/commands/v1/send"
        try:
            async with self._session.post(url, headers=self._headers, json=command_data) as resp:
                try:
                    data = await resp.json()
                    _LOGGER.debug((f"Command result (send_command): {data}"))
                except json.JSONDecodeError:
                    _LOGGER.error("hOn Invalid Data [cannot parse JSON] after sending command ["+ str(command_data)+ "]")
                    return False
                if data["payload"]["resultCode"] == "0":
                    # Invalider le cache pour forcer un rechargement
                    self._invalidate_device_cache(device.mac_address)
                    return True
                _LOGGER.error("hOn command has been rejected. Error message ["+ str(data) + "] sent data ["+ str(command_data)+ "]")
        except aiohttp.ClientError as e:
            _LOGGER.error(f"Network error while sending command: {e}")
            # Réessayer une fois après réauthentification
            await self.async_authorize()
            try:
                async with self._session.post(url, headers=self._headers, json=command_data) as resp:
                    data = await resp.json()
                    if data["payload"]["resultCode"] == "0":
                        self._invalidate_device_cache(device.mac_address)
                        return True
                    _LOGGER.error(f"Retry failed: {data}")
            except Exception as retry_err:
                _LOGGER.error(f"Retry failed: {retry_err}")
        except Exception as e:
            _LOGGER.error(f"Unexpected error: {e}")
            
        return False

    def get_device(self, hass, device_id):
        """Récupère un appareil à partir de son ID"""
        mac = get_hOn_mac(device_id, hass)
        if mac in self._coordinator_dict:
            return self._coordinator_dict[mac].device
        _LOGGER.error(f"Unable to find the device with ID: {device_id} and mac: {mac}")
        return None

def get_hOn_mac(device_id, hass):
    """Récupère l'adresse MAC d'un appareil à partir de son ID"""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    return next(iter(device.identifiers))[1]
