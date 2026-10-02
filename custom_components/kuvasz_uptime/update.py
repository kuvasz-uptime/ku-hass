"""Update entity for the Kuvasz Uptime integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from homeassistant.components.update import UpdateEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KuvaszCoordinator
from .entity import server_device_info

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.device_registry import DeviceInfo
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import KuvaszConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: KuvaszConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Kuvasz update entity for a config entry."""
    coordinator = entry.runtime_data
    if not coordinator.data.update_checks_enabled:
        return
    async_add_entities([KuvaszUpdateEntity(coordinator)])


class KuvaszUpdateEntity(CoordinatorEntity[KuvaszCoordinator], UpdateEntity):
    """Update entity tracking the installed and latest Kuvasz server version."""

    _attr_has_entity_name = True
    # The entity is the server device's main feature, so it takes the device name.
    _attr_name = None

    def __init__(self, coordinator: KuvaszCoordinator) -> None:
        """Initialize the update entity."""
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{DOMAIN}_{entry_id}_update"

    @property
    @override
    def device_info(self) -> DeviceInfo:
        """Return device info for the Kuvasz server hub device."""
        return server_device_info(self.coordinator)

    @property
    @override
    def installed_version(self) -> str | None:
        """Return the currently installed Kuvasz version."""
        return self.coordinator.data.version_info.get("installedVersion")

    @property
    @override
    def latest_version(self) -> str | None:
        """Return the latest Kuvasz version, or None if update checks are disabled."""
        return self.coordinator.data.version_info.get("latestVersion")

    @property
    @override
    def release_url(self) -> str | None:
        """Return a URL to the release notes for the latest version."""
        return self.coordinator.data.version_info.get("latestVersionDetails")
