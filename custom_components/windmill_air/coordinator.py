"""Data update coordinator for the Windmill Air Purifier."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import WindmillAirApi, WindmillApiError, WindmillAuthError
from .const import CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL, DOMAIN, LOGGER


@dataclass
class WindmillData:
    """Snapshot of the device state."""

    online: bool
    pins: dict[str, Any]


class WindmillCoordinator(DataUpdateCoordinator[WindmillData]):
    """Polls all datastream values from the Windmill cloud."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: WindmillAirApi
    ) -> None:
        interval = entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )
        self.api = api

    async def _async_update_data(self) -> WindmillData:
        try:
            online = await self.api.is_connected()
            pins = await self.api.get_all()
        except WindmillAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except WindmillApiError as err:
            raise UpdateFailed(str(err)) from err
        return WindmillData(online=online, pins=pins)

    def pin_value(self, pin: str | None) -> Any:
        """Return the last known value of a pin, or None."""
        if not pin or self.data is None:
            return None
        return self.data.pins.get(pin.lower())

    def set_pin_optimistic(self, pin: str, value: Any) -> None:
        """Update the local snapshot after a successful write."""
        if self.data is not None:
            self.data.pins[pin.lower()] = value
            self.async_update_listeners()
