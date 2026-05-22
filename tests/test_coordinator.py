"""Tests for the Kuvasz DataUpdateCoordinator."""

from unittest.mock import AsyncMock, MagicMock

from custom_components.kuvasz_uptime.api import KuvaszApiError, KuvaszClient
from custom_components.kuvasz_uptime.coordinator import (
    KuvaszCoordinator,
)
from tests.conftest import (
    HTTP_MONITOR_STATS,
    HTTP_MONITOR_UP,
    ICMP_MONITOR_STATS,
    ICMP_MONITOR_UP,
    PUSH_MONITOR_STATS,
    PUSH_MONITOR_UP,
    SETTINGS_RESPONSE,
    SETTINGS_RESPONSE_NO_ICMP,
)


def _make_client(monitors=None, stats=None, monitors_error=None, settings=None):
    stats = stats or {}
    client = MagicMock(spec=KuvaszClient)
    client.get_settings = AsyncMock(return_value=settings or SETTINGS_RESPONSE)
    if monitors_error:
        client.get_all_monitors = AsyncMock(side_effect=monitors_error)
    else:
        tagged = []
        for m in monitors or []:
            tagged.append(m)
        client.get_all_monitors = AsyncMock(return_value=tagged)

    client.get_http_monitor_stats = AsyncMock(
        return_value=stats.get("http", HTTP_MONITOR_STATS)
    )
    client.get_push_monitor_stats = AsyncMock(
        return_value=stats.get("push", PUSH_MONITOR_STATS)
    )
    client.get_icmp_monitor_stats = AsyncMock(
        return_value=stats.get("icmp", ICMP_MONITOR_STATS)
    )
    return client


class TestCoordinatorFetch:
    async def test_returns_all_monitors(self, hass):
        monitors = [HTTP_MONITOR_UP, PUSH_MONITOR_UP, ICMP_MONITOR_UP]
        client = _make_client(monitors=monitors)
        coordinator = KuvaszCoordinator(hass, client, scan_interval=30)

        await coordinator.async_refresh()

        assert len(coordinator.data.monitors) == 3

    async def test_stats_keyed_by_type_and_id(self, hass):
        monitors = [HTTP_MONITOR_UP, PUSH_MONITOR_UP, ICMP_MONITOR_UP]
        client = _make_client(monitors=monitors)
        coordinator = KuvaszCoordinator(hass, client, scan_interval=30)

        await coordinator.async_refresh()

        assert "http_1" in coordinator.data.stats
        assert "push_20" in coordinator.data.stats
        assert "icmp_30" in coordinator.data.stats

    async def test_monitor_stats_helper(self, hass):
        client = _make_client(
            monitors=[HTTP_MONITOR_UP], stats={"http": HTTP_MONITOR_STATS}
        )
        coordinator = KuvaszCoordinator(hass, client, scan_interval=30)

        await coordinator.async_refresh()

        stats = coordinator.data.monitor_stats("http", 1)
        assert stats["uptimeHistory"]["uptimeRatio"] == 0.9987

    async def test_raises_update_failed_on_api_error(self, hass):
        client = _make_client(monitors_error=KuvaszApiError("network down"))
        coordinator = KuvaszCoordinator(hass, client, scan_interval=30)

        await coordinator.async_refresh()

        assert coordinator.last_update_success is False

    async def test_stats_fetch_failure_does_not_crash_coordinator(self, hass):
        """A stats fetch error for one monitor should not abort the whole update."""
        client = _make_client(monitors=[HTTP_MONITOR_UP])
        client.get_http_monitor_stats = AsyncMock(
            side_effect=KuvaszApiError("stats unavailable")
        )
        coordinator = KuvaszCoordinator(hass, client, scan_interval=30)

        await coordinator.async_refresh()

        assert coordinator.last_update_success is True
        assert coordinator.data.monitor_stats("http", 1) == {}

    async def test_empty_monitor_list(self, hass):
        client = _make_client(monitors=[])
        coordinator = KuvaszCoordinator(hass, client, scan_interval=30)

        await coordinator.async_refresh()

        assert coordinator.data.monitors == []
        assert coordinator.data.stats == {}

    async def test_monitor_stats_returns_empty_dict_for_unknown_key(self, hass):
        client = _make_client(monitors=[HTTP_MONITOR_UP])
        coordinator = KuvaszCoordinator(hass, client, scan_interval=30)

        await coordinator.async_refresh()

        assert coordinator.data.monitor_stats("http", 9999) == {}


