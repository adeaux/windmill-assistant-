"""Base entity for the Windmill Air Purifier."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, NAME
from .coordinator import WindmillCoordinator


class WindmillEntity(CoordinatorEntity[WindmillCoordinator]):
    """Base entity tied to one Windmill device (one token = one device)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: WindmillCoordinator, suffix: str) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        model = coordinator.model
        self._attr_unique_id = f"{entry_id}_{suffix}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=coordinator.config_entry.title or NAME,
            manufacturer="Windmill",
            model=model.name,
            model_id=model.model_number or None,
        )

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.data is not None
            and self.coordinator.data.online
        )
