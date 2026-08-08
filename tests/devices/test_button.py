"""Tests for the hOn button entity classes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.hon.devices.button import (
    HonBaseButtonEntity,
    HonBaseSettingsButtonEntity,
)
from tests.conftest import MAC


def make_command(dump=("text", "{}")) -> MagicMock:
    """Build a command mock with the button API."""
    command = MagicMock()
    command.get_programs.return_value = {"eco": MagicMock()}
    command.dump.return_value = dump
    return command


async def test_hon_base_button_entity(coordinator, appliance, make_device) -> None:
    """The start button dumps a notification per program."""
    command = make_command()
    coordinator._device = make_device({})
    coordinator._device.commands = {"startProgram": command}
    entity = HonBaseButtonEntity(coordinator, appliance)

    assert entity.unique_id == f"{MAC}_start_button"
    assert entity.translation_key == "start_button"
    await entity.async_press()
    command.set_program.assert_called_once_with("eco")
    command.dump.assert_called()


async def test_hon_base_button_entity_no_commands(
    coordinator, appliance, make_device
) -> None:
    """Without a start program the button press raises."""
    coordinator._device = make_device({})
    coordinator._device.commands = {}
    entity = HonBaseButtonEntity(coordinator, appliance)
    with pytest.raises(AttributeError):
        await entity.async_press()


async def test_hon_base_settings_button_entity(
    coordinator, appliance, make_device
) -> None:
    """The settings button dumps a single notification."""
    command = make_command()
    coordinator._device = make_device({})
    coordinator._device.commands = {"settings": command}
    entity = HonBaseSettingsButtonEntity(coordinator, appliance)

    assert entity.unique_id == f"{MAC}_settings_button"
    assert entity.translation_key == "settings_button"
    await entity.async_press()
    command.dump.assert_called_once()


def test_button_device_info(coordinator, appliance, make_device) -> None:
    """The button device_info is delegated to the device."""
    coordinator._device = make_device({})
    info = {"identifiers": {("hon", MAC, "WM")}}
    coordinator._device.device_info = info
    entity = HonBaseButtonEntity(coordinator, appliance)
    assert entity.device_info == info


async def test_hon_base_button_entity_registry_device_id(
    coordinator, appliance, make_device, hass, config_entry
) -> None:
    """The start button resolves the device id from the registry."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={("hon", MAC, "WM")},
    )
    entry = er.async_get(hass).async_get_or_create(
        "button",
        "hon",
        "unique",
        config_entry=config_entry,
        device_id=device.id,
        suggested_object_id="hon_start",
    )
    command = make_command()
    coordinator._device = make_device({})
    coordinator._device.commands = {"startProgram": command}
    entity = HonBaseButtonEntity(coordinator, appliance)
    entity.entity_id = entry.entity_id
    await entity.async_press()
    command.dump.assert_called()


def test_hon_base_settings_button_device_info(
    coordinator, appliance, make_device
) -> None:
    """The settings button device_info is delegated to the device."""
    coordinator._device = make_device({})
    info = {"identifiers": {("hon", MAC, "WM")}}
    coordinator._device.device_info = info
    entity = HonBaseSettingsButtonEntity(coordinator, appliance)
    assert entity.device_info == info


async def test_hon_base_settings_button_registry_device_id(
    coordinator, appliance, make_device, hass, config_entry
) -> None:
    """The settings button resolves the device id from the registry."""
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er

    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={("hon", MAC, "WM")},
    )
    entry = er.async_get(hass).async_get_or_create(
        "button",
        "hon",
        "settings-unique",
        config_entry=config_entry,
        device_id=device.id,
        suggested_object_id="hon_settings",
    )
    command = make_command()
    coordinator._device = make_device({})
    coordinator._device.commands = {"settings": command}
    entity = HonBaseSettingsButtonEntity(coordinator, appliance)
    entity.entity_id = entry.entity_id
    await entity.async_press()
    command.dump.assert_called_once()


async def test_button_notification_in_french(
    hass, coordinator, appliance, make_device
) -> None:
    """The notification text is localized in French with translated title."""
    command = make_command()
    coordinator._device = make_device({})
    coordinator._device.commands = {"startProgram": command}
    coordinator._device._type_name = "TD"
    entity = HonBaseButtonEntity(coordinator, appliance)

    created = []
    with (
        patch(
            "custom_components.hon.devices.button.async_get_cached_translations",
            return_value={"component.hon.entity.sensor.programs_td.state.eco": "Éco"},
        ),
        patch(
            "custom_components.hon.devices.button.create",
            side_effect=lambda hass, text, title: created.append((text, title)),
        ),
    ):
        await entity.async_press()

    assert created, "une notification doit être créée"
    text, title = created[0]
    assert "Paramètres" in text
    assert "program: eco" in text  # la valeur du programme reste brute
    assert title == "Programme [Éco]"
