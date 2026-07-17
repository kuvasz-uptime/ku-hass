"""DataUpdateCoordinator for Kuvasz."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KuvaszApiError, KuvaszClient
from .const import DEFAULT_STATS_PERIOD, DOMAIN
from .monitor_types import (
    MONITOR_TYPES_BY_KEY,
    read_only_monitor_types,
    supported_monitor_types,
)

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class KuvaszCoordinatorData:
    """Holds all fetched Kuvasz data."""

    def __init__(
        self,
        monitors: list[dict[str, Any]],
        stats: dict[str, dict[str, Any]],
        *,
        read_only_types: frozenset[str] = frozenset(),
        version_info: dict[str, Any] | None = None,
        update_checks_enabled: bool = False,
    ) -> None:
        """Initialize coordinator data with monitors, stats and read-only types."""
        self.monitors = monitors
        # stats keyed by "{type}_{id}"
        self.stats = stats
        self.read_only_types = read_only_types
        self.version_info: dict[str, Any] = version_info or {}
        self.update_checks_enabled = update_checks_enabled

    def monitor_stats(self, monitor_type: str, monitor_id: int) -> dict[str, Any]:
        """Return stats dict for the given monitor, or empty dict if unavailable."""
        return self.stats.get(f"{monitor_type}_{monitor_id}", {})

    def is_read_only(self, monitor_type: str) -> bool:
        """Return True if monitors of the given type cannot be modified via the API."""
        if monitor_type not in MONITOR_TYPES_BY_KEY:
            return True
        return monitor_type in self.read_only_types


class KuvaszCoordinator(DataUpdateCoordinator[KuvaszCoordinatorData]):
    """Coordinator that fetches and caches all Kuvasz monitor data."""

    def __init__(  # noqa: PLR0913
        self,
        hass: HomeAssistant,
        client: KuvaszClient,
        scan_interval: int,
        selected_monitors: list[str] | None = None,
        stats_period: str = DEFAULT_STATS_PERIOD,
        entry_id: str = "",
    ) -> None:
        """Initialize the coordinator with a Kuvasz API client and poll settings."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self.entry_id = entry_id
        self._selected_monitors: set[str] | None = (
            set(selected_monitors) if selected_monitors is not None else None
        )
        self._stats_period = stats_period

    async def _async_update_data(self) -> KuvaszCoordinatorData:
        try:
            settings = await self.client.get_settings()
            app_settings = settings.get("app", {})
            monitors = await self.client.get_all_monitors(
                supported_monitor_types(settings)
            )
            if self._selected_monitors is not None:
                monitors = [
                    m
                    for m in monitors
                    if f"{m['_type']}_{m['id']}" in self._selected_monitors
                ]
            stats = await self._fetch_stats(monitors)
        except KuvaszApiError as err:
            msg = f"Error during communication with your Kuvasz instance: {err}"
            raise UpdateFailed(msg) from err

        return KuvaszCoordinatorData(
            monitors=monitors,
            stats=stats,
            read_only_types=read_only_monitor_types(settings),
            version_info=settings.get("versionInfo"),
            update_checks_enabled=app_settings.get("updateChecksEnabled", False),
        )

    async def _fetch_stats(
        self, monitors: list[dict[str, Any]]
    ) -> dict[str, dict[str, Any]]:
        async def _get_stats(monitor: dict[str, Any]) -> tuple[str, dict[str, Any]]:
            monitor_type = monitor["_type"]
            monitor_id = monitor["id"]
            key = f"{monitor_type}_{monitor_id}"
            spec = MONITOR_TYPES_BY_KEY.get(monitor_type)
            if spec is None:
                return key, {}
            try:
                data = await self.client.get_monitor_stats(
                    spec, monitor_id, self._stats_period
                )
            except KuvaszApiError:
                _LOGGER.debug("Could not fetch stats for monitor %s", key)
                data = {}
            return key, data

        results = await asyncio.gather(*[_get_stats(m) for m in monitors])
        return dict(results)
