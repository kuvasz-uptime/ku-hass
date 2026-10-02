"""Base entity for Kuvasz monitors."""

from __future__ import annotations

from typing import Any, override

from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN
from .coordinator import KuvaszCoordinator
from .monitor_types import MONITOR_TYPES_BY_KEY, monitor_key

MANUFACTURER = "Kuvasz Uptime"


def server_device_identifier(entry_id: str) -> tuple[str, str]:
    """Return the device identifier of the Kuvasz server (hub) device."""
    return (DOMAIN, f"{entry_id}_server")


def monitor_device_identifier(
    entry_id: str, monitor_type: str, monitor_id: int
) -> tuple[str, str]:
    """Return the device identifier of a monitor device."""
    return (DOMAIN, f"{entry_id}_{monitor_key(monitor_type, monitor_id)}")


def server_device_info(coordinator: KuvaszCoordinator) -> DeviceInfo:
    """Return device registry information for the Kuvasz server itself."""
    entry = coordinator.config_entry
    return DeviceInfo(
        identifiers={server_device_identifier(entry.entry_id)},
        # Named after the entry so that several instances can be told apart.
        name=entry.title,
        manufacturer=MANUFACTURER,
        sw_version=coordinator.data.version_info.get("installedVersion"),
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=entry.data[CONF_HOST],
    )


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
        return self.coordinator.data.monitor(self._monitor_type, self._monitor_id)

    @property
    @override
    def available(self) -> bool:
        """Return False once the monitor is no longer reported by the instance."""
        return super().available and bool(self._monitor_data)

    @property
    def _monitor_stats(self) -> dict[str, Any]:
        return self.coordinator.data.monitor_stats(self._monitor_type, self._monitor_id)

    @property
    def _instance_key(self) -> str:
        """Return a unique prefix for this config entry, scoping all identifiers."""
        return self.coordinator.config_entry.entry_id

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return device registry information for this monitor."""
        spec = MONITOR_TYPES_BY_KEY.get(self._monitor_type)
        type_label = spec.device_label if spec else self._monitor_type.upper()
        info = DeviceInfo(
            identifiers={
                monitor_device_identifier(
                    self._instance_key, self._monitor_type, self._monitor_id
                )
            },
            name=self._monitor_name,
            manufacturer=MANUFACTURER,
            model=f"{type_label} Monitor",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=self.coordinator.config_entry.data[CONF_HOST],
        )
        if self.coordinator.server_device_id is not None:
            info["via_device_id"] = self.coordinator.server_device_id
        return info
