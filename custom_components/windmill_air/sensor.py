"""Sensors for the Windmill Air Purifier.

Besides the mapped AQI / PM2.5 sensors, every datastream reported by the cloud
that is not mapped to another entity is exposed as a diagnostic sensor. Watch
those while pressing buttons in the Windmill app to work out the pin mapping,
then assign pins in the integration options.
"""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONCENTRATION_MICROGRAMS_PER_CUBIC_METER, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_AQI_PIN,
    CONF_AUTO_PIN,
    CONF_CHILD_LOCK_PIN,
    CONF_DISPLAY_LIGHT_PIN,
    CONF_FAN_SPEED_PIN,
    CONF_PM25_PIN,
    CONF_POWER_PIN,
    CONF_SLEEP_PIN,
    DEFAULT_AQI_PIN,
    DEFAULT_FAN_SPEED_PIN,
    DEFAULT_POWER_PIN,
    DOMAIN,
)
from .coordinator import WindmillCoordinator
from .entity import WindmillEntity
from .util import as_float


def _mapped_pins(entry: ConfigEntry) -> set[str]:
    options = entry.options
    pins = {
        options.get(CONF_POWER_PIN, DEFAULT_POWER_PIN),
        options.get(CONF_FAN_SPEED_PIN, DEFAULT_FAN_SPEED_PIN),
        options.get(CONF_AQI_PIN, DEFAULT_AQI_PIN),
        options.get(CONF_PM25_PIN, ""),
        options.get(CONF_AUTO_PIN, ""),
        options.get(CONF_SLEEP_PIN, ""),
        options.get(CONF_CHILD_LOCK_PIN, ""),
        options.get(CONF_DISPLAY_LIGHT_PIN, ""),
    }
    return {p.lower() for p in pins if p}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WindmillCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    aqi_pin = entry.options.get(CONF_AQI_PIN, DEFAULT_AQI_PIN)
    if aqi_pin:
        entities.append(
            WindmillValueSensor(
                coordinator,
                pin=aqi_pin,
                suffix="aqi",
                name="Air quality index",
                device_class=SensorDeviceClass.AQI,
            )
        )
    pm25_pin = entry.options.get(CONF_PM25_PIN, "")
    if pm25_pin:
        entities.append(
            WindmillValueSensor(
                coordinator,
                pin=pm25_pin,
                suffix="pm25",
                name="PM2.5",
                device_class=SensorDeviceClass.PM25,
                unit=CONCENTRATION_MICROGRAMS_PER_CUBIC_METER,
            )
        )

    mapped = _mapped_pins(entry)
    if coordinator.data is not None:
        entities.extend(
            WindmillPinSensor(coordinator, pin)
            for pin in sorted(coordinator.data.pins)
            if pin not in mapped
        )

    async_add_entities(entities)


class WindmillValueSensor(WindmillEntity, SensorEntity):
    """A numeric sensor backed by one datastream."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: WindmillCoordinator,
        pin: str,
        suffix: str,
        name: str,
        device_class: SensorDeviceClass | None = None,
        unit: str | None = None,
    ) -> None:
        super().__init__(coordinator, suffix)
        self._pin = pin
        self._attr_name = name
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> float | int | None:
        value = as_float(self.coordinator.pin_value(self._pin))
        if value is not None and value.is_integer():
            return int(value)
        return value


class WindmillPinSensor(WindmillEntity, SensorEntity):
    """Diagnostic sensor exposing the raw value of an unmapped datastream."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: WindmillCoordinator, pin: str) -> None:
        super().__init__(coordinator, f"pin_{pin}")
        self._pin = pin
        self._attr_name = f"Pin {pin.upper()}"

    @property
    def native_value(self) -> str | None:
        value = self.coordinator.pin_value(self._pin)
        return None if value is None else str(value)
