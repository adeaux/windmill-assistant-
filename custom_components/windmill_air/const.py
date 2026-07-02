"""Constants for the Windmill Air Purifier integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "windmill_air"
NAME = "Windmill Air Purifier"

# Windmill runs its cloud on a white-labeled Blynk server.
BASE_URL = "https://dashboard.windmillair.com"

CONF_TOKEN = "token"

# Options (all pin values are datastream names like "v0"; empty string disables
# the corresponding entity).
CONF_POWER_PIN = "power_pin"
CONF_FAN_SPEED_PIN = "fan_speed_pin"
CONF_SPEED_COUNT = "speed_count"
CONF_AUTO_PIN = "auto_pin"
CONF_SLEEP_PIN = "sleep_pin"
CONF_AQI_PIN = "aqi_pin"
CONF_PM25_PIN = "pm25_pin"
CONF_CHILD_LOCK_PIN = "child_lock_pin"
CONF_DISPLAY_LIGHT_PIN = "display_light_pin"
CONF_UPDATE_INTERVAL = "update_interval"

DEFAULT_POWER_PIN = "v0"
DEFAULT_FAN_SPEED_PIN = "v1"
DEFAULT_AQI_PIN = "v2"
DEFAULT_SPEED_COUNT = 5
DEFAULT_UPDATE_INTERVAL = 30

PRESET_AUTO = "Auto"
PRESET_SLEEP = "Sleep"
