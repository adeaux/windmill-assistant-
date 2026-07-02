"""Fan entity for the Windmill Air Purifier."""

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
    CONF_AUTO_PIN,
    CONF_FAN_SPEED_PIN,
    CONF_POWER_PIN,
    CONF_SLEEP_PIN,
    CONF_SPEED_COUNT,
    DEFAULT_FAN_SPEED_PIN,
    DEFAULT_POWER_PIN,
    DEFAULT_SPEED_COUNT,
    DOMAIN,
    PRESET_AUTO,
    PRESET_SLEEP,
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
    """The purifier itself: power, speed and (optionally) preset modes."""

    _attr_name = None  # takes the device name
    _enable_turn_on_off_backwards_compatibility = False

    def __init__(self, coordinator: WindmillCoordinator) -> None:
        super().__init__(coordinator, "fan")
        options = coordinator.config_entry.options
        self._power_pin: str = options.get(CONF_POWER_PIN, DEFAULT_POWER_PIN)
        self._speed_pin: str = options.get(CONF_FAN_SPEED_PIN, DEFAULT_FAN_SPEED_PIN)
        self._auto_pin: str = options.get(CONF_AUTO_PIN, "")
        self._sleep_pin: str = options.get(CONF_SLEEP_PIN, "")
        self._speed_count: int = int(
            options.get(CONF_SPEED_COUNT, DEFAULT_SPEED_COUNT)
        )

        features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        if self._speed_pin:
            features |= FanEntityFeature.SET_SPEED
        presets = []
        if self._auto_pin:
            presets.append(PRESET_AUTO)
        if self._sleep_pin:
            presets.append(PRESET_SLEEP)
        if presets:
            features |= FanEntityFeature.PRESET_MODE
            self._attr_preset_modes = presets
        self._attr_supported_features = features

    @property
    def speed_count(self) -> int:
        return self._speed_count

    @property
    def is_on(self) -> bool | None:
        return as_bool(self.coordinator.pin_value(self._power_pin))

    @property
    def percentage(self) -> int | None:
        if self.is_on is False:
            return 0
        level = as_int(self.coordinator.pin_value(self._speed_pin))
        if level is None:
            return None
        if level <= 0:
            return 0
        return ranged_value_to_percentage((1, self._speed_count), level)

    @property
    def preset_mode(self) -> str | None:
        if self._auto_pin and as_bool(self.coordinator.pin_value(self._auto_pin)):
            return PRESET_AUTO
        if self._sleep_pin and as_bool(self.coordinator.pin_value(self._sleep_pin)):
            return PRESET_SLEEP
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
        # Manual speed cancels auto/sleep presets when those pins are mapped.
        if self._auto_pin:
            await self._write(self._auto_pin, 0)
        if self._sleep_pin:
            await self._write(self._sleep_pin, 0)
        level = math.ceil(
            percentage_to_ranged_value((1, self._speed_count), percentage)
        )
        await self._write(self._speed_pin, level)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        if self.is_on is False:
            await self._write(self._power_pin, 1)
        if preset_mode == PRESET_AUTO:
            await self._write(self._auto_pin, 1)
            if self._sleep_pin:
                await self._write(self._sleep_pin, 0)
        elif preset_mode == PRESET_SLEEP:
            await self._write(self._sleep_pin, 1)
            if self._auto_pin:
                await self._write(self._auto_pin, 0)
        await self.coordinator.async_request_refresh()
