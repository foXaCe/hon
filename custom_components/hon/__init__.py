"""hOn (Haier smart home) integration."""

from __future__ import annotations

import ast
import asyncio
import logging
from datetime import datetime

import voluptuous as vol
from dateutil.tz import gettz
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .api.client import HonConnection, get_hOn_mac
from .api.exceptions import HonAuthenticationError, HonConnectionError
from .const import DOMAIN, PLATFORMS

_LOGGER = logging.getLogger(__name__)
SERVICE_REGISTRY = "service_registry"


type HonConfigEntry = ConfigEntry[HonConnection]


HON_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
    }
)

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema(vol.All(cv.ensure_list, [HON_SCHEMA]))},
    extra=vol.ALLOW_EXTRA,
)


# This method will update a sensor value with the targetted one for a better user experience
def update_sensor(hass, device_id, mac, sensor_name, state):
    """Update the matching sensor with the given state."""

    entity_reg = er.async_get(hass)
    entries = er.async_entries_for_device(entity_reg, device_id)

    # Loop over all entries and update the good one
    for entry in entries:
        if entry.unique_id.endswith("_" + mac + "_" + sensor_name):
            inputStateObject = hass.states.get(entry.entity_id)
            hass.states.async_set(entry.entity_id, state, inputStateObject.attributes)


def get_parameters(call):
    """Parse the parameters string from a service call."""
    parameters_str = call.data.get("parameters", "{}")
    if type(parameters_str) != str:
        parameters_str = str(parameters_str)
    return ast.literal_eval(parameters_str)


def _minutes_until(target: datetime, now: datetime) -> int:
    """Return the number of whole minutes until the target time."""
    return max(0, int((target - now).total_seconds() / 60))


def get_device_ids(hass, call):
    """Return the target device ids from a service call."""
    device_ids = set(call.data.get("device_id", []))
    entity_ids = call.data.get("entity_id", [])

    ent_reg = er.async_get(hass)

    for entity_id in entity_ids:
        entry = ent_reg.async_get(entity_id)
        if entry and entry.device_id:
            device_ids.add(entry.device_id)

    return list(device_ids)


