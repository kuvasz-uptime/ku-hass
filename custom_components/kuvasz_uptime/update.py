"""Update entity for the Kuvasz Uptime integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.update import UpdateEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import KuvaszCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Kuvasz update entity for a config entry."""
    coordinator: KuvaszCoordinator = hass.data[DOMAIN][entry.entry_id]
    if not coordinator.data.update_checks_enabled:
        return
    async_add_entities([KuvaszUpdateEntity(coordinator, entry)])


class KuvaszUpdateEntity(CoordinatorEntity["KuvaszCoordinator"], UpdateEntity):
    """Update entity tracking the installed and latest Kuvasz server version."""

    _attr_has_entity_name = True
    _attr_translation_key = "kuvasz_update"

    def __init__(self, coordinator: KuvaszCoordinator, entry: ConfigEntry) -> None:
        """Initialize the update entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_update"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info for the Kuvasz server hub device."""
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry.entry_id}_server")},
            name="Kuvasz Server",
            manufacturer="Kuvasz Uptime",
        )

    @property
    def installed_version(self) -> str | None:
        """Return the currently installed Kuvasz version."""
        return self.coordinator.data.version_info.get("installedVersion")

    @property
    def latest_version(self) -> str | None:
        """Return the latest Kuvasz version, or None if update checks are disabled."""
        return self.coordinator.data.version_info.get("latestVersion")

    @property
    def release_url(self) -> str | None:
        """Return a URL to the release notes for the latest version."""
        return self.coordinator.data.version_info.get("latestVersionDetails")
