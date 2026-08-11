"""Shared fixtures for the hon test suite."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.hon.const import DOMAIN

EMAIL = "test@example.com"
PASSWORD = "test-password"
MAC = "08-b6-1f-de-c9-14"
MAC2 = "ac-15-18-df-2b-64"
ENTRY_UID = f"{EMAIL}_{MAC}"


def build_appliance(
    mac: str = MAC,
    appliance_type: str = "WM",
    appliance_type_id: int = 1,
    brand: str = "haier",
    model_name: str = "HW100-B14959U1FR",
    nick_name: str = "Lave-linge",
    extra: dict | None = None,
) -> dict:
    """Build a raw hOn appliance payload."""
    payload = {
        "macAddress": mac,
        "applianceTypeName": appliance_type,
        "applianceTypeId": appliance_type_id,
        "brand": brand,
        "modelName": model_name,
        "applianceModelId": "model-1",
        "fwVersion": "5.30.0",
        "serialNumber": "SN123",
        "nickName": nick_name,
        "connectivity": "wifi",
        "code": "CODE",
        "series": "series",
        "eepromId": "eeprom",
    }
    if extra:
        payload.update(extra)
    return payload


def context_payload(parameters: dict | None = None) -> dict:
    """Build a minimal /commands/v1/context payload."""
    params = {
        "onOffStatus": "1",
        "machMode": "1",
        "tempSel": "40",
        "remainingTimeMM": "30",
        **({} if parameters is None else parameters),
    }
    return {
        "payload": {
            "shadow": {
                "parameters": {
                    name: {"parNewVal": value} for name, value in params.items()
                }
            }
        }
    }


@pytest.fixture
def appliance() -> dict:
    """A single washing machine appliance."""
    return build_appliance()


@pytest.fixture
def appliance_climate() -> dict:
    """A single climate appliance."""
    return build_appliance(
        mac=MAC2,
        appliance_type="AC",
        appliance_type_id=11,
        model_name="Climate 5000",
        nick_name="Climatiseur",
    )


@pytest.fixture
def mock_connection() -> MagicMock:
    """A fully mocked HonConnection."""
    connection = MagicMock()
    connection.appliances = [build_appliance()]
    connection.async_authorize = AsyncMock(return_value=True)
    connection.async_restore_or_authorize = AsyncMock(return_value=True)
    connection.persist_tokens = MagicMock()
    connection.async_close = AsyncMock()
    connection.async_get_context = AsyncMock(return_value=context_payload())
    connection.load_commands = AsyncMock(
        return_value={"applianceModel": {}, "options": {}}
    )
    connection.load_statistics = AsyncMock(return_value={})
    connection.async_set = AsyncMock(return_value=True)
    connection.send_command = AsyncMock(return_value=True)
    connection.entry = None
    connection.async_load_setup_cache = AsyncMock()
    connection.get_cached_setup = MagicMock(return_value=None)
    connection.store_setup_cache = MagicMock()
    connection.get_cached_appliances = MagicMock(return_value=None)
    connection.store_cached_appliances = MagicMock()
    connection.prune_coordinators = MagicMock()
    return connection


@pytest.fixture
def config_entry(hass) -> MockConfigEntry:
    """A config entry for the hon integration."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "email": EMAIL,
            "password": PASSWORD,
            "id_token": "",
            "cognito_token": "",
            "refresh_token": "",
        },
        unique_id=EMAIL,
        version=2,
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def config_entry_v1(hass) -> MockConfigEntry:
    """A config entry at version 1 (for migration tests)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            "email": EMAIL,
            "password": PASSWORD,
            "id_token": "",
            "cognito_token": "",
            "refresh_token": "",
        },
        unique_id=EMAIL,
        version=1,
    )
    entry.add_to_hass(hass)
    return entry
