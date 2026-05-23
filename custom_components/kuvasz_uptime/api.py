"""Kuvasz REST API client."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    API_HTTP_MONITORS,
    API_ICMP_MONITORS,
    API_PUSH_MONITORS,
    MONITOR_TYPE_HTTP,
    MONITOR_TYPE_ICMP,
    MONITOR_TYPE_PUSH,
)

_LOGGER = logging.getLogger(__name__)

_HTTP_UNAUTHORIZED = 401
_HTTP_CLIENT_ERROR = 400


class KuvaszApiError(Exception):
    """Raised when a Kuvasz API request fails."""


class KuvaszAuthError(KuvaszApiError):
    """Raised when the API key is invalid or missing."""


class KuvaszClient:
    """HTTP client for the Kuvasz Uptime REST API."""

    def __init__(
        self,
        host: str,
        session: aiohttp.ClientSession,
        api_key: str | None = None,
    ) -> None:
        """Initialize the client with a host, optional API key and shared session."""
        self._base_url = host.rstrip("/")
        self._headers = {"X-API-KEY": api_key} if api_key else {}
        self._session = session

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.get(
                url, headers=self._headers, params=params
            ) as resp:
                if resp.status == _HTTP_UNAUTHORIZED:
                    msg = "Invalid API key"
                    raise KuvaszAuthError(msg)
                if resp.status >= _HTTP_CLIENT_ERROR:
                    msg = f"API error {resp.status} for {path}"
                    raise KuvaszApiError(msg)
                return await resp.json()
        except aiohttp.ClientError as err:
            msg = f"Connection error: {err}"
            raise KuvaszApiError(msg) from err
        except TimeoutError as err:
            msg = "Request timed out"
            raise KuvaszApiError(msg) from err

    async def _patch(self, path: str, data: dict[str, Any]) -> None:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.patch(
                url, headers=self._headers, json=data
            ) as resp:
                if resp.status == _HTTP_UNAUTHORIZED:
                    msg = "Invalid API key"
                    raise KuvaszAuthError(msg)
                if resp.status >= _HTTP_CLIENT_ERROR:
                    msg = f"API error {resp.status} for {path}"
                    raise KuvaszApiError(msg)
        except aiohttp.ClientError as err:
            msg = f"Connection error: {err}"
            raise KuvaszApiError(msg) from err
        except TimeoutError as err:
            msg = "Request timed out"
            raise KuvaszApiError(msg) from err

    async def get_settings(self) -> dict[str, Any]:
        """Return the Kuvasz instance settings."""
        return await self._get("/api/v2/settings")

    async def verify_connection(self) -> bool:
        """Verify credentials by fetching the settings endpoint."""
        await self.get_settings()
        return True

    async def get_http_monitors(self) -> list[dict[str, Any]]:
        """Return all HTTP monitors."""
        return await self._get(API_HTTP_MONITORS)

    async def get_push_monitors(self) -> list[dict[str, Any]]:
        """Return all push monitors."""
        return await self._get(API_PUSH_MONITORS)

    async def get_icmp_monitors(self) -> list[dict[str, Any]]:
        """Return all ICMP monitors."""
        return await self._get(API_ICMP_MONITORS)

    async def patch_http_monitor(self, monitor_id: int, data: dict[str, Any]) -> None:
        """Patch an HTTP monitor with the given fields."""
        await self._patch(f"{API_HTTP_MONITORS}/{monitor_id}", data)

    async def patch_push_monitor(self, monitor_id: int, data: dict[str, Any]) -> None:
        """Patch a push monitor with the given fields."""
        await self._patch(f"{API_PUSH_MONITORS}/{monitor_id}", data)

    async def patch_icmp_monitor(self, monitor_id: int, data: dict[str, Any]) -> None:
        """Patch an ICMP monitor with the given fields."""
        await self._patch(f"{API_ICMP_MONITORS}/{monitor_id}", data)

    async def get_http_monitor_stats(
        self, monitor_id: int, period: str
    ) -> dict[str, Any]:
        """Return statistics for an HTTP monitor over the given period."""
        return await self._get(
            f"{API_HTTP_MONITORS}/{monitor_id}/stats", params={"period": period}
        )

    async def get_push_monitor_stats(
        self, monitor_id: int, period: str
    ) -> dict[str, Any]:
        """Return statistics for a push monitor over the given period."""
        return await self._get(
            f"{API_PUSH_MONITORS}/{monitor_id}/stats", params={"period": period}
        )

    async def get_icmp_monitor_stats(
        self, monitor_id: int, period: str
    ) -> dict[str, Any]:
        """Return statistics for an ICMP monitor over the given period."""
        return await self._get(
            f"{API_ICMP_MONITORS}/{monitor_id}/stats", params={"period": period}
        )

    async def get_all_monitors(
        self, *, icmp_supported: bool = True
    ) -> list[dict[str, Any]]:
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
                    _LOGGER.debug(
                        "ICMP monitors not supported on this instance, skipping: %s",
                        result,
                    )
                    continue
                msg = f"Failed to fetch {monitor_type} monitors: {result}"
                raise KuvaszApiError(msg) from result
            for m in result:
                m["_type"] = monitor_type
            monitors.extend(result)
        return monitors
