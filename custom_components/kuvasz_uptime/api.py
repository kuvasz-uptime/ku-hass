"""Kuvasz REST API client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

from .const import (
    API_HTTP_MONITORS,
    API_ICMP_MONITORS,
    API_PUSH_MONITORS,
    MONITOR_TYPE_HTTP,
    MONITOR_TYPE_ICMP,
    MONITOR_TYPE_PUSH,
)


class KuvaszApiError(Exception):
    pass


class KuvaszAuthError(KuvaszApiError):
    pass


class KuvaszClient:
    def __init__(
        self,
        host: str,
        api_key: str,
        session: aiohttp.ClientSession,
    ) -> None:
        self._base_url = host.rstrip("/")
        self._headers = {"X-API-KEY": api_key}
        self._session = session

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.get(url, headers=self._headers, params=params) as resp:
                if resp.status == 401:
                    raise KuvaszAuthError("Invalid API key")
                if resp.status >= 400:
                    raise KuvaszApiError(f"API error {resp.status} for {path}")
                return await resp.json()
        except aiohttp.ClientError as err:
            raise KuvaszApiError(f"Connection error: {err}") from err
        except asyncio.TimeoutError as err:
            raise KuvaszApiError("Request timed out") from err

    async def _patch(self, path: str, data: dict[str, Any]) -> None:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.patch(url, headers=self._headers, json=data) as resp:
                if resp.status == 401:
                    raise KuvaszAuthError("Invalid API key")
                if resp.status >= 400:
                    raise KuvaszApiError(f"API error {resp.status} for {path}")
        except aiohttp.ClientError as err:
            raise KuvaszApiError(f"Connection error: {err}") from err
        except asyncio.TimeoutError as err:
            raise KuvaszApiError("Request timed out") from err

    async def get_settings(self) -> dict[str, Any]:
        return await self._get("/api/v2/settings")

    async def verify_connection(self) -> bool:
        """Verify credentials by fetching the settings endpoint."""
        await self.get_settings()
        return True

    async def get_http_monitors(self) -> list[dict[str, Any]]:
        return await self._get(API_HTTP_MONITORS)

    async def get_push_monitors(self) -> list[dict[str, Any]]:
        return await self._get(API_PUSH_MONITORS)

    async def get_icmp_monitors(self) -> list[dict[str, Any]]:
        return await self._get(API_ICMP_MONITORS)

    async def patch_http_monitor(self, monitor_id: int, data: dict[str, Any]) -> None:
        await self._patch(f"{API_HTTP_MONITORS}/{monitor_id}", data)

    async def patch_push_monitor(self, monitor_id: int, data: dict[str, Any]) -> None:
        await self._patch(f"{API_PUSH_MONITORS}/{monitor_id}", data)

    async def patch_icmp_monitor(self, monitor_id: int, data: dict[str, Any]) -> None:
        await self._patch(f"{API_ICMP_MONITORS}/{monitor_id}", data)

    async def get_http_monitor_stats(self, monitor_id: int, period: str) -> dict[str, Any]:
        return await self._get(f"{API_HTTP_MONITORS}/{monitor_id}/stats", params={"period": period})

    async def get_push_monitor_stats(self, monitor_id: int, period: str) -> dict[str, Any]:
        return await self._get(f"{API_PUSH_MONITORS}/{monitor_id}/stats", params={"period": period})

    async def get_icmp_monitor_stats(self, monitor_id: int, period: str) -> dict[str, Any]:
        return await self._get(f"{API_ICMP_MONITORS}/{monitor_id}/stats", params={"period": period})

    async def get_all_monitors(self, icmp_supported: bool = True) -> list[dict[str, Any]]:
        """Fetch all monitor types and tag each with its type."""
        coros = [self.get_http_monitors(), self.get_push_monitors()]
        if icmp_supported:
            coros.append(self.get_icmp_monitors())

        results = await asyncio.gather(*coros, return_exceptions=True)

        http, push = results[0], results[1]
        icmp = results[2] if icmp_supported else []

        monitors: list[dict[str, Any]] = []
        for result, monitor_type in (
            (http, MONITOR_TYPE_HTTP),
            (push, MONITOR_TYPE_PUSH),
            (icmp, MONITOR_TYPE_ICMP),
        ):
            if isinstance(result, Exception):
                if monitor_type == MONITOR_TYPE_ICMP:
                    _LOGGER.debug("ICMP monitors not supported on this instance, skipping: %s", result)
                    continue
                raise KuvaszApiError(f"Failed to fetch {monitor_type} monitors: {result}") from result
            for m in result:
                m["_type"] = monitor_type
            monitors.extend(result)
        return monitors
