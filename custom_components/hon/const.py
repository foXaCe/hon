"""hOn component constants."""

from __future__ import annotations

from enum import IntEnum

from homeassistant.components.climate.const import (
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
    FAN_OFF,
    HVACMode,
)

DOMAIN = "hon"


CONF_ID_TOKEN = "token"
CONF_COGNITO_TOKEN = "cognito_token"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_FRAMEWORK = "framework"

CONF_UPDATE_INTERVAL = "update_interval"
DEFAULT_SCAN_INTERVAL = 60

PLATFORMS = [
    "climate",
    "water_heater",
    "sensor",
    "binary_sensor",
    "button",
    "switch",
    "number",
    "select",
]


AUTH_API = "https://account2.hon-smarthome.com/SmartHome"
API_URL = "https://api-iot.he.services"
APP_VERSION = "2.27.9"
OS_VERSION = 31
OS = "android"
DEVICE_MODEL = "exynos9820"


class APPLIANCE_TYPE(IntEnum):
    """Appliance type identifiers used by the hOn API."""

    WASHING_MACHINE = (1,)
    WASH_DRYER = (2,)
    OVEN = (4,)
    WATER_HEATER = (10,)
    WINE_COOLER = (6,)
    PURIFIER = (7,)
    TUMBLE_DRYER = (8,)
    DISH_WASHER = (9,)
    CLIMATE = (11,)
    FRIDGE = (14,)
    TV = (25,)
    AIR_TO_WATER = 27


APPLIANCE_DEFAULT_NAME = {
    "1": "Washing Machine",
    "2": "Wash Dryer",
    "4": "Oven",
    "10": "Water Heater",
    "6": "Wine Cooler",
    "7": "Purifier",
    "8": "Tumble Dryer",
    "9": "Dish Washer",
    "11": "Climate",
    "14": "Fridge",
    "25": "TV",
    "27": "Air to Water",
}

# Appliance families that expose multi-program start helpers.
PROGRAM_HELPER_APPLIANCE_TYPES = {
    APPLIANCE_TYPE.OVEN,
    APPLIANCE_TYPE.DISH_WASHER,
}

CLIMATE_FAN_MODE = {
    FAN_OFF: "0",
    FAN_LOW: "3",
    FAN_MEDIUM: "2",
    FAN_HIGH: "1",
    FAN_AUTO: "5",
}

CLIMATE_HVAC_MODE = {
    HVACMode.AUTO: "0",
    HVACMode.COOL: "1",
    HVACMode.HEAT: "4",
    HVACMode.DRY: "2",
    HVACMode.FAN_ONLY: "6",
}


class ClimateSwingVertical:
    """Vertical swing positions for climate devices."""

    AUTO = "8"
    VERY_LOW = "7"
    LOW = "6"
    MIDDLE = "5"
    HIGH = "4"
    HEALTH_LOW = "3"
    VERY_HIGH = "2"
    HEALTH_HIGH = "1"


class ClimateSwingHorizontal:
    """Horizontal swing positions for climate devices."""

    AUTO = "7"
    MIDDLE = "0"
    FAR_LEFT = "3"
    LEFT = "4"
    RIGHT = "5"
    FAR_RIGHT = "6"


class ClimateEcoPilotMode:
    """Eco pilot modes for climate devices."""

    OFF = "0"
    AVOID = "1"
    FOLLOW = "2"
