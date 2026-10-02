"""Diagnostics support for Kuvasz Uptime."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST

from .const import CONF_API_KEY

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from .coordinator import KuvaszConfigEntry

# Credentials, plus anything that can point at private infrastructure or carry
# secrets of its own (URLs with tokens, auth headers, request bodies).
TO_REDACT = {
    CONF_API_KEY,
    CONF_HOST,
    "dockerHost",
    "expectedHeaders",
    "requestBody",
    "requestHeaders",
    "url",
}


def _without_logs(stats: dict[str, Any]) -> dict[str, Any]:
    """Drop the raw per-check logs, which can hold thousands of samples."""
    return {k: v for k, v in stats.items() if not k.endswith("Logs")}


async def async_get_config_entry_diagnostics(
    _hass: HomeAssistant, entry: KuvaszConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
        },
        "version_info": data.version_info,
        "update_checks_enabled": data.update_checks_enabled,
        "read_only_types": sorted(data.read_only_types),
        "monitors": async_redact_data(data.monitors, TO_REDACT),
        "stats": {key: _without_logs(stats) for key, stats in data.stats.items()},
    }
