"""Tests for the Kuvasz API client."""

import asyncio

import aiohttp
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.kuvasz_uptime.api import (
    KuvaszApiError,
    KuvaszAuthError,
    KuvaszClient,
)
from tests.conftest import (
    HTTP_MONITOR_DOWN,
    HTTP_MONITOR_STATS,
    HTTP_MONITOR_UP,
    ICMP_MONITOR_STATS,
    ICMP_MONITOR_UP,
    PUSH_MONITOR_STATS,
    PUSH_MONITOR_UP,
    SETTINGS_RESPONSE,
)

BASE_URL = "http://kuvasz.local:8080"
API_KEY = "test-api-key-1234567"


@pytest.fixture
def mock_api() -> AiohttpClientMocker:
    return AiohttpClientMocker()


async def _client(mock_api: AiohttpClientMocker, host: str, **kwargs):
    """Yield a KuvaszClient whose session is bound to mock_api."""
    session = mock_api.create_session(asyncio.get_running_loop())
    try:
        yield KuvaszClient(host=host, session=session, **kwargs)
    finally:
        await session.close()


@pytest.fixture
async def client(mock_api):
    async for c in _client(mock_api, BASE_URL, api_key=API_KEY):
        yield c


@pytest.fixture
async def client_no_key(mock_api):
    async for c in _client(mock_api, BASE_URL):
        yield c


