"""Optional switches (child lock, display light) for the Windmill Air Purifier."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_CHILD_LOCK_PIN, CONF_DISPLAY_LIGHT_PIN, DOMAIN
from .coordinator import WindmillCoordinator
from .entity import WindmillEntity
from .util import as_bool


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WindmillCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    if pin := entry.options.get(CONF_CHILD_LOCK_PIN, ""):
        entities.append(
            WindmillSwitch(coordinator, pin, "child_lock", "Child lock", "mdi:lock")
        )
    if pin := entry.options.get(CONF_DISPLAY_LIGHT_PIN, ""):
        entities.append(
            WindmillSwitch(
                coordinator, pin, "display_light", "Display light", "mdi:lightbulb-on"
            )
        )
    async_add_entities(entities)


class WindmillSwitch(WindmillEntity, SwitchEntity):
    """An on/off toggle backed by one datastream."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: WindmillCoordinator,
        pin: str,
        suffix: str,
        name: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, suffix)
        self._pin = pin
        self._attr_name = name
        self._attr_icon = icon

    @property
    def is_on(self) -> bool | None:
        return as_bool(self.coordinator.pin_value(self._pin))

    async def _write(self, value: int) -> None:
        await self.coordinator.api.set_pin(self._pin, value)
        self.coordinator.set_pin_optimistic(self._pin, value)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._write(1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._write(0)
