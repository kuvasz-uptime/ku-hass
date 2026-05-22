"""The Kuvasz Uptime integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.const import CONF_HOST, Platform
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import KuvaszClient
from .const import (
    CONF_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_SELECTED_MONITORS,
    CONF_STATS_PERIOD,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STATS_PERIOD,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)
from .coordinator import KuvaszCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH]


def _entry_value(entry: ConfigEntry, key: str, default: Any | None = None) -> Any:
    """Read a value from entry.options first, then entry.data, then default."""
    return entry.options.get(key, entry.data.get(key, default))


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Kuvasz Uptime from a config entry."""
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    client = KuvaszClient(
        host=entry.data[CONF_HOST],
        api_key=entry.data[CONF_API_KEY],
        session=session,
    )
    scan_interval = _entry_value(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    selected_monitors = _entry_value(entry, CONF_SELECTED_MONITORS)
    stats_period = _entry_value(entry, CONF_STATS_PERIOD, DEFAULT_STATS_PERIOD)
    coordinator = KuvaszCoordinator(
        hass, client, scan_interval, selected_monitors, stats_period
    )
    await coordinator.async_config_entry_first_refresh()

    _remove_stale_devices(hass, entry, coordinator.data.monitors)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


def _remove_stale_devices(
    hass: HomeAssistant, entry: ConfigEntry, active_monitors: list
) -> None:
    """
    Remove devices (and their entities) for monitors no longer in the active set.

    Device identifiers use the format (DOMAIN, "{type}_{id}") - see entity.py.
    Removing a device from the device registry also removes all its entity
    registry entries.
    """
    active_keys = {f"{m['_type']}_{m['id']}" for m in active_monitors}
    dev_reg = dr.async_get(hass)
    for device_entry in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        monitor_key = next(
            (
                identifier
                for domain, identifier in device_entry.identifiers
                if domain == DOMAIN
            ),
            None,
        )
        if monitor_key not in active_keys:
            dev_reg.async_remove_device(device_entry.id)


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a Kuvasz Uptime config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
