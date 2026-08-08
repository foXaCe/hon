"""Tests for the hOn binary sensor entity classes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from homeassistant.components.binary_sensor import BinarySensorDeviceClass

if TYPE_CHECKING:
    from collections.abc import Callable


from custom_components.hon.devices.binary_sensor import (
    HonBaseBinarySensorEntity,
    HonBaseChildLockStatus,
    HonBaseDoor2Status,
    HonBaseDoorLockStatus,
    HonBaseDoorStatus,
    HonBaseGenericStatus,
    HonBaseHealthMode,
    HonBaseLightStatus,
    HonBaseMuteStatus,
    HonBaseOnOff,
    HonBasePauseStatus,
    HonBasePreheating,
    HonBaseRemoteControl,
)
from tests.conftest import MAC


def test_hon_base_binary_sensor_entity(coordinator, appliance, make_device) -> None:
    """The base binary sensor reads its key and derives the unique id."""
    coordinator._device = make_device({"doorStatus": "1"})
    entity = HonBaseBinarySensorEntity(coordinator, appliance, "doorStatus", "Door")

    assert entity.unique_id == f"{MAC}_door_status"
    assert entity.name == "Door"
    assert entity.is_on is True


def test_hon_base_binary_sensor_entity_off(coordinator, appliance, make_device) -> None:
    """A zero value maps to a False state."""
    coordinator._device = make_device({"doorStatus": "0"})
    entity = HonBaseBinarySensorEntity(coordinator, appliance, "doorStatus", "Door")
    assert entity.is_on is False


def test_hon_base_onoff(coordinator, appliance, make_device) -> None:
    """HonBaseOnOff reflects the power state."""
    coordinator._device = make_device({"onOffStatus": "1"})
    entity = HonBaseOnOff(None, coordinator, None, appliance)
    assert entity.device_class is BinarySensorDeviceClass.POWER
    assert entity.is_on is True


def test_hon_base_onoff_connected_fallback(coordinator, appliance, make_device) -> None:
    """HonBaseOnOff falls back to the connection category."""
    coordinator._device = make_device({})
    coordinator._device.attributes = {"lastConnEvent": {"category": "CONNECTED"}}
    entity = HonBaseOnOff(None, coordinator, None, appliance)
    assert entity.is_on is True


def test_hon_base_door_lock_status_inverted(
    coordinator, appliance, make_device
) -> None:
    """HonBaseDoorLockStatus is on when the lock is open."""
    coordinator._device = make_device({"doorLockStatus": "0"})
    entity = HonBaseDoorLockStatus(None, coordinator, None, appliance)
    assert entity.device_class is BinarySensorDeviceClass.LOCK
    assert entity.is_on is True


def test_hon_base_child_lock_status(coordinator, appliance, make_device) -> None:
    """HonBaseChildLockStatus is on when the child lock is off."""
    coordinator._device = make_device({"lockStatus": "0"})
    entity = HonBaseChildLockStatus(None, coordinator, None, appliance)
    assert entity.translation_key == "lockstatus"
    assert entity.device_class is BinarySensorDeviceClass.LOCK
    assert entity.is_on is True


def test_hon_base_child_lock_status_locked(coordinator, appliance, make_device) -> None:
    """HonBaseChildLockStatus is off while the child lock is active."""
    coordinator._device = make_device({"lockStatus": "1"})
    entity = HonBaseChildLockStatus(None, coordinator, None, appliance)
    assert entity.is_on is False


def test_hon_base_mute_status(coordinator, appliance, make_device) -> None:
    """HonBaseMuteStatus is on when muted."""
    coordinator._device = make_device({"muteStatus": "1"})
    entity = HonBaseMuteStatus(None, coordinator, None, appliance)
    assert entity.is_on is True


def test_hon_base_pause_status(coordinator, appliance, make_device) -> None:
    """HonBasePauseStatus is on when paused."""
    coordinator._device = make_device({"pause": "1"})
    entity = HonBasePauseStatus(None, coordinator, None, appliance)
    assert entity.is_on is True


def test_hon_base_generic_status(coordinator, appliance, make_device) -> None:
    """HonBaseGenericStatus binds a key to a device class."""
    coordinator._device = make_device({"defrostStatus": "1"})
    entity = HonBaseGenericStatus(
        None,
        coordinator,
        None,
        appliance,
        "defrostStatus",
        "Defrost",
        BinarySensorDeviceClass.RUNNING,
    )
    assert entity.device_class is BinarySensorDeviceClass.RUNNING
    assert entity.is_on is True


def test_hon_base_light_status(coordinator, appliance, make_device) -> None:
    """HonBaseLightStatus exposes its supported attributes."""
    coordinator._device = make_device({"lightStatus": "1"})
    entity = HonBaseLightStatus(None, coordinator, None, appliance)
    assert entity.device_class is BinarySensorDeviceClass.LIGHT
    assert "SET_LIGHT" in entity.supported_attributes


BINARY_BUILDERS: list[tuple[str, Callable[[Any, dict], Any]]] = [
    ("on_off", lambda c, a: HonBaseOnOff(None, c, None, a)),
    ("door_status", lambda c, a: HonBaseDoorStatus(None, c, None, a, "Z1", "zone 1")),
    ("door2_status", lambda c, a: HonBaseDoor2Status(None, c, None, a, "Z1", "zone 1")),
    ("light_status", lambda c, a: HonBaseLightStatus(None, c, None, a)),
    ("remote_control", lambda c, a: HonBaseRemoteControl(None, c, None, a)),
    ("door_lock_status", lambda c, a: HonBaseDoorLockStatus(None, c, None, a)),
    ("child_lock_status", lambda c, a: HonBaseChildLockStatus(None, c, None, a)),
    ("preheating", lambda c, a: HonBasePreheating(None, c, None, a)),
    ("health_mode", lambda c, a: HonBaseHealthMode(None, c, None, a)),
    ("mute_status", lambda c, a: HonBaseMuteStatus(None, c, None, a)),
    ("pause_status", lambda c, a: HonBasePauseStatus(None, c, None, a)),
]


@pytest.mark.parametrize(
    "name,builder",
    BINARY_BUILDERS,
    ids=[name for name, _ in BINARY_BUILDERS],
)
def test_binary_sensor_classes_smoke(
    coordinator, appliance, make_device, full_data, name: str, builder: Callable
) -> None:
    """Every binary sensor class constructs cleanly and updates."""
    coordinator._device = make_device(dict(full_data))
    entity = builder(coordinator, appliance)
    assert entity.unique_id.startswith(MAC)
    assert entity.name
    entity.coordinator_update()
    assert entity.is_on is not None