class TestVerifyConnection:
    async def test_success(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/settings", json=SETTINGS_RESPONSE)
        assert await client.verify_connection() is True

    async def test_raises_auth_error_on_401(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/settings", status=401)
        with pytest.raises(KuvaszAuthError):
            await client.verify_connection()

    async def test_raises_api_error_on_500(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/settings", status=500)
        with pytest.raises(KuvaszApiError):
            await client.verify_connection()

    async def test_raises_api_error_on_connection_failure(self, client, mock_api):
        mock_api.get(
            f"{BASE_URL}/api/v2/settings",
            exc=aiohttp.ClientConnectionError(),
        )
        with pytest.raises(KuvaszApiError):
            await client.verify_connection()


class TestGetMonitors:
    async def test_get_http_monitors(self, client, mock_api):
        mock_api.get(
            f"{BASE_URL}/api/v2/http-monitors",
            json=[HTTP_MONITOR_UP, HTTP_MONITOR_DOWN],
        )
        result = await client.get_http_monitors()
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["uptimeStatus"] == "DOWN"

    async def test_get_push_monitors(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/push-monitors", json=[PUSH_MONITOR_UP])
        result = await client.get_push_monitors()
        assert len(result) == 1
        assert result[0]["name"] == "My Cron Job"

    async def test_get_icmp_monitors(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/icmp-monitors", json=[ICMP_MONITOR_UP])
        result = await client.get_icmp_monitors()
        assert len(result) == 1
        assert result[0]["name"] == "My Server"

    async def test_get_all_monitors_tags_type(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/http-monitors", json=[HTTP_MONITOR_UP])
        mock_api.get(f"{BASE_URL}/api/v2/push-monitors", json=[PUSH_MONITOR_UP])
        mock_api.get(f"{BASE_URL}/api/v2/icmp-monitors", json=[ICMP_MONITOR_UP])
        result = await client.get_all_monitors()

        types = {m["_type"] for m in result}
        assert types == {"http", "push", "icmp"}
        assert len(result) == 3

    async def test_get_all_monitors_raises_if_any_request_fails(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/http-monitors", status=500)
        mock_api.get(f"{BASE_URL}/api/v2/push-monitors", json=[])
        mock_api.get(f"{BASE_URL}/api/v2/icmp-monitors", json=[])
        with pytest.raises(KuvaszApiError):
            await client.get_all_monitors()

    async def test_get_all_monitors_skips_icmp_on_error_when_supported(
        self, client, mock_api
    ):
        """ICMP fetch failure is silently skipped; HTTP/push errors still raise."""
        mock_api.get(f"{BASE_URL}/api/v2/http-monitors", json=[HTTP_MONITOR_UP])
        mock_api.get(f"{BASE_URL}/api/v2/push-monitors", json=[PUSH_MONITOR_UP])
        mock_api.get(f"{BASE_URL}/api/v2/icmp-monitors", status=404)
        result = await client.get_all_monitors(icmp_supported=True)

        types = {m["_type"] for m in result}
        assert types == {"http", "push"}
        assert len(result) == 2

    async def test_get_all_monitors_skips_icmp_fetch_when_not_supported(
        self, client, mock_api
    ):
        """When icmp_supported=False the ICMP endpoint is never called."""
        mock_api.get(f"{BASE_URL}/api/v2/http-monitors", json=[HTTP_MONITOR_UP])
        mock_api.get(f"{BASE_URL}/api/v2/push-monitors", json=[PUSH_MONITOR_UP])
        result = await client.get_all_monitors(icmp_supported=False)

        types = {m["_type"] for m in result}
        assert types == {"http", "push"}
        assert len(result) == 2
        called = [str(url) for _, url, _, _ in mock_api.mock_calls]
        assert not any("icmp-monitors" in url for url in called)

    async def test_api_key_sent_as_header(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/http-monitors", json=[])
        await client.get_http_monitors()
        assert mock_api.mock_calls[0][3]["X-API-KEY"] == API_KEY

    async def test_no_api_key_header_when_key_is_omitted(self, client_no_key, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/http-monitors", json=[])
        await client_no_key.get_http_monitors()
        assert "X-API-KEY" not in mock_api.mock_calls[0][3]

    async def test_get_icmp_monitors_raises_if_request_fails(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/icmp-monitors", status=500)
        with pytest.raises(KuvaszApiError):
            await client.get_icmp_monitors()


class TestGetStats:
    async def test_get_http_monitor_stats(self, client, mock_api):
        mock_api.get(
            f"{BASE_URL}/api/v2/http-monitors/1/stats?period=P1D",
            json=HTTP_MONITOR_STATS,
        )
        result = await client.get_http_monitor_stats(1, "P1D")
        assert result["uptimeHistory"]["uptimeRatio"] == 0.9987
        assert result["latencyStats"]["averageLatencyInMs"] == 123

    async def test_get_http_monitor_stats_custom_period(self, client, mock_api):
        mock_api.get(
            f"{BASE_URL}/api/v2/http-monitors/1/stats?period=P7D",
            json=HTTP_MONITOR_STATS,
        )
        result = await client.get_http_monitor_stats(1, "P7D")
        assert result["uptimeHistory"]["uptimeRatio"] == 0.9987

    async def test_get_push_monitor_stats(self, client, mock_api):
        mock_api.get(
            f"{BASE_URL}/api/v2/push-monitors/20/stats?period=P1D",
            json=PUSH_MONITOR_STATS,
        )
        result = await client.get_push_monitor_stats(20, "P1D")
        assert result["uptimeHistory"]["uptimeRatio"] is None

    async def test_get_icmp_monitor_stats(self, client, mock_api):
        mock_api.get(
            f"{BASE_URL}/api/v2/icmp-monitors/30/stats?period=P1D",
            json=ICMP_MONITOR_STATS,
        )
        result = await client.get_icmp_monitor_stats(30, "P1D")
        assert result["uptimeHistory"]["uptimeRatio"] == 0.9999
        assert result["latencyStats"]["averageLatencyInMs"] == 10
        assert result["packetLossStats"]["averagePacketLossPercentage"] == 0

    async def test_trailing_slash_stripped_from_host(self, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/settings", json=SETTINGS_RESPONSE)
        async for client in _client(mock_api, f"{BASE_URL}/", api_key=API_KEY):
            assert await client.verify_connection() is True
