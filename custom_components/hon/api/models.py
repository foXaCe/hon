"""Data models for hOn API responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HonAppliance:
    """An appliance (device) owned by the account."""

    mac_address: str
    appliance_type: str
    appliance_type_id: int
    brand: str
    model_name: str
    model_id: str
    fw_version: str
    serial_number: str
    nick_name: str
    connectivity: str
    code: str
    series: str
    eeprom_id: str
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HonAppliance:
        """Build an appliance from the raw API payload."""
        return cls(
            mac_address=data["macAddress"],
            appliance_type=data.get("applianceTypeName", ""),
            appliance_type_id=data["applianceTypeId"],
            brand=data.get("brand", ""),
            model_name=data.get("modelName", ""),
            model_id=data.get("applianceModelId", ""),
            fw_version=data.get("fwVersion", ""),
            serial_number=data.get("serialNumber", ""),
            nick_name=data.get("nickName", ""),
            connectivity=data.get("connectivity", ""),
            code=data.get("code", ""),
            series=data.get("series", ""),
            eeprom_id=data.get("eepromId", ""),
            raw=data,
        )
