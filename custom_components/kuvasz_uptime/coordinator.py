"""DataUpdateCoordinator for Kuvasz."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import KuvaszApiError, KuvaszClient
from .const import DEFAULT_STATS_PERIOD, DOMAIN, MONITOR_TYPE_HTTP, MONITOR_TYPE_ICMP, MONITOR_TYPE_PUSH

_LOGGER = logging.getLogger(__name__)


class KuvaszCoordinatorData:
    """Holds all fetched Kuvasz data."""

    def __init__(
        self,
        monitors: list[dict[str, Any]],
        stats: dict[str, dict[str, Any]],
        http_read_only: bool = False,
        push_read_only: bool = False,
        icmp_read_only: bool = False,
    ) -> None:
        self.monitors = monitors
        # stats keyed by "{type}_{id}"
        self.stats = stats
        self.http_read_only = http_read_only
        self.push_read_only = push_read_only
        self.icmp_read_only = icmp_read_only

    def monitor_stats(self, monitor_type: str, monitor_id: int) -> dict[str, Any]:
        return self.stats.get(f"{monitor_type}_{monitor_id}", {})

    def is_read_only(self, monitor_type: str) -> bool:
        if monitor_type == MONITOR_TYPE_HTTP:
            return self.http_read_only
        if monitor_type == MONITOR_TYPE_PUSH:
            return self.push_read_only
        if monitor_type == MONITOR_TYPE_ICMP:
            return self.icmp_read_only
        return True


class KuvaszCoordinator(DataUpdateCoordinator[KuvaszCoordinatorData]):
    def __init__(
        self,
        hass: HomeAssistant,
        client: KuvaszClient,
        scan_interval: int,
        selected_monitors: list[str] | None = None,
        stats_period: str = DEFAULT_STATS_PERIOD,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.client = client
        self._selected_monitors: set[str] | None = (
            set(selected_monitors) if selected_monitors is not None else None
        )
        self._stats_period = stats_period

    async def _async_update_data(self) -> KuvaszCoordinatorData:
        try:
            settings, monitors = await asyncio.gather(
                self.client.get_settings(),
                self.client.get_all_monitors(),
            )
            if self._selected_monitors is not None:
                monitors = [
                    m for m in monitors
                    if f"{m['_type']}_{m['id']}" in self._selected_monitors
                ]
            stats = await self._fetch_stats(monitors)
        except KuvaszApiError as err:
            raise UpdateFailed(f"Error during communication with your Kuvasz instance: {err}") from err

        editability = settings.get("app", {}).get("editabilityState", {})
        return KuvaszCoordinatorData(
            monitors=monitors,
            stats=stats,
            http_read_only=editability.get("areHttpMonitorsReadOnly", False),
            push_read_only=editability.get("arePushMonitorsReadOnly", False),
            icmp_read_only=editability.get("areIcmpMonitorsReadOnly", False),
        )

    async def _fetch_stats(self, monitors: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        async def _get_stats(monitor: dict[str, Any]) -> tuple[str, dict[str, Any]]:
            monitor_type = monitor["_type"]
            monitor_id = monitor["id"]
            key = f"{monitor_type}_{monitor_id}"
            try:
                if monitor_type == MONITOR_TYPE_HTTP:
                    data = await self.client.get_http_monitor_stats(monitor_id, self._stats_period)
                elif monitor_type == MONITOR_TYPE_PUSH:
                    data = await self.client.get_push_monitor_stats(monitor_id, self._stats_period)
                elif monitor_type == MONITOR_TYPE_ICMP:
                    data = await self.client.get_icmp_monitor_stats(monitor_id, self._stats_period)
                else:
                    data = {}
            except KuvaszApiError:
                _LOGGER.debug("Could not fetch stats for monitor %s", key)
                data = {}
            return key, data

        results = await asyncio.gather(*[_get_stats(m) for m in monitors])
        return dict(results)