async def async_migrate_entry(hass: HomeAssistant, entry: HonConfigEntry) -> bool:
    """Migrate a config entry to a newer version.

    Version 2 prefixes every entity unique id with ``{entry.unique_id}_`` so
    that ids are namespaced per config entry (Quality Scale Gold format).
    """
    if entry.version != 1:
        return True

    _LOGGER.info(
        "Migrating %s config entry from version %s", entry.title, entry.version
    )

    registry = er.async_get(hass)
    uid_prefix = f"{entry.unique_id}_"

    @callback
    def update_unique_id(entity_entry: er.RegistryEntry) -> dict[str, str] | None:
        if entity_entry.unique_id.startswith(uid_prefix):
            return None
        return {"new_unique_id": f"{uid_prefix}{entity_entry.unique_id}"}

    await er.async_migrate_entries(hass, entry.entry_id, update_unique_id)
    hass.config_entries.async_update_entry(entry, version=2)
    _LOGGER.info("Migrated %s config entry to version 2", entry.title)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: HonConfigEntry) -> bool:
    """Set up the hOn integration for a config entry."""
    hon = HonConnection(hass, entry)
    try:
        result = await hon.async_authorize()
    except HonConnectionError as err:
        raise ConfigEntryNotReady(f"hOn connection failed: {err}") from err
    except HonAuthenticationError as err:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN, translation_key="auth_failed"
        ) from err
    if not result:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN, translation_key="auth_failed"
        )

    # Log the appliance count only (MAC addresses are identifiers)
    _LOGGER.debug("Appliances loaded: %d", len(hon.appliances))

    entry.runtime_data = hon

    # Load every appliance context in parallel to keep the boot fast.
    coordinators = [
        await hon.async_get_coordinator(appliance) for appliance in hon.appliances
    ]
    await asyncio.gather(
        *(
            coordinator.async_config_entry_first_refresh()
            for coordinator in coordinators
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _update_listener(hass: HomeAssistant, entry: HonConfigEntry) -> None:
        """Handle options update."""
        await hass.config_entries.async_reload(entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(_update_listener))

    async def handle_oven_start(call):

        delay_time = 0
        tz = gettz(hass.config.time_zone)

        if "start" in call.data:
            date = datetime.strptime(
                call.data.get("start"), "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=tz)
            delay_time = _minutes_until(date, datetime.now(tz))

        if "end" in call.data and "duration" in call.data:
            date = datetime.strptime(call.data.get("end"), "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=tz
            )
            duration = call.data.get("duration")
            delay_time = max(0, _minutes_until(date, datetime.now(tz)) - duration)

        parameters = {
            "delayTime": delay_time,
            "onOffStatus": "1",
            "prCode": call.data.get("program"),
            "prPosition": "1",
            "recipeId": "NULL",
            "recipeStep": "1",
            "prTime": call.data.get("duration", "0"),
            "tempSel": call.data.get("temperature"),
            "preheatStatus": "1" if call.data.get("preheat", False) else "0",
        }

        mac = get_hOn_mac(call.data.get("device"), hass)

        return await hon.async_set(mac, "OV", parameters)

    async def handle_dishwasher_start(call):

        delay_time = 0
        tz = gettz(hass.config.time_zone)

        if "start" in call.data:
            date = datetime.strptime(
                call.data.get("start"), "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=tz)
            delay_time = _minutes_until(date, datetime.now(tz))

        if "end" in call.data and "duration" in call.data:
            date = datetime.strptime(call.data.get("end"), "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=tz
            )
            duration = call.data.get("duration")
            delay_time = max(0, _minutes_until(date, datetime.now(tz)) - duration)

        parameters = {
            "delayTime": delay_time,
            "onOffStatus": "1",
            "prCode": call.data.get("program"),
            "prPosition": "1",
            "prTime": call.data.get("duration", "0"),
            #           "extraDry": "1" if call.data.get("extra_dry", False) else "0",
            #           "openDoor": "1" if call.data.get("open_door", False) else "0", ##conditional program
            #           "halfLoad": "1" if call.data.get("half_load", False) else "0", ##conditional programm
            #           "prStrDisp": call.data.get("string_display"),
        }

        mac = get_hOn_mac(call.data.get("device"), hass)

        return await hon.async_set(mac, "DW", parameters)

    async def handle_washingmachine_start(call):

        delay_time = 0
        tz = gettz(hass.config.time_zone)
        if "end" in call.data:
            date = datetime.strptime(call.data.get("end"), "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=tz
            )
            delay_time = _minutes_until(date, datetime.now(tz))

        parameters = {
            "haier_MainWashSpeed": "50",
            "creaseResistSoakStatus": "0",
            "haier_SoakPrewashSelection": "0",
            "prCode": "999",
            "soakWashStatus": "0",
            "strongStatus": "0",
            "energySavingStatus": "0",
            "spinSpeed": call.data.get("spinSpeed", "400"),
            "haier_MainWashWaterLevel": "2",
            "rinseIterationTime": "8",
            "haier_SoakPrewashSpeed": "0",
            "permanentPressStatus": "1",
            "nightWashStatus": "0",
            "intelligenceStatus": "0",
            "haier_SoakPrewashStopTime": "0",
            "weight": "5",
            "highWaterLevelStatus": "0",
            "voiceStatus": "0",
            "haier_SoakPrewashTime": "0",
            "autoDisinfectantStatus": "0",
            "cloudProgSrc": "2",
            "haier_SoakPrewashRotateTime": "0",
            "cloudProgId": "255",
            "haier_SoakPrewashTemperature": "0",
            "dryProgFlag": "0",
            "dryLevel": "0",
            "haier_RinseRotateTime": "20",
            "uvSterilizationStatus": "0",
            "dryTime": "0",
            "delayStatus": "0",
            "dryLevelAllowed": "0",
            "rinseIterations": call.data.get("rinseIterations", "2"),
            "lockStatus": "0",
            "mainWashTime": call.data.get("mainWashTime", "15"),
            "autoSoftenerStatus": call.data.get("autoSoftenerStatus", "0"),
            "washerDryIntensity": "1",
            "autoDetergentStatus": "0",
            "antiAllergyStatus": "0",
            "speedUpStatus": "0",
            "temp": call.data.get("temp", "30"),
            "haier_MainWashRotateTime": "20",
            "detergentBStatus": "0",
            "haier_MainWashStopTime": "5",
            "texture": "1",
            "operationName": "grOnlineWash",
            "haier_RinseSpeed": "50",
            "haier_ConstantTempStatus": "1",
            "haier_RinseStopTime": "5",
            "delayTime": delay_time,
        }

        mac = get_hOn_mac(call.data.get("device"), hass)

        coordinator = await hon.async_get_existing_coordinator(mac)
        if (
            coordinator is None
            or coordinator.device.get("attributes.lastConnEvent.category")
            == "DISCONNECTED"
        ):
            _LOGGER.error("This hOn device is disconnected")
            return

        return await hon.async_set(mac, "WM", parameters)

    async def handle_purifier_start(call):

        parameters = {
            "onOffStatus": "1",
            "machMode": "2",
        }

        mac = get_hOn_mac(call.data.get("device"), hass)

        return await hon.async_set(mac, "AP", parameters)

    async def handle_purifier_maxmode(call):

        parameters = {"machMode": "4"}

        mac = get_hOn_mac(call.data.get("device"), hass)

        return await hon.async_set(mac, "AP", parameters)

    async def handle_purifier_automode(call):

        parameters = {"machMode": "2"}

        mac = get_hOn_mac(call.data.get("device"), hass)

        return await hon.async_set(mac, "AP", parameters)

    async def handle_purifier_sleepmode(call):
        parameters = {"machMode": "1"}
        mac = get_hOn_mac(call.data.get("device"), hass)
        return await hon.async_set(mac, "AP", parameters)

    # Generic method to set a mode to any hOn device
    async def handle_set_mode(call):
        # parameters = {"onOffStatus": "1", "machMode": call.data.get("mode", 1)}
        # return await hon.async_set_parameter(call.data.get("device_id")[0], parameters)
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)
        coordinator = await hon.async_get_existing_coordinator(mac)
        parameters = {"onOffStatus": "1", "machMode": call.data.get("mode", 1)}
        await coordinator.async_set(parameters)
        await coordinator.async_request_refresh()

    # Generic method to TURN OFF any hOn device
    async def handle_turn_off(call):
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)

        coordinator = await hon.async_get_existing_coordinator(mac)
        parameters = {"onOffStatus": "0", "machMode": "1"}
        await coordinator.async_set(parameters)
        await coordinator.async_request_refresh()

    async def handle_oven_off(call):
        parameters = {"onOffStatus": "0", "prPosition": "0", "prCode": "0"}
        mac = get_hOn_mac(call.data.get("device"), hass)
        return await hon.async_set(mac, "OV", parameters)

    async def handle_washingmachine_off(call):
        mac = get_hOn_mac(call.data.get("device"), hass)
        return await hon.async_set(mac, "WM", {"onOffStatus": "0"})

    async def handle_purifier_off(call):
        parameters = {"onOffStatus": "0", "machMode": "1"}
        mac = get_hOn_mac(call.data.get("device"), hass)
        return await hon.async_set(mac, "AP", parameters)

    async def handle_light_on(call):
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)

        update_sensor(hass, device_id, mac, "light_status", "on")
        coordinator = await hon.async_get_existing_coordinator(mac)
        await coordinator.async_set({"lightStatus": "1"})
        await coordinator.async_request_refresh()

    async def handle_light_off(call):
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)
        update_sensor(hass, device_id, mac, "light_status", "off")

        coordinator = await hon.async_get_existing_coordinator(mac)
        await coordinator.async_set({"lightStatus": "0"})
        await coordinator.async_request_refresh()

    async def handle_health_mode_on(call):
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)
        update_sensor(hass, device_id, mac, "health_mode", "on")

        coordinator = await hon.async_get_existing_coordinator(mac)
        await coordinator.async_set({"healthMode": "1"})
        await coordinator.async_request_refresh()

    async def handle_health_mode_off(call):
        device_id = call.data.get("device")
        mac = get_hOn_mac(device_id, hass)
        update_sensor(hass, device_id, mac, "health_mode", "off")

        coordinator = await hon.async_get_existing_coordinator(mac)
        await coordinator.async_set({"healthMode": "0"})
        await coordinator.async_request_refresh()

    async def handle_start_program(call):
        device_ids = get_device_ids(hass, call)

        for device_id in device_ids:
            device = hon.get_device(hass, device_id)
            command = device.commands.get("startProgram")
            programs = command.get_programs()
            program = call.data.get("program")
            if program not in programs.keys():
                keys = ", ".join(programs)
                raise HomeAssistantError(
                    f"Invalid [Program] value, allowed values [{keys}]"
                )

            parameters = get_parameters(call)
            await device.start_command(program, parameters).send()

    async def handle_custom_request(call):
        device_ids = get_device_ids(hass, call)
        parameters = get_parameters(call)
        for device_id in device_ids:
            device = hon.get_device(hass, device_id)
            await device.coordinator.async_set(parameters)
            await device.coordinator.async_request_refresh()

    async def handle_update_settings(call):
        # device_ids = call.data.get("device_id", [])
        # entity_ids = call.data.get("entity_id", [])
        # for entity_id in entity_ids:
        #    device_ids.append(get_device_id(hass, entity_id))
        # device_ids = list(dict.fromkeys(device_ids))
        device_ids = get_device_ids(hass, call)
        parameters = get_parameters(call)

        for device_id in device_ids:
            device = hon.get_device(hass, device_id)
            await device.settings_command(parameters).send()

    async def async_get_setting(call: ServiceCall):
        """Handle the get_setting service call."""
        parameter = call.data.get("parameter")
        device_ids = get_device_ids(hass, call)

        results = {}

        for device_id in device_ids:
            device = hon.get_device(hass, device_id)
            results[device_id] = device.get(parameter)

        _LOGGER.debug("get_setting results: %s", results)
        hass.bus.async_fire("hon_get_setting_result", {"results": results})
        return results

    services = {
        "turn_on_washingmachine": handle_washingmachine_start,
        "turn_off_washingmachine": handle_washingmachine_off,
        "turn_on_oven": handle_oven_start,
        "turn_off_oven": handle_oven_off,
        "turn_on_dishwasher": handle_dishwasher_start,
        "turn_on_purifier": handle_purifier_start,
        "turn_off_purifier": handle_purifier_off,
        "set_auto_mode_purifier": handle_purifier_automode,
        "set_sleep_mode_purifier": handle_purifier_sleepmode,
        "set_max_mode_purifier": handle_purifier_maxmode,
        "set_mode": handle_set_mode,
        "turn_off": handle_turn_off,
        "turn_light_on": handle_light_on,
        "turn_light_off": handle_light_off,
        "send_custom_request": handle_custom_request,
        "climate_turn_health_mode_on": handle_health_mode_on,
        "climate_turn_health_mode_off": handle_health_mode_off,
        "start_program": handle_start_program,
        "update_settings": handle_update_settings,
        "get_setting": async_get_setting,
    }

    registered_services = hass.data.setdefault(DOMAIN, {}).setdefault(
        SERVICE_REGISTRY, set()
    )
    for service_name, handler in services.items():
        if service_name in registered_services:
            continue
        hass.services.async_register(
            domain=DOMAIN,
            service=service_name,
            service_func=handler,
            schema=None,
        )
        registered_services.add(service_name)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: HonConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    hon = entry.runtime_data
    await hon.async_close()

    return True
