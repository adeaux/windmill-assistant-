"""Constants for the Windmill Air Purifier integration."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "windmill_air"
NAME = "Windmill Air Purifier"

# Windmill runs its cloud on a white-labeled Blynk server.
BASE_URL = "https://dashboard.windmillair.com"

CONF_TOKEN = "token"

# --- Pin-mapping options -------------------------------------------------
# All pin values are Blynk datastream names like "v3"; an empty string
# disables the corresponding entity.
CONF_POWER_PIN = "power_pin"
# The mode pin holds the fan speed (1..speed_count) AND the special Eco /
# Sleep values, so it drives both the speed slider and the presets.
CONF_MODE_PIN = "mode_pin"
CONF_SPEED_COUNT = "speed_count"
# Sub-mode pin, only meaningful while the mode pin is set to Sleep.
CONF_SLEEP_SUBMODE_PIN = "sleep_submode_pin"
CONF_AQI_PIN = "aqi_pin"
CONF_PM25_PIN = "pm25_pin"
CONF_CHILD_LOCK_PIN = "child_lock_pin"
CONF_LED_FADE_PIN = "led_fade_pin"
CONF_BEEP_PIN = "beep_pin"
CONF_UPDATE_INTERVAL = "update_interval"

# --- Defaults (discovered on the Windmill Air Purifier) ------------------
DEFAULT_POWER_PIN = "v0"
DEFAULT_MODE_PIN = "v3"
DEFAULT_SPEED_COUNT = 4
DEFAULT_SLEEP_SUBMODE_PIN = "v4"
DEFAULT_AQI_PIN = ""  # unconfirmed on this hardware; map it via Configure
DEFAULT_CHILD_LOCK_PIN = "v11"
DEFAULT_LED_FADE_PIN = "v5"
DEFAULT_BEEP_PIN = "v6"
DEFAULT_UPDATE_INTERVAL = 30

# --- Mode-pin enum values (device firmware behavior) ---------------------
MODE_ECO = 5
MODE_SLEEP = 6
# Sleep sub-mode values on CONF_SLEEP_SUBMODE_PIN.
SLEEP_WHISPER = 1
SLEEP_WHITE_NOISE = 2

PRESET_ECO = "Eco"
PRESET_SLEEP_WHISPER = "Sleep: Whisper"
PRESET_SLEEP_WHITE_NOISE = "Sleep: White noise"
