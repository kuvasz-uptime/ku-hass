"""Switch for enabling/disabling Kuvasz monitors (writable monitor types only)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN
from .entity import KuvaszMonitorEntity
from .monitor_types import MONITOR_TYPES_BY_KEY

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
    """Set up Kuvasz switches for a config entry."""
    coordinator: KuvaszCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        KuvaszEnabledSwitch(coordinator, monitor)
        for monitor in coordinator.data.monitors
        if not coordinator.data.is_read_only(monitor["_type"])
    )


class KuvaszEnabledSwitch(KuvaszMonitorEntity, SwitchEntity):
    """Switch that enables or disables a writable Kuvasz monitor."""

    _attr_translation_key = "enabled"

    def __init__(self, coordinator: KuvaszCoordinator, monitor: dict[str, Any]) -> None:
        """Initialize the enabled switch."""
        super().__init__(coordinator, monitor)
        self._attr_unique_id = self._build_unique_id("enabled_switch")
        self.entity_id = self._build_entity_id("switch", "enabled")

    @property
    def is_on(self) -> bool | None:
        """Return True if the monitor is currently enabled."""
        enabled = self._monitor_data.get("enabled")
        if enabled is None:
            return None
        return bool(enabled)

    async def async_turn_on(self, **_kwargs: Any) -> None:
        """Enable the monitor."""
        await self._set_enabled(enabled=True)

    async def async_turn_off(self, **_kwargs: Any) -> None:
        """Disable the monitor."""
        await self._set_enabled(enabled=False)

    async def _set_enabled(self, *, enabled: bool) -> None:
        await self.coordinator.client.patch_monitor(
            MONITOR_TYPES_BY_KEY[self._monitor_type],
            self._monitor_id,
            {"enabled": enabled},
        )
        await self.coordinator.async_request_refresh()
