"""Kuvasz REST API client."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

import aiohttp

if TYPE_CHECKING:
    from collections.abc import Sequence

    from .monitor_types import MonitorType

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

    async def get_monitors(self, monitor_type: MonitorType) -> list[dict[str, Any]]:
        """Return all monitors of the given type."""
        return await self._get(monitor_type.api_path)

    async def patch_monitor(
        self, monitor_type: MonitorType, monitor_id: int, data: dict[str, Any]
    ) -> None:
        """Patch a monitor of the given type with the given fields."""
        await self._patch(f"{monitor_type.api_path}/{monitor_id}", data)

    async def get_monitor_stats(
        self, monitor_type: MonitorType, monitor_id: int, period: str
    ) -> dict[str, Any]:
        """Return statistics for a monitor over the given period."""
        return await self._get(
            f"{monitor_type.api_path}/{monitor_id}/stats", params={"period": period}
        )

    async def get_all_monitors(
        self, monitor_types: Sequence[MonitorType]
    ) -> list[dict[str, Any]]:
        """
        Fetch every monitor of the given types and tag each with its type.

        Callers pass only the types the instance actually supports, so any
        failure here is a real one and is raised rather than swallowed.
        """
        results = await asyncio.gather(
            *(self.get_monitors(m) for m in monitor_types), return_exceptions=True
        )

        monitors: list[dict[str, Any]] = []
        for monitor_type, result in zip(monitor_types, results, strict=True):
            if isinstance(result, BaseException):
                msg = f"Failed to fetch {monitor_type.key} monitors: {result}"
                raise KuvaszApiError(msg) from result
            for m in result:
                m["_type"] = monitor_type.key
            monitors.extend(result)
        return monitors
