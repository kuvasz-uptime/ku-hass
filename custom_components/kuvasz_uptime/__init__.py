"""The Kuvasz Uptime integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import callback
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
)
from .coordinator import KuvaszConfigEntry, KuvaszCoordinator, entry_value
from .entity import (
    monitor_device_identifier,
    server_device_identifier,
    server_device_info,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH, Platform.UPDATE]


async def async_setup_entry(hass: HomeAssistant, entry: KuvaszConfigEntry) -> bool:
    """Set up Kuvasz Uptime from a config entry."""
    verify_ssl = entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    client = KuvaszClient(
        host=entry.data[CONF_HOST],
        api_key=entry.data.get(CONF_API_KEY) or None,
        session=session,
    )
    scan_interval = entry_value(entry, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    selected_monitors = entry_value(entry, CONF_SELECTED_MONITORS)
    stats_period = entry_value(entry, CONF_STATS_PERIOD, DEFAULT_STATS_PERIOD)
    coordinator = KuvaszCoordinator(
        hass,
        entry,
        client,
        scan_interval=scan_interval,
        selected_monitors=selected_monitors,
        stats_period=stats_period,
    )
    await coordinator.async_config_entry_first_refresh()

    _remove_stale_devices(hass, entry, coordinator.data.monitors)

    # Monitor devices point at the server device via via_device_id, so it has to
    # exist before the platforms add their entities.
    dev_reg = dr.async_get(hass)
    server_device = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id, **server_device_info(coordinator)
    )
    coordinator.server_device_id = server_device.id
    server_version = server_device.sw_version

    @callback
    def _async_sync_devices() -> None:
        """Follow server upgrades and drop devices of monitors deleted in Kuvasz."""
        nonlocal server_version
        version = coordinator.data.version_info.get("installedVersion")
        if version != server_version:
            server_version = version
            dev_reg.async_update_device(server_device.id, sw_version=version)
        _remove_stale_devices(hass, entry, coordinator.data.monitors)

    entry.async_on_unload(coordinator.async_add_listener(_async_sync_devices))

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


def _remove_stale_devices(
    hass: HomeAssistant, entry: KuvaszConfigEntry, active_monitors: list
) -> None:
    """
    Remove devices (and their entities) for monitors no longer in the active set.

    The server hub device is never removed. Removing a device also removes all its
    entity registry entries.
    """
    entry_id = entry.entry_id
    active = {
        monitor_device_identifier(entry_id, m["_type"], m["id"])
        for m in active_monitors
    }
    active.add(server_device_identifier(entry_id))
    dev_reg = dr.async_get(hass)
    for device_entry in dr.async_entries_for_config_entry(dev_reg, entry_id):
        if not device_entry.identifiers & active:
            dev_reg.async_remove_device(device_entry.id)


async def async_unload_entry(hass: HomeAssistant, entry: KuvaszConfigEntry) -> bool:
    """Unload a Kuvasz Uptime config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
