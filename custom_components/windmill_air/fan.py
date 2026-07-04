"""Fan entity for the Windmill Air Purifier.

The purifier exposes a single "mode" datastream (V3 by default) that holds
both the numbered fan speeds and the special Eco / Sleep values:

    1..speed_count -> fan speed levels        -> percentage slider
    MODE_ECO (5)   -> Eco                      -> preset
    MODE_SLEEP (6) -> Sleep                    -> preset, with a sub-mode pin
                                                  (V4: Whisper / White noise)
"""

from __future__ import annotations

import math
from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .const import (
    CONF_MODE_PIN,
    CONF_POWER_PIN,
    CONF_SLEEP_SUBMODE_PIN,
    CONF_SPEED_COUNT,
    DEFAULT_MODE_PIN,
    DEFAULT_POWER_PIN,
    DEFAULT_SLEEP_SUBMODE_PIN,
    DEFAULT_SPEED_COUNT,
    DOMAIN,
    MODE_ECO,
    MODE_SLEEP,
    PRESET_ECO,
    PRESET_SLEEP_WHISPER,
    PRESET_SLEEP_WHITE_NOISE,
    SLEEP_WHISPER,
    SLEEP_WHITE_NOISE,
)
from .coordinator import WindmillCoordinator
from .entity import WindmillEntity
from .util import as_bool, as_int


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WindmillCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WindmillFan(coordinator)])


class WindmillFan(WindmillEntity, FanEntity):
    """The purifier: power, 4 fan speeds, and Eco / Sleep presets."""

    _attr_name = None  # takes the device name
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, coordinator: WindmillCoordinator) -> None:
        super().__init__(coordinator, "fan")
        options = coordinator.config_entry.options
        self._power_pin: str = options.get(CONF_POWER_PIN, DEFAULT_POWER_PIN)
        self._mode_pin: str = options.get(CONF_MODE_PIN, DEFAULT_MODE_PIN)
        self._submode_pin: str = options.get(
            CONF_SLEEP_SUBMODE_PIN, DEFAULT_SLEEP_SUBMODE_PIN
        )
        self._speed_count: int = int(
            options.get(CONF_SPEED_COUNT, DEFAULT_SPEED_COUNT)
        )

        self._attr_supported_features = (
            FanEntityFeature.TURN_ON
            | FanEntityFeature.TURN_OFF
            | FanEntityFeature.SET_SPEED
            | FanEntityFeature.PRESET_MODE
        )
        presets = [PRESET_ECO]
        if self._submode_pin:
            presets += [PRESET_SLEEP_WHISPER, PRESET_SLEEP_WHITE_NOISE]
        self._attr_preset_modes = presets

    @property
    def speed_count(self) -> int:
        return self._speed_count

    def _mode(self) -> int | None:
        return as_int(self.coordinator.pin_value(self._mode_pin))

    @property
    def is_on(self) -> bool | None:
        return as_bool(self.coordinator.pin_value(self._power_pin))

    @property
    def percentage(self) -> int | None:
        if self.is_on is False:
            return 0
        mode = self._mode()
        if mode is None:
            return None
        if 1 <= mode <= self._speed_count:
            return ranged_value_to_percentage((1, self._speed_count), mode)
        # Eco / Sleep are presets, not numbered speeds.
        return None

    @property
    def preset_mode(self) -> str | None:
        if self.is_on is False:
            return None
        mode = self._mode()
        if mode == MODE_ECO:
            return PRESET_ECO
        if mode == MODE_SLEEP:
            if not self._submode_pin:
                return None
            sub = as_int(self.coordinator.pin_value(self._submode_pin))
            if sub == SLEEP_WHITE_NOISE:
                return PRESET_SLEEP_WHITE_NOISE
            return PRESET_SLEEP_WHISPER
        return None

    async def _write(self, pin: str, value: Any) -> None:
        await self.coordinator.api.set_pin(pin, value)
        self.coordinator.set_pin_optimistic(pin, value)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        await self._write(self._power_pin, 1)
        if preset_mode is not None:
            await self.async_set_preset_mode(preset_mode)
        elif percentage is not None:
            await self.async_set_percentage(percentage)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._write(self._power_pin, 0)
        await self.coordinator.async_request_refresh()

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return
        if self.is_on is False:
            await self._write(self._power_pin, 1)
        # Writing a numbered speed to the mode pin leaves Eco / Sleep.
        level = math.ceil(
            percentage_to_ranged_value((1, self._speed_count), percentage)
        )
        await self._write(self._mode_pin, level)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if self.is_on is False:
            await self._write(self._power_pin, 1)
        if preset_mode == PRESET_ECO:
            await self._write(self._mode_pin, MODE_ECO)
        elif preset_mode == PRESET_SLEEP_WHISPER:
            await self._write(self._mode_pin, MODE_SLEEP)
            if self._submode_pin:
                await self._write(self._submode_pin, SLEEP_WHISPER)
        elif preset_mode == PRESET_SLEEP_WHITE_NOISE:
            await self._write(self._mode_pin, MODE_SLEEP)
            if self._submode_pin:
                await self._write(self._submode_pin, SLEEP_WHITE_NOISE)
        await self.coordinator.async_request_refresh()
