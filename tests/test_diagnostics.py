"""Tests for the hon diagnostics."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.hon.coordinator import HonBaseCoordinator

pytestmark = pytest.mark.usefixtures("enable_custom_integrations")


async def test_diagnostics_redacts_and_structures(
    hass, mock_connection, config_entry
) -> None:
    """Diagnostics redact secrets and expose devices/entities."""
    config_entry.runtime_data = mock_connection

    coordinator = MagicMock(spec=HonBaseCoordinator)
    coordinator.last_update_success = True
    coordinator.device = MagicMock()
    coordinator.device.mac_address = "08-b6-1f-de-c9-14"
    coordinator.device.attributes = {"onOffStatus": "1", "tempSel": "40"}
    mock_connection._coordinator_dict = {"08-b6-1f-de-c9-14": coordinator}

    mock_connection.appliances = [
        {
            "macAddress": "08-b6-1f-de-c9-14",
            "serialNumber": "SN123",
            "brand": "haier",
        }
    ]

    from custom_components.hon.diagnostics import async_get_config_entry_diagnostics

    device = MagicMock()
    device.id = "dev1"
    device.name = "Lave-linge"
    device.identifiers = {("hon", "08-b6-1f-de-c9-14", "WM")}
    device.manufacturer = "haier"
    device.model = "HW100"
    device.sw_version = "5.30"
    device.config_entry_id = config_entry.entry_id

    entity = MagicMock()
    entity.entity_id = "sensor.lave_linge_mode"
    entity.platform = "hon"
    entity.unique_id = "email_08-b6-1f-de-c9-14_mach_mode"
    entity.device_id = "dev1"
    entity.disabled_by = None
    entity.config_entry_id = config_entry.entry_id

    with (
        patch(
            "custom_components.hon.diagnostics.dr.async_get",
            return_value=MagicMock(devices={"dev1": device}),
        ),
        patch(
            "custom_components.hon.diagnostics.er.async_get",
            return_value=MagicMock(entities={"entity1": entity}),
        ),
    ):
        result = await async_get_config_entry_diagnostics(hass, config_entry)

    assert result["entry"]["password"] == "**REDACTED**"
    assert result["entry"]["email"] == "**REDACTED**"
    assert result["entry"]["id_token"] == ""
    # les appliances et coordinators sont redactés (serialNumber masqué)
    assert result["appliances"][0]["serialNumber"] == "**REDACTED**"
    assert "coordinators" in result
    assert len(result["entities"]) == 1
    assert result["entities"][0]["entity_id"] == "sensor.lave_linge_mode"
    assert len(result["devices"]) == 1
    assert result["devices"][0]["name"] == "Lave-linge"
