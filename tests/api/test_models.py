"""Tests for the hOn API data models."""

from __future__ import annotations

from custom_components.hon.api.models import HonAppliance


def test_hon_appliance_from_dict(appliance: dict) -> None:
    """from_dict maps every camelCase API field onto the dataclass."""
    model = HonAppliance.from_dict(appliance)

    assert model.mac_address == appliance["macAddress"]
    assert model.appliance_type == appliance["applianceTypeName"]
    assert model.appliance_type_id == appliance["applianceTypeId"]
    assert model.brand == appliance["brand"]
    assert model.model_name == appliance["modelName"]
    assert model.model_id == appliance["applianceModelId"]
    assert model.fw_version == appliance["fwVersion"]
    assert model.serial_number == appliance["serialNumber"]
    assert model.nick_name == appliance["nickName"]
    assert model.connectivity == appliance["connectivity"]
    assert model.code == appliance["code"]
    assert model.series == appliance["series"]
    assert model.eeprom_id == appliance["eepromId"]
    assert model.raw == appliance


def test_hon_appliance_from_dict_missing_optional() -> None:
    """from_dict falls back to empty strings for missing optional fields."""
    model = HonAppliance.from_dict({"macAddress": "aa-bb", "applianceTypeId": 1})

    assert model.mac_address == "aa-bb"
    assert model.appliance_type == ""
    assert model.brand == ""
    assert model.model_name == ""
    assert model.nick_name == ""
    assert model.raw == {"macAddress": "aa-bb", "applianceTypeId": 1}


def test_hon_appliance_default_raw() -> None:
    """raw defaults to an empty dict for manual construction."""
    model = HonAppliance(
        mac_address="aa-bb",
        appliance_type="WM",
        appliance_type_id=1,
        brand="haier",
        model_name="M",
        model_id="id",
        fw_version="1",
        serial_number="SN",
        nick_name="Name",
        connectivity="wifi",
        code="C",
        series="S",
        eeprom_id="E",
    )
    assert model.raw == {}
