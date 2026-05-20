"""Tests for the Kuvasz API client."""
import pytest
from aioresponses import aioresponses
import aiohttp

from custom_components.kuvasz_uptime.api import KuvaszClient, KuvaszApiError, KuvaszAuthError
from tests.conftest import (
    HTTP_MONITOR_UP,
    HTTP_MONITOR_DOWN,
    PUSH_MONITOR_UP,
    HTTP_MONITOR_STATS,
    PUSH_MONITOR_STATS,
    SETTINGS_RESPONSE,
)

BASE_URL = "http://kuvasz.local:8080"
API_KEY = "test-api-key-1234567"


@pytest.fixture
async def client():
    async with aiohttp.ClientSession() as session:
        yield KuvaszClient(host=BASE_URL, api_key=API_KEY, session=session)


class TestVerifyConnection:
    async def test_success(self, client):
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/v2/settings", payload=SETTINGS_RESPONSE)
            result = await client.verify_connection()
        assert result is True

    async def test_raises_auth_error_on_401(self, client):
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/v2/settings", status=401)
            with pytest.raises(KuvaszAuthError):
                await client.verify_connection()

    async def test_raises_api_error_on_500(self, client):
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/v2/settings", status=500)
            with pytest.raises(KuvaszApiError):
                await client.verify_connection()

    async def test_raises_api_error_on_connection_failure(self, client):
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/v2/settings", exception=aiohttp.ClientConnectionError())
            with pytest.raises(KuvaszApiError):
                await client.verify_connection()


class TestGetMonitors:
    async def test_get_http_monitors(self, client):
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/v2/http-monitors", payload=[HTTP_MONITOR_UP, HTTP_MONITOR_DOWN])
            result = await client.get_http_monitors()
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[1]["uptimeStatus"] == "DOWN"

    async def test_get_push_monitors(self, client):
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/v2/push-monitors", payload=[PUSH_MONITOR_UP])
            result = await client.get_push_monitors()
        assert len(result) == 1
        assert result[0]["name"] == "My Cron Job"

    async def test_get_all_monitors_tags_type(self, client):
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/v2/http-monitors", payload=[HTTP_MONITOR_UP])
            m.get(f"{BASE_URL}/api/v2/push-monitors", payload=[PUSH_MONITOR_UP])
            result = await client.get_all_monitors()

        types = {m["_type"] for m in result}
        assert types == {"http", "push"}
        assert len(result) == 2

    async def test_get_all_monitors_raises_if_any_request_fails(self, client):
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/v2/http-monitors", status=500)
            m.get(f"{BASE_URL}/api/v2/push-monitors", payload=[])
            with pytest.raises(KuvaszApiError):
                await client.get_all_monitors()

    async def test_api_key_sent_as_header(self, client):
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/v2/http-monitors", payload=[])
            await client.get_http_monitors()
            request = list(m.requests.values())[0][0]
        assert request.kwargs["headers"]["X-API-KEY"] == API_KEY


class TestGetStats:
    async def test_get_http_monitor_stats(self, client):
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/v2/http-monitors/1/stats?period=P1D", payload=HTTP_MONITOR_STATS)
            result = await client.get_http_monitor_stats(1, "P1D")
        assert result["uptimeHistory"]["uptimeRatio"] == 0.9987
        assert result["latencyStats"]["averageLatencyInMs"] == 123

    async def test_get_http_monitor_stats_custom_period(self, client):
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/v2/http-monitors/1/stats?period=P7D", payload=HTTP_MONITOR_STATS)
            result = await client.get_http_monitor_stats(1, "P7D")
        assert result["uptimeHistory"]["uptimeRatio"] == 0.9987

    async def test_get_push_monitor_stats(self, client):
        with aioresponses() as m:
            m.get(f"{BASE_URL}/api/v2/push-monitors/20/stats?period=P1D", payload=PUSH_MONITOR_STATS)
            result = await client.get_push_monitor_stats(20, "P1D")
        assert result["uptimeHistory"]["uptimeRatio"] is None

    async def test_trailing_slash_stripped_from_host(self):
        async with aiohttp.ClientSession() as session:
            client = KuvaszClient(host=f"{BASE_URL}/", api_key=API_KEY, session=session)
            with aioresponses() as m:
                m.get(f"{BASE_URL}/api/v2/settings", payload=SETTINGS_RESPONSE)
                result = await client.verify_connection()
            assert result is True
