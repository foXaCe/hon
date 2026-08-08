"""Shared fixtures for the hOn device entity tests."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.hon.coordinator import HonBaseCoordinator
from tests.conftest import MAC


class FakeDevice:
    """A minimal HonDevice stand-in backed by a plain dict."""

    def __init__(self, data: dict[str, Any] | None = None, program_name=None) -> None:
        self._data = data or {}
        self._program_name = program_name
        self.mac_address = MAC
        self.appliance_type = "WM"
        self.name = "Fake device"
        self._type_name = "WM"
        self.attributes: dict[str, Any] = {}
        self.settings: dict[str, Any] = {}
        self.commands: dict[str, Any] = {}

    def get(self, item: str, default: Any = None) -> Any:
        if item.startswith("attributes."):
            result: Any = self.attributes
            try:
                for key in item[len("attributes.") :].split("."):
                    result = result[key]
                return result
            except (KeyError, TypeError):
                return default
        return self._data.get(item, default)

    def getInt(self, item: str) -> int:
        return int(self._data.get(item, 0))

    def getFloat(self, item: str) -> float:
        return float(self._data.get(item, 0))

    def has(self, item: str) -> bool:
        return self.get(item) is not None

    def getProgramName(self) -> Any:
        return self._program_name

    def set(self, item: str, value: Any) -> None:
        self._data[item] = value

    def get_setting(self, key: str) -> Any:
        return self.settings.get(key)

    def has_current_setting(self, key: str) -> bool:
        return key in self.settings

    def start_command(self, program: Any = None, parameters: dict | None = None):
        command = MagicMock()
        command.send = AsyncMock(return_value=True)
        self._last_command = command
        return command

    def settings_command(self, parameters: dict | None = None):
        command = MagicMock()
        command.parameters = self.settings
        command.send = AsyncMock(return_value=True)
        self._last_command = command
        return command

    def stop_command(self, parameters: dict | None = None):
        command = MagicMock()
        command.send = AsyncMock(return_value=True)
        self._last_command = command
        return command


@pytest.fixture
def coordinator(hass, mock_connection, appliance) -> HonBaseCoordinator:
    """A coordinator wired to the mocked connection."""
    return HonBaseCoordinator(hass, mock_connection, appliance, timedelta(seconds=60))


@pytest.fixture
def make_device() -> Any:
    """Return a factory building :class:`FakeDevice` instances."""

    def _make(
        data: dict[str, Any] | None = None, program_name: Any = None
    ) -> FakeDevice:
        return FakeDevice(data, program_name)

    return _make


@pytest.fixture
def full_data() -> dict[str, Any]:
    """Device data covering every key read by the sensor classes."""
    return {
        "machMode": "1",
        "onOffStatus": "1",
        "temp": "40",
        "tempSel": "40",
        "humidity": "50",
        "humidityZ1": "50",
        "remainingTimeMM": "30",
        "delayTime": "5",
        "prCode": "5",
        "prPhase": "3",
        "prTime": "60",
        "dryLevel": "1",
        "totalWashCycle": "10",
        "totalWaterUsed": "100",
        "totalElectricityUsed": "5",
        "actualWeight": "5",
        "currentWaterUsed": "10",
        "currentElectricityUsed": "2",
        "errors": "E01",
        "spinSpeed": "800",
        "volume": "10",
        "displayedApp": "youtube",
        "currentWashCycle": "3",
        "detergentPercent": "80",
        "waterHard": "2",
        "power": "500",
        "totalWorkTime": "120",
        "preFilterStatus": "30",
        "mainFilterStatus": "40",
        "pm2p5ValueIndoor": "10",
        "pm10ValueIndoor": "20",
        "vocValueIndoor": "5",
        "coLevel": "3",
        "airQuality": "50",
        "windSpeed": "5",
        "quickModeZ1": "2",
        "remoteCtrValid": "1",
        "lockStatus": "0",
        "doorLockStatus": "0",
        "muteStatus": "1",
        "pause": "0",
        "doorStatus": "1",
        "lightStatus": "1",
        "preheatStatus": "1",
        "healthMode": "1",
        "doorStatusZ1": "1",
        "door2StatusZ1": "1",
        "statistics.programsCounter": "42",
    }
