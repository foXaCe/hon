"""Tests for the hOn config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from aiohttp.client_reqrep import ConnectionKey
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hon.api.exceptions import (
    HonAuthenticationError,
    HonConnectionError,
    HonRateLimitError,
)
from custom_components.hon.config_flow import HonFlowHandler, HonOptionsFlowHandler
from custom_components.hon.const import CONF_UPDATE_INTERVAL, DOMAIN
from tests.conftest import EMAIL, PASSWORD

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


def _flow_connection(auth_ok: bool = True, exc: Exception | None = None) -> MagicMock:
    """Build a mocked HonConnection for the config flow."""
    connection = MagicMock()
    connection.async_authorize = AsyncMock(
        return_value=auth_ok if exc is None else None
    )
    if exc is not None:
        connection.async_authorize.side_effect = exc
    connection.async_close = AsyncMock()
    return connection


def _setup_connection() -> MagicMock:
    """Build a mocked HonConnection used by the auto entry setup."""
    connection = MagicMock()
    connection.async_authorize = AsyncMock(return_value=True)
    connection.async_close = AsyncMock()
    connection.appliances = []
    return connection


def _mock_entry() -> MockConfigEntry:
    """Build a config entry already added to hass."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_EMAIL: EMAIL,
            CONF_PASSWORD: PASSWORD,
            "token": "",
            "cognito_token": "",
            "refresh_token": "",
        },
        unique_id=EMAIL,
        version=2,
    )
    return entry


async def test_user_step_shows_form(hass) -> None:
    """Without user input the user step renders the credentials form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_user_step_success(hass) -> None:
    """A valid login creates an entry keyed by the email address."""
    with (
        patch(
            "custom_components.hon.config_flow.HonConnection",
            return_value=_flow_connection(),
        ) as connection_cls,
        patch("custom_components.hon.HonConnection", return_value=_setup_connection()),
        patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["result"].unique_id == EMAIL
    assert result["data"][CONF_EMAIL] == EMAIL
    assert result["data"][CONF_PASSWORD] == PASSWORD
    connection_cls.assert_called_once()


async def test_user_step_invalid_auth(hass) -> None:
    """Invalid credentials surface as an invalid_auth error."""
    with patch(
        "custom_components.hon.config_flow.HonConnection",
        return_value=_flow_connection(exc=HonAuthenticationError("bad")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_step_invalid_auth_when_login_returns_false(hass) -> None:
    """A successful call returning False also means invalid credentials."""
    with patch(
        "custom_components.hon.config_flow.HonConnection",
        return_value=_flow_connection(auth_ok=False),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


@pytest.mark.parametrize(
    "exc",
    [
        HonConnectionError("down"),
        HonRateLimitError("limited"),
        aiohttp.ClientConnectorError(
            ConnectionKey("host", 443, True, None, None, None, None, None),
            OSError("connection refused"),
        ),
    ],
)
async def test_user_step_cannot_connect(hass, exc: Exception) -> None:
    """Transport failures surface as a cannot_connect error."""
    with patch(
        "custom_components.hon.config_flow.HonConnection",
        return_value=_flow_connection(exc=exc),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_step_already_configured(hass) -> None:
    """A duplicate email aborts the flow with already_configured."""
    _mock_entry().add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD},
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_import_step_delegates_to_user(hass) -> None:
    """The import step reuses the user step."""
    with (
        patch(
            "custom_components.hon.config_flow.HonConnection",
            return_value=_flow_connection(),
        ),
        patch("custom_components.hon.HonConnection", return_value=_setup_connection()),
        patch.object(hass.config_entries, "async_forward_entry_setups", AsyncMock()),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_IMPORT}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_EMAIL: EMAIL, CONF_PASSWORD: PASSWORD},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_reauth_success(hass) -> None:
    """A valid reauth updates the stored password and aborts."""
    entry = _mock_entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.hon.config_flow.HonConnection",
        return_value=_flow_connection(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
        )
        assert result["type"] == FlowResultType.FORM
        with patch.object(hass.config_entries, "async_reload", AsyncMock()):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {CONF_PASSWORD: "new-password"}
            )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_PASSWORD] == "new-password"
    assert entry.data["token"] == ""


async def test_reauth_invalid_auth(hass) -> None:
    """Invalid credentials during reauth keep the form open."""
    entry = _mock_entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.hon.config_flow.HonConnection",
        return_value=_flow_connection(exc=HonAuthenticationError("bad")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "wrong"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reconfigure_success(hass) -> None:
    """A valid reconfigure updates the password and aborts."""
    entry = _mock_entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.hon.config_flow.HonConnection",
        return_value=_flow_connection(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        assert result["type"] == FlowResultType.FORM
        with patch.object(hass.config_entries, "async_reload", AsyncMock()):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {CONF_PASSWORD: "updated"}
            )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_PASSWORD] == "updated"


async def test_reconfigure_cannot_connect(hass) -> None:
    """A transport failure during reconfigure keeps the form open."""
    entry = _mock_entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.hon.config_flow.HonConnection",
        return_value=_flow_connection(exc=HonConnectionError("down")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "updated"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_async_get_options_flow(hass) -> None:
    """async_get_options_flow returns an options flow handler."""
    entry = _mock_entry()
    flow = HonFlowHandler().async_get_options_flow(entry)
    assert isinstance(flow, HonOptionsFlowHandler)


def _make_options_handler(hass, entry) -> HonOptionsFlowHandler:
    """Build an options handler linked to the config entry."""
    handler = object.__new__(HonOptionsFlowHandler)
    handler.hass = hass
    handler.handler = entry.entry_id
    return handler


async def test_options_flow_init_form(hass) -> None:
    """The options form is rendered without user input."""
    entry = _mock_entry()
    entry.add_to_hass(hass)
    handler = _make_options_handler(hass, entry)
    result = await handler.async_step_init()
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_init_creates_entry(hass) -> None:
    """Submitting the options form creates an entry with the data."""
    entry = _mock_entry()
    entry.add_to_hass(hass)
    handler = _make_options_handler(hass, entry)
    result = await handler.async_step_init({CONF_UPDATE_INTERVAL: 120})
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_UPDATE_INTERVAL: 120}


async def test_options_flow_via_framework(hass) -> None:
    """The options flow can be started through the framework (no 500)."""
    entry = _mock_entry()
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_UPDATE_INTERVAL: 120}
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_UPDATE_INTERVAL: 120}


async def test_reauth_cannot_connect(hass) -> None:
    """A transport failure during reauth keeps the form open."""
    entry = _mock_entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.hon.config_flow.HonConnection",
        return_value=_flow_connection(exc=HonConnectionError("down")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "new"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_reconfigure_invalid_auth(hass) -> None:
    """Invalid credentials during reconfigure keep the form open."""
    entry = _mock_entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.hon.config_flow.HonConnection",
        return_value=_flow_connection(exc=HonAuthenticationError("bad")),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "new"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reconfigure_login_false(hass) -> None:
    """A falsy authorize result during reconfigure keeps the form open."""
    entry = _mock_entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.hon.config_flow.HonConnection",
        return_value=_flow_connection(auth_ok=False),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "new"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_reauth_login_false(hass) -> None:
    """A falsy authorize result during reauth keeps the form open."""
    entry = _mock_entry()
    entry.add_to_hass(hass)
    with patch(
        "custom_components.hon.config_flow.HonConnection",
        return_value=_flow_connection(auth_ok=False),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_REAUTH,
                "entry_id": entry.entry_id,
            },
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_PASSWORD: "new"}
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}
