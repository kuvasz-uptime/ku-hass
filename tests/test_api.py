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
from custom_components.kuvasz_uptime.monitor_types import (
    MONITOR_TYPES,
    MONITOR_TYPES_BY_KEY,
)
from tests.conftest import (
    DNS_MONITOR_STATS,
    DNS_MONITOR_UP,
    HTTP_MONITOR_DOWN,
    HTTP_MONITOR_STATS,
    HTTP_MONITOR_UP,
    ICMP_MONITOR_STATS,
    ICMP_MONITOR_UP,
    PUSH_MONITOR_STATS,
    PUSH_MONITOR_UP,
    SETTINGS_RESPONSE,
    TCP_MONITOR_STATS,
    TCP_MONITOR_UP,
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


class TestGetSettings:
    async def test_success(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/settings", json=SETTINGS_RESPONSE)
        result = await client.get_settings()
        assert result["app"]["editabilityState"]["areTcpMonitorsReadOnly"] is False

    async def test_raises_auth_error_on_401(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/settings", status=401)
        with pytest.raises(KuvaszAuthError):
            await client.get_settings()

    async def test_raises_api_error_on_500(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/settings", status=500)
        with pytest.raises(KuvaszApiError):
            await client.get_settings()

    async def test_raises_api_error_on_connection_failure(self, client, mock_api):
        mock_api.get(
            f"{BASE_URL}/api/v2/settings",
            exc=aiohttp.ClientConnectionError(),
        )
        with pytest.raises(KuvaszApiError):
            await client.get_settings()


class TestGetMonitors:
    async def test_get_monitors(self, client, mock_api):
        mock_api.get(
            f"{BASE_URL}/api/v2/http-monitors",
            json=[HTTP_MONITOR_UP, HTTP_MONITOR_DOWN],
        )
        result = await client.get_monitors(MONITOR_TYPES_BY_KEY["http"])
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["uptimeStatus"] == "DOWN"

    async def test_get_push_monitors(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/push-monitors", json=[PUSH_MONITOR_UP])
        result = await client.get_monitors(MONITOR_TYPES_BY_KEY["push"])
        assert len(result) == 1
        assert result[0]["name"] == "My Cron Job"

    async def test_get_icmp_monitors(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/icmp-monitors", json=[ICMP_MONITOR_UP])
        result = await client.get_monitors(MONITOR_TYPES_BY_KEY["icmp"])
        assert len(result) == 1
        assert result[0]["name"] == "My Server"

    async def test_get_tcp_monitors(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/tcp-monitors", json=[TCP_MONITOR_UP])
        result = await client.get_monitors(MONITOR_TYPES_BY_KEY["tcp"])
        assert len(result) == 1
        assert result[0]["name"] == "My Database"
        assert result[0]["port"] == 5432

    async def test_get_dns_monitors(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/dns-monitors", json=[DNS_MONITOR_UP])
        result = await client.get_monitors(MONITOR_TYPES_BY_KEY["dns"])
        assert len(result) == 1
        assert result[0]["name"] == "My Domain"
        assert result[0]["host"] == "example.com"

    async def test_get_all_monitors_tags_type(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/http-monitors", json=[HTTP_MONITOR_UP])
        mock_api.get(f"{BASE_URL}/api/v2/push-monitors", json=[PUSH_MONITOR_UP])
        mock_api.get(f"{BASE_URL}/api/v2/icmp-monitors", json=[ICMP_MONITOR_UP])
        mock_api.get(f"{BASE_URL}/api/v2/tcp-monitors", json=[TCP_MONITOR_UP])
        mock_api.get(f"{BASE_URL}/api/v2/dns-monitors", json=[DNS_MONITOR_UP])
        result = await client.get_all_monitors(MONITOR_TYPES)

        types = {m["_type"] for m in result}
        assert types == {"http", "push", "icmp", "tcp", "dns"}
        assert len(result) == 5

    async def test_get_all_monitors_raises_if_any_request_fails(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/http-monitors", status=500)
        mock_api.get(f"{BASE_URL}/api/v2/push-monitors", json=[])
        mock_api.get(f"{BASE_URL}/api/v2/icmp-monitors", json=[])
        mock_api.get(f"{BASE_URL}/api/v2/tcp-monitors", json=[])
        mock_api.get(f"{BASE_URL}/api/v2/dns-monitors", json=[])
        with pytest.raises(KuvaszApiError):
            await client.get_all_monitors(MONITOR_TYPES)

    @pytest.mark.parametrize("failing", ["icmp", "tcp", "dns"])
    async def test_get_all_monitors_raises_when_requested_type_fails(
        self, client, mock_api, failing
    ):
        """A type the caller asked for is supported, so its errors are real."""
        for key in ("http", "push", "icmp", "tcp", "dns"):
            path = f"{BASE_URL}{MONITOR_TYPES_BY_KEY[key].api_path}"
            if key == failing:
                mock_api.get(path, status=503)
            else:
                mock_api.get(path, json=[])

        with pytest.raises(KuvaszApiError, match=failing):
            await client.get_all_monitors(MONITOR_TYPES)

    async def test_get_all_monitors_only_fetches_given_types(self, client, mock_api):
        """Types the instance does not support are never probed."""
        mock_api.get(f"{BASE_URL}/api/v2/http-monitors", json=[HTTP_MONITOR_UP])
        mock_api.get(f"{BASE_URL}/api/v2/push-monitors", json=[PUSH_MONITOR_UP])
        legacy = tuple(m for m in MONITOR_TYPES if not m.optional)
        result = await client.get_all_monitors(legacy)

        types = {m["_type"] for m in result}
        assert types == {"http", "push"}
        called = [str(url) for _, url, _, _ in mock_api.mock_calls]
        assert not any(
            probe in url
            for url in called
            for probe in ("icmp-monitors", "tcp-monitors", "dns-monitors")
        )

    async def test_get_all_monitors_empty_types(self, client, mock_api):
        assert await client.get_all_monitors(()) == []
        assert mock_api.mock_calls == []

    async def test_api_key_sent_as_header(self, client, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/http-monitors", json=[])
        await client.get_monitors(MONITOR_TYPES_BY_KEY["http"])
        assert mock_api.mock_calls[0][3]["X-API-KEY"] == API_KEY

    async def test_no_api_key_header_when_key_is_omitted(self, client_no_key, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/http-monitors", json=[])
        await client_no_key.get_monitors(MONITOR_TYPES_BY_KEY["http"])
        assert "X-API-KEY" not in mock_api.mock_calls[0][3]

    @pytest.mark.parametrize("key", ["http", "push", "icmp", "tcp", "dns"])
    async def test_get_monitors_raises_if_request_fails(self, client, mock_api, key):
        spec = MONITOR_TYPES_BY_KEY[key]
        mock_api.get(f"{BASE_URL}{spec.api_path}", status=500)
        with pytest.raises(KuvaszApiError):
            await client.get_monitors(spec)


class TestGetStats:
    async def test_get_http_monitor_stats(self, client, mock_api):
        mock_api.get(
            f"{BASE_URL}/api/v2/http-monitors/1/stats?period=P1D",
            json=HTTP_MONITOR_STATS,
        )
        result = await client.get_monitor_stats(MONITOR_TYPES_BY_KEY["http"], 1, "P1D")
        assert result["uptimeHistory"]["uptimeRatio"] == 0.9987
        assert result["latencyStats"]["averageLatencyInMs"] == 123

    async def test_get_http_monitor_stats_custom_period(self, client, mock_api):
        mock_api.get(
            f"{BASE_URL}/api/v2/http-monitors/1/stats?period=P7D",
            json=HTTP_MONITOR_STATS,
        )
        result = await client.get_monitor_stats(MONITOR_TYPES_BY_KEY["http"], 1, "P7D")
        assert result["uptimeHistory"]["uptimeRatio"] == 0.9987

    async def test_get_push_monitor_stats(self, client, mock_api):
        mock_api.get(
            f"{BASE_URL}/api/v2/push-monitors/20/stats?period=P1D",
            json=PUSH_MONITOR_STATS,
        )
        result = await client.get_monitor_stats(MONITOR_TYPES_BY_KEY["push"], 20, "P1D")
        assert result["uptimeHistory"]["uptimeRatio"] is None

    async def test_get_icmp_monitor_stats(self, client, mock_api):
        mock_api.get(
            f"{BASE_URL}/api/v2/icmp-monitors/30/stats?period=P1D",
            json=ICMP_MONITOR_STATS,
        )
        result = await client.get_monitor_stats(MONITOR_TYPES_BY_KEY["icmp"], 30, "P1D")
        assert result["uptimeHistory"]["uptimeRatio"] == 0.9999
        assert result["latencyStats"]["averageLatencyInMs"] == 10
        assert result["packetLossStats"]["averagePacketLossPercentage"] == 0

    async def test_get_tcp_monitor_stats(self, client, mock_api):
        mock_api.get(
            f"{BASE_URL}/api/v2/tcp-monitors/40/stats?period=P1D",
            json=TCP_MONITOR_STATS,
        )
        result = await client.get_monitor_stats(MONITOR_TYPES_BY_KEY["tcp"], 40, "P1D")
        assert result["uptimeHistory"]["uptimeRatio"] == 0.9995
        assert result["latencyStats"]["averageLatencyInMs"] == 15

    async def test_get_dns_monitor_stats(self, client, mock_api):
        mock_api.get(
            f"{BASE_URL}/api/v2/dns-monitors/50/stats?period=P1D",
            json=DNS_MONITOR_STATS,
        )
        result = await client.get_monitor_stats(MONITOR_TYPES_BY_KEY["dns"], 50, "P1D")
        assert result["uptimeHistory"]["uptimeRatio"] == 0.9998
        assert result["latencyStats"]["averageLatencyInMs"] == 12

    async def test_trailing_slash_stripped_from_host(self, mock_api):
        mock_api.get(f"{BASE_URL}/api/v2/settings", json=SETTINGS_RESPONSE)
        async for client in _client(mock_api, f"{BASE_URL}/", api_key=API_KEY):
            assert await client.get_settings() == SETTINGS_RESPONSE
