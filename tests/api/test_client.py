"""Tests for the hOn cloud API client."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest

from custom_components.hon.api.client import (
    HonConnection,
    async_remove_setup_cache,
    get_hOn_mac,
)
from custom_components.hon.api.exceptions import (
    HonAuthenticationError,
    HonConnectionError,
    HonPasswordChangeRequiredError,
    HonRateLimitError,
)
from custom_components.hon.const import APP_VERSION, CONF_UPDATE_INTERVAL, DOMAIN
from custom_components.hon.coordinator import HonBaseCoordinator
from tests.conftest import EMAIL, MAC, PASSWORD, build_appliance

if TYPE_CHECKING:
    from collections.abc import Callable


class FakeResponse:
    """An aiohttp response stand-in usable as an async context manager."""

    def __init__(
        self, status: int, json_data: Any = None, exc: Exception | None = None
    ) -> None:
        self.status = status
        self._json_data = json_data
        self._exc = exc

    async def __aenter__(self) -> FakeResponse:
        if self._exc is not None:
            raise self._exc
        return self

    async def __aexit__(self, *exc_info: Any) -> bool:
        return False

    async def json(self) -> Any:
        return self._json_data


class FakeTextResponse(FakeResponse):
    """A response that raises on json() and exposes raw text.

    Models the hOn ``ChangePassword`` HTML redirect that the authorize step
    can return instead of JSON.
    """

    def __init__(self, status: int, text: str) -> None:
        super().__init__(status, None)
        self._text = text

    async def json(self) -> Any:
        raise aiohttp.ContentTypeError(None, ()) from None

    async def text(self) -> str:
        return self._text


class FakeSession:
    """An aiohttp session stand-in serving responses from a queue."""

    def __init__(self, responses: list[FakeResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict[str, Any]]] = []
        self.closed = False

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        response = self._responses.pop(0)
        self.calls.append((method, url, kwargs))
        return response

    async def close(self) -> None:
        self.closed = True


def authorize_responses(
    appliances: list[dict[str, Any]] | None = None,
) -> list[FakeResponse]:
    """Build the three responses of a successful CIAM login."""
    if appliances is None:
        appliances = [build_appliance()]
    return [
        FakeResponse(200, {"session_id": "session-1"}),
        FakeResponse(
            200,
            {
                "tokens": {
                    "cognito_token": "cognito",
                    "id_token": "id",
                    "refresh_token": "refresh",
                }
            },
        ),
        FakeResponse(
            200,
            {"modules": {"applianceList": {"payload": {"appliances": appliances}}}},
        ),
    ]


def make_entry(options: dict[str, Any] | None = None) -> MagicMock:
    """Build a config-entry stand-in with the expected data/options."""
    entry = MagicMock()
    entry.data = {
        "email": EMAIL,
        "password": PASSWORD,
        "token": "",
        "refresh_token": "",
        "cognito_token": "",
    }
    entry.options = options or {}
    entry.unique_id = EMAIL
    return entry


def make_connection(
    responses: list[FakeResponse] | None = None, entry: Any | None = None
) -> HonConnection:
    """Build a HonConnection backed by a fake session (no real network)."""
    if entry is not None:
        connection = HonConnection(None, entry)
    else:
        connection = HonConnection(None, None, EMAIL, PASSWORD)
        connection._id_token = ""
        connection._cognito_token = ""
    connection._session = FakeSession(responses or [])
    return connection


@pytest.fixture
def fake_response() -> Callable[..., FakeResponse]:
    """Return a factory building :class:`FakeResponse` instances."""

    def _factory(
        status: int, json_data: Any = None, exc: Exception | None = None
    ) -> FakeResponse:
        return FakeResponse(status, json_data, exc)

    return _factory


async def test_async_authorize_success() -> None:
    """A full CIAM login returns True and stores the appliances."""
    connection = make_connection(authorize_responses())
    assert await connection.async_authorize() is True
    assert connection._cognito_token == "cognito"
    assert connection._id_token == "id"
    assert connection._refresh_token == "refresh"
    assert connection.appliances == [build_appliance()]


async def test_async_restore_or_authorize_uses_stored_tokens() -> None:
    """A session with stored tokens skips the PKCE round-trips."""
    entry = make_entry()
    connection = make_connection(
        [
            FakeResponse(
                200,
                {
                    "modules": {
                        "applianceList": {
                            "payload": {"appliances": [build_appliance()]}
                        }
                    }
                },
            )
        ],
        entry=entry,
    )
    connection._id_token = "id"
    connection._cognito_token = "cognito"
    assert await connection.async_restore_or_authorize() is True
    assert connection.appliances == [build_appliance()]
    # Only the appliance-list request was made (no CIAM authorize/token)
    assert len(connection._session.calls) == 1


async def test_async_restore_or_authorize_falls_back_on_401() -> None:
    """A rejected stored session triggers a full PKCE login."""
    entry = make_entry()
    connection = make_connection(
        [
            FakeResponse(401, {}),
            *authorize_responses(),
        ],
        entry=entry,
    )
    connection._id_token = "stale"
    connection._cognito_token = "stale"
    with patch("custom_components.hon.api.client.asyncio.sleep", AsyncMock()):
        assert await connection.async_restore_or_authorize() is True
    assert connection._cognito_token == "cognito"
    assert connection.appliances == [build_appliance()]


async def test_async_restore_or_authorize_falls_back_on_403() -> None:
    """A revoked stored session (403) also triggers a full PKCE login."""
    entry = make_entry()
    connection = make_connection(
        [
            FakeResponse(403, {}),
            *authorize_responses(),
        ],
        entry=entry,
    )
    connection._id_token = "revoked"
    connection._cognito_token = "revoked"
    assert await connection.async_restore_or_authorize() is True
    assert connection._cognito_token == "cognito"
    assert connection.appliances == [build_appliance()]


async def test_async_request_refreshes_on_403() -> None:
    """A 403 during a data request triggers a token refresh then retries."""
    connection = make_connection(
        [
            FakeResponse(403, {}),
            *authorize_responses(),
            FakeResponse(200, {"final": True}),
        ]
    )
    result = await connection._async_request("GET", "https://example.test/x")
    assert result == {"final": True}
    assert connection._cognito_token == "cognito"


async def test_async_restore_or_authorize_without_tokens() -> None:
    """Without stored tokens the full login runs."""
    connection = make_connection(authorize_responses())
    connection._id_token = ""
    connection._cognito_token = ""
    assert await connection.async_restore_or_authorize() is True
    assert connection.appliances == [build_appliance()]


async def test_async_restore_or_authorize_auth_failed() -> None:
    """A genuine credential failure after restore raises."""
    entry = make_entry()
    connection = make_connection(
        [FakeResponse(401, {}), FakeResponse(200, {"error": "nope"})],
        entry=entry,
    )
    connection._id_token = "stale"
    connection._cognito_token = "stale"
    with (
        patch("custom_components.hon.api.client.asyncio.sleep", AsyncMock()),
        pytest.raises(HonAuthenticationError),
    ):
        await connection.async_restore_or_authorize()


async def test_persist_tokens_updates_entry(hass) -> None:
    """persist_tokens writes the current tokens back to the config entry."""
    entry = make_entry()
    connection = HonConnection(hass, entry)
    connection._id_token = "new-id"
    connection._cognito_token = "new-cognito"
    connection._refresh_token = "new-refresh"
    with patch.object(hass.config_entries, "async_update_entry") as update_entry:
        connection.persist_tokens()
    update_entry.assert_called_once()
    updated_data = update_entry.call_args.kwargs["data"]
    assert updated_data["token"] == "new-id"
    assert updated_data["cognito_token"] == "new-cognito"
    assert updated_data["refresh_token"] == "new-refresh"


async def test_persist_tokens_without_entry() -> None:
    """persist_tokens is a no-op during the config flow (no entry)."""
    connection = HonConnection(None, None, EMAIL, PASSWORD)
    connection.persist_tokens()  # must not raise


async def test_async_authorize_filters_appliances() -> None:
    """Appliances missing a MAC or a type id are dropped."""
    with_mac = {"macAddress": MAC, "applianceTypeId": 1, "brand": "haier"}
    without_mac = {"applianceTypeId": 2}
    without_type = {"macAddress": "00-11-22-33-44-55"}
    connection = make_connection(
        authorize_responses([with_mac, without_mac, without_type])
    )
    assert await connection.async_authorize() is True
    assert connection.appliances == [with_mac]


async def test_async_authorize_missing_session_id() -> None:
    """A response without a session id means invalid credentials."""
    connection = make_connection([FakeResponse(200, {"error": "nope"})])
    with pytest.raises(HonAuthenticationError):
        await connection.async_authorize()


async def test_async_authorize_password_change_required() -> None:
    """A ChangePassword HTML reply raises the dedicated error."""
    html = FakeTextResponse(200, "<html>ChangePassword</html>")
    connection = make_connection(
        [html, FakeTextResponse(200, "<html>ChangePassword</html>")]
    )
    with pytest.raises(HonPasswordChangeRequiredError):
        await connection.async_authorize()


async def test_async_authorize_missing_tokens() -> None:
    """A token response without the tokens key raises."""
    connection = make_connection(
        [
            FakeResponse(200, {"session_id": "session-1"}),
            FakeResponse(200, {"unexpected": True}),
        ]
    )
    with pytest.raises(HonAuthenticationError):
        await connection.async_authorize()


async def test_async_authorize_invalid_appliance_payload() -> None:
    """An appliance-list payload without the expected shape returns False."""
    connection = make_connection(
        [
            FakeResponse(200, {"session_id": "session-1"}),
            FakeResponse(
                200,
                {
                    "tokens": {
                        "cognito_token": "c",
                        "id_token": "i",
                        "refresh_token": "r",
                    }
                },
            ),
            FakeResponse(200, {"modules": {}}),
        ]
    )
    assert await connection.async_authorize() is False


async def test_async_authorize_401_loop_avoided() -> None:
    """A 401 while authorizing raises instead of looping."""
    connection = make_connection([FakeResponse(401, {})])
    connection._authorizing = True
    with pytest.raises(HonAuthenticationError):
        await connection._async_request("GET", "https://example.test/x")


async def test_async_request_retries_on_500() -> None:
    """A transient 500 is retried once before a successful call."""
    connection = make_connection(
        [FakeResponse(500, {}), FakeResponse(200, {"ok": True})]
    )
    with patch(
        "custom_components.hon.api.client.asyncio.sleep", AsyncMock()
    ) as sleep_mock:
        result = await connection._async_request("GET", "https://example.test/x")
    assert result == {"ok": True}
    sleep_mock.assert_awaited_once_with(1)


async def test_async_request_rate_limit_after_retries() -> None:
    """Persistent 429s raise HonRateLimitError once retries are exhausted."""
    connection = make_connection([FakeResponse(429, {})] * 4)
    with (
        patch("custom_components.hon.api.client.asyncio.sleep", AsyncMock()),
        pytest.raises(HonRateLimitError),
    ):
        await connection._async_request("GET", "https://example.test/x")


async def test_async_request_connection_error_after_retries() -> None:
    """A failing transport raises HonConnectionError after retries."""
    connection = make_connection(
        [FakeResponse(200, {}, exc=aiohttp.ClientError("boom"))] * 4
    )
    with (
        patch("custom_components.hon.api.client.asyncio.sleep", AsyncMock()),
        pytest.raises(HonConnectionError),
    ):
        await connection._async_request("GET", "https://example.test/x")


async def test_async_request_refreshes_on_401() -> None:
    """A 401 triggers a token refresh then the request is retried."""
    connection = make_connection(
        [
            FakeResponse(401, {}),
            *authorize_responses(),
            FakeResponse(200, {"final": True}),
        ]
    )
    result = await connection._async_request("GET", "https://example.test/x")
    assert result == {"final": True}
    assert connection._cognito_token == "cognito"


async def test_async_request_raises_on_4xx() -> None:
    """Any other >= 400 status raises HonConnectionError."""
    connection = make_connection([FakeResponse(400, {})])
    with pytest.raises(HonConnectionError):
        await connection._async_request("GET", "https://example.test/x")


async def test_load_commands_success() -> None:
    """load_commands returns the payload after dropping resultCode."""
    connection = make_connection(
        [FakeResponse(200, {"payload": {"resultCode": "0", "applianceModel": {}}})]
    )
    result = await connection.load_commands(build_appliance())
    assert result == {"applianceModel": {}}


async def test_load_commands_failure() -> None:
    """A non-zero resultCode yields an empty dict."""
    connection = make_connection([FakeResponse(200, {"payload": {"resultCode": "1"}})])
    assert await connection.load_commands(build_appliance()) == {}


async def test_load_commands_empty_payload() -> None:
    """A missing payload yields an empty dict."""
    connection = make_connection([FakeResponse(200, {})])
    assert await connection.load_commands(build_appliance()) == {}


async def test_load_commands_missing_series() -> None:
    """An appliance without a series field does not raise a KeyError."""
    connection = make_connection(
        [FakeResponse(200, {"payload": {"resultCode": "0", "applianceModel": {}}})]
    )
    appliance = build_appliance()
    appliance.pop("series", None)
    result = await connection.load_commands(appliance)
    assert result == {"applianceModel": {}}


async def test_async_get_context() -> None:
    """async_get_context returns the payload of the context endpoint."""
    device = MagicMock()
    device.mac_address = MAC
    device.appliance_type = "WM"
    connection = make_connection([FakeResponse(200, {"payload": {"shadow": {}}})])
    result = await connection.async_get_context(device)
    assert result == {"shadow": {}}


async def test_load_statistics() -> None:
    """load_statistics returns the payload of the statistics endpoint."""
    device = MagicMock()
    device.mac_address = MAC
    device.appliance_type = "WM"
    connection = make_connection([FakeResponse(200, {"payload": {"k": "v"}})])
    result = await connection.load_statistics(device)
    assert result == {"k": "v"}


async def test_async_set_success() -> None:
    """async_set returns True on a zero resultCode."""
    connection = make_connection([FakeResponse(200, {"payload": {"resultCode": "0"}})])
    assert await connection.async_set(MAC, "WM", {"onOffStatus": "1"}) is True


async def test_async_set_rejected() -> None:
    """async_set returns False on a non-zero resultCode."""
    connection = make_connection([FakeResponse(200, {"payload": {"resultCode": "1"}})])
    assert await connection.async_set(MAC, "WM", {"onOffStatus": "1"}) is False


async def test_async_set_connection_error() -> None:
    """async_set returns False when the transport fails."""
    connection = make_connection([FakeResponse(400, {})])
    assert await connection.async_set(MAC, "WM", {}) is False


async def test_send_command_success() -> None:
    """send_command returns True on a zero resultCode."""
    device = MagicMock()
    device.mac_address = MAC
    device.appliance_type = "WM"
    device.commands_options = {}
    connection = make_connection([FakeResponse(200, {"payload": {"resultCode": "0"}})])
    assert await connection.send_command(device, "startProgram", {}, {}) is True


async def test_send_command_rejected() -> None:
    """send_command returns False on a non-zero resultCode."""
    device = MagicMock()
    device.mac_address = MAC
    device.appliance_type = "WM"
    device.commands_options = {}
    connection = make_connection([FakeResponse(200, {"payload": {"resultCode": "1"}})])
    assert await connection.send_command(device, "startProgram", {}, {}) is False


async def test_async_get_coordinator_creates(hass) -> None:
    """async_get_coordinator creates a coordinator with the entry interval."""
    entry = make_entry(options={CONF_UPDATE_INTERVAL: 120})
    connection = make_connection(entry=entry)
    coordinator = await connection.async_get_coordinator(build_appliance())
    assert isinstance(coordinator, HonBaseCoordinator)
    assert coordinator.update_interval == timedelta(seconds=120)
    assert await connection.async_get_coordinator(build_appliance()) is coordinator


async def test_async_get_coordinator_default_interval(hass) -> None:
    """A missing update interval falls back to the default scan interval."""
    entry = make_entry(options={})
    connection = make_connection(entry=entry)
    coordinator = await connection.async_get_coordinator(build_appliance())
    assert coordinator.update_interval == timedelta(seconds=60)


async def test_async_get_existing_coordinator() -> None:
    """async_get_existing_coordinator returns only known MACs."""
    connection = make_connection()
    existing = MagicMock()
    connection._coordinator_dict[MAC] = existing
    assert await connection.async_get_existing_coordinator(MAC) is existing
    assert await connection.async_get_existing_coordinator("00-00") is None


async def test_get_device() -> None:
    """get_device resolves the coordinator registered for a MAC."""
    connection = make_connection()
    device = MagicMock()
    coordinator = MagicMock()
    coordinator.device = device
    connection._coordinator_dict[MAC] = coordinator
    with patch(
        "custom_components.hon.api.client.get_hOn_mac", return_value=MAC
    ) as get_mac:
        assert connection.get_device(None, "device-id") is device
    get_mac.assert_called_once_with("device-id", None)


async def test_get_device_unknown() -> None:
    """get_device returns None for an unknown device id."""
    connection = make_connection()
    with patch("custom_components.hon.api.client.get_hOn_mac", return_value=MAC):
        assert connection.get_device(None, "device-id") is None


async def test_get_hon_mac(hass, config_entry) -> None:
    """get_hOn_mac returns the first identifier of the device."""
    from homeassistant.helpers import device_registry as dr

    registry = dr.async_get(hass)
    device = registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, MAC)},
    )
    assert get_hOn_mac(device.id, hass) == MAC


async def test_async_close_closes_private_session() -> None:
    """async_close closes and clears the private session."""
    connection = make_connection()
    session = FakeSession([])
    connection._session = session
    await connection.async_close()
    assert session.closed
    assert connection._session is None


async def test_async_close_without_session() -> None:
    """async_close is a no-op when no private session exists."""
    connection = make_connection()
    connection._session = None
    await connection.async_close()


async def test_appliances_property() -> None:
    """appliances exposes the internal appliance list."""
    connection = make_connection()
    appliances = [{"mac": "1"}]
    connection._appliances = appliances
    assert connection.appliances == appliances


async def test_entry_property() -> None:
    """entry exposes the config entry bound to the connection."""
    entry = make_entry()
    connection = make_connection(entry=entry)
    assert connection.entry is entry


async def test_headers() -> None:
    """_headers carries the current tokens."""
    connection = make_connection()
    connection._cognito_token = "cognito"
    connection._id_token = "id"
    headers = connection._headers
    assert headers["cognito-token"] == "cognito"
    assert headers["id-token"] == "id"


async def test_ensure_session_refreshes_when_expired() -> None:
    """_ensure_session re-authenticates when the session is stale."""
    connection = make_connection()
    connection._start_time = 0
    connection.async_authorize = AsyncMock(return_value=True)
    await connection._ensure_session()
    connection.async_authorize.assert_awaited_once()


async def test_ensure_session_skips_when_fresh() -> None:
    """_ensure_session does nothing for a fresh session."""
    connection = make_connection()
    connection.async_authorize = AsyncMock(return_value=True)
    await connection._ensure_session()
    connection.async_authorize.assert_not_awaited()


async def test_async_request_refresh_401_exhausted() -> None:
    """Repeated 401s after refreshing eventually raise HonAuthenticationError."""
    connection = make_connection(
        [
            *([FakeResponse(401, {})] + authorize_responses()) * 4,
            FakeResponse(200, {}),
        ]
    )
    with pytest.raises(HonAuthenticationError):
        await connection._async_request("GET", "https://example.test/x")


async def test_send_command_connection_error() -> None:
    """send_command returns False when the transport fails."""
    device = MagicMock()
    device.mac_address = MAC
    device.appliance_type = "WM"
    device.commands_options = {}
    connection = make_connection([FakeResponse(400, {})])
    assert await connection.send_command(device, "startProgram", {}, {}) is False


async def test_session_provider_creates_private_session() -> None:
    """_session_provider creates a private aiohttp session when needed."""
    connection = HonConnection(None, None, EMAIL, PASSWORD)
    fake_session = FakeSession([])
    with patch(
        "custom_components.hon.api.client.aiohttp.ClientSession",
        return_value=fake_session,
    ) as client_session:
        session = connection._session_provider
    client_session.assert_called_once()
    assert session is fake_session
    assert connection._session is fake_session
    await connection.async_close()
    assert fake_session.closed


async def test_session_provider_uses_hass_session(hass) -> None:
    """_session_provider returns the hass client session when available."""
    connection = HonConnection(hass, None, EMAIL, PASSWORD)
    with patch(
        "custom_components.hon.api.client.async_get_clientsession",
        return_value="hass-session",
    ) as get_session:
        assert connection._session_provider == "hass-session"
    get_session.assert_called_once_with(hass)


async def test_setup_cache_roundtrip(hass) -> None:
    """store_setup_cache feeds get_cached_setup and keys on fw/app versions."""
    entry = make_entry()
    entry.entry_id = "entry-1"
    connection = HonConnection(hass, entry)
    await connection.async_load_setup_cache()
    assert connection.get_cached_setup(MAC, "5.30.0") is None

    connection.store_setup_cache(MAC, "5.30.0", {"applianceModel": {}}, {"s": 1})
    cached = connection.get_cached_setup(MAC, "5.30.0")
    assert cached is not None
    assert cached["commands"] == {"applianceModel": {}}
    assert cached["statistics"] == {"s": 1}
    # A firmware change invalidates the cached entry.
    assert connection.get_cached_setup(MAC, "6.0.0") is None


async def test_get_cached_setup_app_version_mismatch(hass) -> None:
    """An integration app-version bump invalidates the cached entry."""
    entry = make_entry()
    entry.entry_id = "entry-1"
    connection = HonConnection(hass, entry)
    await connection.async_load_setup_cache()
    connection.store_setup_cache(MAC, "5.30.0", {}, {})
    connection._setup_cache[MAC]["app_version"] = "0.0.0"
    assert connection.get_cached_setup(MAC, "5.30.0") is None


async def test_store_setup_cache_schedules_save(hass) -> None:
    """store_setup_cache schedules a coalesced disk write."""
    entry = make_entry()
    entry.entry_id = "entry-1"
    connection = HonConnection(hass, entry)
    await connection.async_load_setup_cache()
    with patch.object(connection._setup_store, "async_delay_save") as delay_save:
        connection.store_setup_cache(MAC, "5.30.0", {}, {})
    delay_save.assert_called_once()
    assert delay_save.call_args.args[0]() is connection._setup_cache


async def test_setup_cache_noop_without_entry() -> None:
    """During the config flow the setup cache is inert."""
    connection = HonConnection(None, None, EMAIL, PASSWORD)
    await connection.async_load_setup_cache()
    assert connection._setup_store is None
    connection.store_setup_cache(MAC, "5.30.0", {}, {})  # must not raise
    assert connection.get_cached_setup(MAC, "5.30.0") is None


async def test_async_load_setup_cache_restores(hass, hass_storage) -> None:
    """A persisted cache is restored from disk on the next boot."""
    key = f"{DOMAIN}.setup_cache_entry-1"
    hass_storage[key] = {
        "version": 1,
        "key": key,
        "data": {
            MAC: {
                "fw_version": "5.30.0",
                "app_version": APP_VERSION,
                "commands": {"c": 1},
                "statistics": {"s": 2},
            }
        },
    }
    entry = make_entry()
    entry.entry_id = "entry-1"
    connection = HonConnection(hass, entry)
    await connection.async_load_setup_cache()
    cached = connection.get_cached_setup(MAC, "5.30.0")
    assert cached is not None
    assert cached["commands"] == {"c": 1}


async def test_async_remove_setup_cache(hass, hass_storage) -> None:
    """Removing the cache deletes the on-disk store."""
    key = f"{DOMAIN}.setup_cache_entry-1"
    hass_storage[key] = {"version": 1, "key": key, "data": {}}
    await async_remove_setup_cache(hass, "entry-1")
    assert key not in hass_storage