class TestCoordinatorMonitorFiltering:
    async def test_selected_monitors_filters_results(self, hass):
        client = _make_client(monitors=[HTTP_MONITOR_UP, PUSH_MONITOR_UP])
        coordinator = KuvaszCoordinator(
            hass, client, scan_interval=30, selected_monitors=["http_1"]
        )

        await coordinator.async_refresh()

        assert len(coordinator.data.monitors) == 1
        assert coordinator.data.monitors[0]["_type"] == "http"

    async def test_none_selected_monitors_shows_all(self, hass):
        client = _make_client(monitors=[HTTP_MONITOR_UP, PUSH_MONITOR_UP])
        coordinator = KuvaszCoordinator(
            hass, client, scan_interval=30, selected_monitors=None
        )

        await coordinator.async_refresh()

        assert len(coordinator.data.monitors) == 2

    async def test_empty_selected_monitors_shows_nothing(self, hass):
        client = _make_client(monitors=[HTTP_MONITOR_UP, PUSH_MONITOR_UP])
        coordinator = KuvaszCoordinator(
            hass, client, scan_interval=30, selected_monitors=[]
        )

        await coordinator.async_refresh()

        assert coordinator.data.monitors == []

    async def test_unknown_monitor_key_is_ignored(self, hass):
        client = _make_client(monitors=[HTTP_MONITOR_UP, PUSH_MONITOR_UP])
        coordinator = KuvaszCoordinator(
            hass, client, scan_interval=30, selected_monitors=["http_1", "http_999"]
        )

        await coordinator.async_refresh()

        assert len(coordinator.data.monitors) == 1
        assert coordinator.data.monitors[0]["id"] == 1

    async def test_only_selected_monitors_get_stats_fetched(self, hass):
        client = _make_client(monitors=[HTTP_MONITOR_UP, PUSH_MONITOR_UP])
        coordinator = KuvaszCoordinator(
            hass, client, scan_interval=30, selected_monitors=["http_1"]
        )

        await coordinator.async_refresh()

        assert "http_1" in coordinator.data.stats
        assert "push_20" not in coordinator.data.stats


class TestIcmpCoordinator:
    async def test_icmp_stats_fetched(self, hass):
        client = _make_client(
            monitors=[ICMP_MONITOR_UP], stats={"icmp": ICMP_MONITOR_STATS}
        )
        coordinator = KuvaszCoordinator(hass, client, scan_interval=30)

        await coordinator.async_refresh()

        stats = coordinator.data.monitor_stats("icmp", 30)
        assert stats["uptimeHistory"]["uptimeRatio"] == 0.9999
        assert stats["latencyStats"]["averageLatencyInMs"] == 10
        assert stats["packetLossStats"]["averagePacketLossPercentage"] == 0

    async def test_icmp_read_only_flag_from_settings(self, hass):
        from tests.conftest import SETTINGS_RESPONSE_READ_ONLY

        client = _make_client(
            monitors=[ICMP_MONITOR_UP], settings=SETTINGS_RESPONSE_READ_ONLY
        )
        coordinator = KuvaszCoordinator(hass, client, scan_interval=30)

        await coordinator.async_refresh()

        assert coordinator.data.icmp_read_only is True

    async def test_icmp_not_read_only_by_default(self, hass):
        client = _make_client(monitors=[ICMP_MONITOR_UP])
        coordinator = KuvaszCoordinator(hass, client, scan_interval=30)

        await coordinator.async_refresh()

        assert coordinator.data.icmp_read_only is False

    async def test_is_read_only_icmp(self, hass):
        client = _make_client(monitors=[])
        coordinator = KuvaszCoordinator(hass, client, scan_interval=30)
        await coordinator.async_refresh()
        coordinator.data.icmp_read_only = True

        assert coordinator.data.is_read_only("icmp") is True

    async def test_icmp_skipped_when_not_in_settings(self, hass):
        """Older instances without areIcmpMonitorsReadOnly skip ICMP monitors."""
        client = _make_client(
            monitors=[HTTP_MONITOR_UP, PUSH_MONITOR_UP],
            settings=SETTINGS_RESPONSE_NO_ICMP,
        )
        coordinator = KuvaszCoordinator(hass, client, scan_interval=30)

        await coordinator.async_refresh()

        assert coordinator.last_update_success is True
        client.get_all_monitors.assert_called_once_with(icmp_supported=False)
        assert coordinator.data.icmp_read_only is False

    async def test_icmp_fetched_when_in_settings(self, hass):
        """Instances with areIcmpMonitorsReadOnly should fetch ICMP monitors."""
        client = _make_client(
            monitors=[HTTP_MONITOR_UP, ICMP_MONITOR_UP], settings=SETTINGS_RESPONSE
        )
        coordinator = KuvaszCoordinator(hass, client, scan_interval=30)

        await coordinator.async_refresh()

        client.get_all_monitors.assert_called_once_with(icmp_supported=True)
