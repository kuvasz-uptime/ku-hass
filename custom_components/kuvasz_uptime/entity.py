"""Base entity for Kuvasz monitors."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import KuvaszCoordinator
from .monitor_types import MONITOR_TYPES_BY_KEY


class KuvaszMonitorEntity(CoordinatorEntity[KuvaszCoordinator]):
    """Base class for all Kuvasz monitor entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: KuvaszCoordinator,
        monitor: dict[str, Any],
    ) -> None:
        """Initialize the entity from a coordinator and monitor data dict."""
        super().__init__(coordinator)
        self._monitor_id: int = monitor["id"]
        self._monitor_type: str = monitor["_type"]
        self._monitor_name: str = monitor["name"]

    def _build_unique_id(self, key: str) -> str:
        """Return a globally unique entity ID scoped to this config entry."""
        return (
            f"{DOMAIN}_{self._instance_key}"
            f"_{self._monitor_type}_{self._monitor_id}_{key}"
        )

    def _build_entity_id(self, platform: str, key: str) -> str:
        name_slug = slugify(self._monitor_name)
        return f"{platform}.kuvasz_{self._monitor_type}_{name_slug}_{key}"

    @property
    def _monitor_data(self) -> dict[str, Any]:
        for m in self.coordinator.data.monitors:
            if m["id"] == self._monitor_id and m["_type"] == self._monitor_type:
                return m
        return {}

    @property
    def _monitor_stats(self) -> dict[str, Any]:
        return self.coordinator.data.monitor_stats(self._monitor_type, self._monitor_id)

    @property
    def _instance_key(self) -> str:
        """Return a unique prefix for this config entry, scoping all identifiers."""
        return self.coordinator.entry_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this monitor."""
        spec = MONITOR_TYPES_BY_KEY.get(self._monitor_type)
        type_label = spec.device_label if spec else self._monitor_type.upper()
        monitor_ident = f"{self._instance_key}_{self._monitor_type}_{self._monitor_id}"
        return DeviceInfo(
            identifiers={(DOMAIN, monitor_ident)},
            name=self._monitor_name,
            manufacturer="Kuvasz Uptime",
            model=f"{type_label} Monitor",
        )
