"""hOn cloud API client.

Wraps the hOn CIAM (PKCE) authentication flow and the unified-api /
commands endpoints. Uses a shared aiohttp session, a bounded timeout and
exponential backoff on transient errors. Tokens are refreshed before they
expire; authentication failures raise :class:`HonAuthenticationError`.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import aiohttp
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from ..const import (
    API_URL,
    APP_VERSION,
    CONF_COGNITO_TOKEN,
    CONF_ID_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_UPDATE_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEVICE_MODEL,
    OS,
    OS_VERSION,
)
from ..coordinator import HonBaseCoordinator
from .exceptions import HonAuthenticationError, HonConnectionError, HonRateLimitError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# CIAM access tokens expire after ~15 minutes, so refresh well before that.
SESSION_TIMEOUT = 600  # seconds
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
MAX_RETRIES = 3


class HonConnection:
    """Connection to the hOn cloud API for one config entry."""

    def __init__(
        self,
        hass: HomeAssistant | None,
        entry: Any | None,
        email: str | None = None,
        password: str | None = None,
    ) -> None:
        """Initialize the connection.

        During the config flow ``hass`` and ``entry`` may be ``None`` and the
        credentials passed explicitly for a one-shot login check.
        """
        self._hass = hass
        self._entry = entry
        self._coordinator_dict: dict[str, HonBaseCoordinator] = {}
        self._mobile_id = secrets.token_hex(8)
        self._session: aiohttp.ClientSession | None = None

        if email is not None and password is not None:
            self._email = email
            self._password = password
        else:
            self._email = entry.data[CONF_EMAIL]
            self._password = entry.data[CONF_PASSWORD]
            self._id_token = entry.data.get(CONF_ID_TOKEN, "")
            self._refresh_token = entry.data.get(CONF_REFRESH_TOKEN, "")
            self._cognito_token = entry.data.get(CONF_COGNITO_TOKEN, "")

        self._start_time = time.time()
        self._appliances: list[dict[str, Any]] = []
        self._authorizing = False

    @property
    def _session_provider(self) -> aiohttp.ClientSession:
        """Return a shared (or private) aiohttp session."""
        if self._session is not None:
            return self._session
        if self._hass is not None:
            return async_get_clientsession(self._hass)
        self._session = aiohttp.ClientSession()
        return self._session

    async def async_close(self) -> None:
        """Close the private session if one was created."""
        if self._session is not None:
            await self._session.close()
            self._session = None

    @property
    def appliances(self) -> list[dict[str, Any]]:
        """Return the appliances owned by the account."""
        return self._appliances

    async def async_get_existing_coordinator(
        self, mac: str
    ) -> HonBaseCoordinator | None:
        """Return the coordinator for a MAC address, if any."""
        return self._coordinator_dict.get(mac)

    async def async_get_coordinator(self, appliance) -> HonBaseCoordinator:
        """Return (creating if needed) the coordinator for an appliance."""
        mac = appliance.get("macAddress", "")
        if mac in self._coordinator_dict:
            return self._coordinator_dict[mac]
        update_interval = self._entry.options.get(
            CONF_UPDATE_INTERVAL, DEFAULT_SCAN_INTERVAL
        )
        coordinator = HonBaseCoordinator(
            self._hass,
            self,
            appliance,
            update_interval=timedelta(seconds=int(update_interval)),
        )
        self._coordinator_dict[mac] = coordinator
        return coordinator

    @property
    def _headers(self) -> dict[str, str]:
        """Return the authenticated request headers."""
        return {
            "Content-Type": "application/json",
            "cognito-token": self._cognito_token,
            "id-token": self._id_token,
        }

    async def _ensure_session(self) -> None:
        """Re-authenticate when the CIAM tokens are close to expiring."""
        if time.time() - self._start_time > SESSION_TIMEOUT:
            await self.async_authorize()

    async def _async_request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        headers: dict[str, str] | None = None,
        retries: int = MAX_RETRIES,
    ) -> dict[str, Any]:
        """Perform a request with timeout, backoff and token refresh.

        Returns the JSON body of a successful (2xx) response.
        """
        session = self._session_provider
        attempt = 0
        while True:
            attempt += 1
            try:
                async with session.request(
                    method,
                    url,
                    params=params,
                    json=json,
                    headers=headers,
                    timeout=REQUEST_TIMEOUT,
                ) as response:
                    if response.status in RETRYABLE_STATUS and attempt <= retries:
                        await asyncio.sleep(min(2 ** (attempt - 1), 8))
                        continue
                    if response.status == 401:
                        if self._authorizing:
                            raise HonAuthenticationError("Authentication failed")
                        await self.async_authorize()
                        if attempt > retries:
                            raise HonAuthenticationError("Authentication failed")
                        continue
                    if response.status == 429:
                        raise HonRateLimitError("hOn API rate limit reached")
                    if response.status >= 400:
                        raise HonConnectionError(f"hOn API returned {response.status}")
                    return await response.json()
            except (aiohttp.ClientError, TimeoutError) as err:
                if attempt > retries:
                    raise HonConnectionError(f"Request failed: {err}") from err
                await asyncio.sleep(min(2 ** (attempt - 1), 8))

    async def async_authorize(self) -> bool:
        """Authenticate against the hOn CIAM endpoint and load the appliances.

        Replaces the legacy Salesforce Aura / OAuth2 login that Haier retired in
        2026-06: the app now logs in through /ciam/authorize + /ciam/token (PKCE)
        and reads appliances from /unified-api/v1/view/appliance-list. The old
        /commands/v1/appliance endpoint now returns an empty list.
        """
        self._authorizing = True
        try:
            return await self._async_authorize()
        finally:
            self._authorizing = False

    async def _async_authorize(self) -> bool:
        # PKCE (S256) verifier + challenge
        code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
        )
        code_challenge = (
            base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
            .rstrip(b"=")
            .decode()
        )

        # 1) Submit credentials, receive a one-time session id
        params = {
            "username": self._email,
            "password": self._password,
            "code_challenge": code_challenge,
        }
        json_data = await self._async_request(
            "GET", f"{API_URL}/ciam/authorize", params=params
        )
        session_id = json_data.get("session_id")
        if not session_id:
            _LOGGER.error("Unable to get [session_id] - check your email/password")
            raise HonAuthenticationError("Invalid credentials")

        # 2) Exchange the session id (+ PKCE verifier) for the tokens
        json_data = await self._async_request(
            "POST",
            f"{API_URL}/ciam/token",
            json={"session_id": session_id, "code_verifier": code_verifier},
        )
        try:
            tokens = json_data["tokens"]
            self._cognito_token = tokens["cognito_token"]
            self._id_token = tokens["id_token"]
            self._refresh_token = tokens.get("refresh_token", "")
        except (KeyError, TypeError):
            _LOGGER.error("Unable to get tokens from /ciam/token.")
            raise HonAuthenticationError("Invalid credentials") from None

        # 3) Load the appliance list from the unified-api view
        url = f"{API_URL}/unified-api/v1/view/appliance-list"
        json_data = await self._async_request(
            "POST", url, headers=self._headers, json={"deviceId": "homeassistant"}
        )
        try:
            self._appliances = json_data["modules"]["applianceList"]["payload"][
                "appliances"
            ]
        except (KeyError, TypeError):
            _LOGGER.error("hOn Invalid Data after POST [%s]", url)
            return False

        _LOGGER.debug("All appliances: %s", self._appliances)

        # Keep only appliances that expose a MAC address and a type id
        self._appliances = [
            appliance
            for appliance in self._appliances
            if "macAddress" in appliance and "applianceTypeId" in appliance
        ]

        self._start_time = time.time()
        return True

    async def load_commands(self, appliance: dict[str, Any]) -> dict[str, Any]:
        """Retrieve the command catalogue for an appliance."""
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
        json_data = await self._async_request(
            "GET", url, params=params, headers=self._headers
        )
        result = json_data.get("payload", {})
        if not result or result.pop("resultCode") != "0":
            return {}
        _LOGGER.debug("Commands: %s", result)
        return result

    async def async_get_context(self, device) -> dict[str, Any]:
        """Fetch the current device context (CYCLE)."""
        await self._ensure_session()

        params = {
            "macAddress": device.mac_address,
            "applianceType": device.appliance_type,
            "category": "CYCLE",
        }
        url = f"{API_URL}/commands/v1/context"
        json_data = await self._async_request(
            "GET", url, params=params, headers=self._headers
        )
        _LOGGER.debug("Context fetched for device type [%s]", device.appliance_type)
        return json_data.get("payload", {})

    async def load_statistics(self, device) -> dict[str, Any]:
        """Fetch the lifetime statistics for a device."""
        params = {
            "macAddress": device.mac_address,
            "applianceType": device.appliance_type,
        }
        url = f"{API_URL}/commands/v1/statistics"
        json_data = await self._async_request(
            "GET", url, params=params, headers=self._headers
        )
        _LOGGER.debug("Statistics fetched for device type [%s]", device.appliance_type)
        return json_data.get("payload", {})

    async def async_set(
        self, mac: str, type_name: str, parameters: dict[str, str]
    ) -> bool:
        """Send a startProgram command with the given parameters."""
        await self._ensure_session()

        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        attributes = {
            "prStr": "HOME_ASSISTANT",
            "channel": "googleHome",
            "origin": "conversationalVoice",
        }
        if type_name == "WM":
            attributes["energyLabel"] = "0"

        command = {
            "macAddress": mac,
            "commandName": "startProgram",
            "applianceOptions": {},
            "programName": f"PROGRAMS.{type_name}.HOME_ASSISTANT",
            "ancillaryParameters": {
                "programFamily": "[standard]",
                "remoteActionable": "1",
                "remoteVisible": "1",
            },
            "applianceType": type_name,
            "attributes": attributes,
            "device": {
                "mobileId": "xxxxxxxxxxxxxxxxxxx",
                "mobileOs": "android",
                "osVersion": "31",
                "appVersion": "1.53.4",
                "deviceModel": "lito",
            },
            "parameters": parameters,
            "timestamp": timestamp,
            "transactionId": f"{mac}_{timestamp}",
        }
        _LOGGER.debug("Command sent (async_set): %s", command)

        try:
            data = await self._async_request(
                "POST",
                f"{API_URL}/commands/v1/send",
                headers=self._headers,
                json=command,
            )
        except (json.JSONDecodeError, HonConnectionError):
            _LOGGER.error("hOn Invalid Data after sending command")
            return False
        _LOGGER.debug("Command result (async_set): %s", data)
        if data["payload"]["resultCode"] == "0":
            return True
        _LOGGER.error("hOn command has been rejected. Error message [%s]", data)
        return False

    async def send_command(
        self,
        device,
        command: str,
        parameters: dict[str, str],
        ancillary_parameters: dict[str, str],
    ) -> bool:
        """Send an arbitrary command to a device."""
        await self._ensure_session()

        now = datetime.now(UTC).isoformat()
        payload = {
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
                "deviceModel": DEVICE_MODEL,
            },
            "attributes": {
                "channel": "mobileApp",
                "origin": "standardProgram",
                "energyLabel": "0",
            },
            "ancillaryParameters": ancillary_parameters,
            "parameters": parameters,
            "applianceType": device.appliance_type,
        }
        _LOGGER.debug("Command sent (send_command): %s", payload)

        try:
            data = await self._async_request(
                "POST",
                f"{API_URL}/commands/v1/send",
                headers=self._headers,
                json=payload,
            )
        except (json.JSONDecodeError, HonConnectionError):
            _LOGGER.error("hOn Invalid Data after sending command")
            return False
        _LOGGER.debug("Command result (send_command): %s", data)
        if data["payload"]["resultCode"] == "0":
            return True
        _LOGGER.error("hOn command has been rejected. Error message [%s]", data)
        return False

    def get_device(self, hass, device_id):
        """Return the HonDevice registered for a device registry id."""
        mac = get_hOn_mac(device_id, hass)
        if mac in self._coordinator_dict:
            return self._coordinator_dict[mac].device
        _LOGGER.error(
            "Unable to find the device with ID: %s and mac: %s", device_id, mac
        )
        return None


def get_hOn_mac(device_id: str, hass) -> str:
    """Return the MAC address of a device registry entry."""
    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    return next(iter(device.identifiers))[1]
