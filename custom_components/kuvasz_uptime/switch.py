"""Switch for enabling/disabling Kuvasz monitors (writable monitor types only)."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MONITOR_TYPE_HTTP, MONITOR_TYPE_ICMP, MONITOR_TYPE_PUSH
from .coordinator import KuvaszCoordinator
from .entity import KuvaszMonitorEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
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
        super().__init__(coordinator, monitor)
        self._attr_unique_id = f"{DOMAIN}_{self._monitor_type}_{self._monitor_id}_enabled_switch"
        self.entity_id = self._build_entity_id("switch", "enabled")

    @property
    def is_on(self) -> bool | None:
        enabled = self._monitor_data.get("enabled")
        if enabled is None:
            return None
        return bool(enabled)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set_enabled(False)

    async def _set_enabled(self, enabled: bool) -> None:
        client = self.coordinator.client
        if self._monitor_type == MONITOR_TYPE_HTTP:
            await client.patch_http_monitor(self._monitor_id, {"enabled": enabled})
        elif self._monitor_type == MONITOR_TYPE_PUSH:
            await client.patch_push_monitor(self._monitor_id, {"enabled": enabled})
        elif self._monitor_type == MONITOR_TYPE_ICMP:
            await client.patch_icmp_monitor(self._monitor_id, {"enabled": enabled})
        await self.coordinator.async_request_refresh()
