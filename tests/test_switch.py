"""Tests for Kuvasz enabled switch."""

from unittest.mock import AsyncMock, MagicMock

from custom_components.kuvasz_uptime.api import KuvaszClient
from custom_components.kuvasz_uptime.const import DOMAIN
from custom_components.kuvasz_uptime.coordinator import (
    KuvaszCoordinator,
    KuvaszCoordinatorData,
)
from custom_components.kuvasz_uptime.monitor_types import MONITOR_TYPES_BY_KEY
from tests.conftest import (
    DNS_MONITOR_UP,
    HTTP_MONITOR_UP,
    ICMP_MONITOR_UP,
    PUSH_MONITOR_UP,
    TCP_MONITOR_UP,
)


def _make_coordinator(hass, monitors, *, read_only_types=frozenset()):
    client = MagicMock(spec=KuvaszClient)
    client.patch_monitor = AsyncMock()
    coordinator = KuvaszCoordinator(
        hass, client, scan_interval=30, entry_id="test_entry"
    )
    coordinator.data = KuvaszCoordinatorData(
        monitors=monitors,
        stats={},
        read_only_types=frozenset(read_only_types),
    )
    return coordinator


async def _setup_integration(hass, coordinator):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["test_entry"] = coordinator

    from homeassistant.config_entries import ConfigEntry

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.domain = DOMAIN

    from custom_components.kuvasz_uptime.switch import async_setup_entry

    entities = []
    await async_setup_entry(hass, entry, entities.extend)
    return entities


class TestEnabledSwitch:
    async def test_enabled_monitor_is_on(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        assert entities[0].is_on is True

    async def test_disabled_monitor_is_off(self, hass):
        monitor = {**HTTP_MONITOR_UP, "enabled": False}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        assert entities[0].is_on is False

    async def test_none_enabled_returns_none(self, hass):
        monitor = {**HTTP_MONITOR_UP, "enabled": None}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        assert entities[0].is_on is None

    async def test_unique_id_http(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)
        assert entities[0].unique_id == "kuvasz_uptime_test_entry_http_1_enabled_switch"

    async def test_unique_id_push(self, hass):
        coordinator = _make_coordinator(hass, [PUSH_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)
        assert (
            entities[0].unique_id == "kuvasz_uptime_test_entry_push_20_enabled_switch"
        )

    async def test_one_switch_per_writable_monitor(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP, PUSH_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == 2

    async def test_no_switch_when_http_read_only(self, hass):
        coordinator = _make_coordinator(
            hass, [HTTP_MONITOR_UP], read_only_types={"http"}
        )
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == 0

    async def test_no_switch_when_push_read_only(self, hass):
        coordinator = _make_coordinator(
            hass, [PUSH_MONITOR_UP], read_only_types={"push"}
        )
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == 0

    async def test_read_only_flags_are_per_type(self, hass):
        coordinator = _make_coordinator(
            hass,
            [HTTP_MONITOR_UP, PUSH_MONITOR_UP],
            read_only_types={"http"},
        )
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == 1
        assert "push" in entities[0].unique_id


class TestEnabledSwitchActions:
    async def test_turn_on_patches_http_monitor(self, hass):
        coordinator = _make_coordinator(hass, [{**HTTP_MONITOR_UP, "enabled": False}])
        coordinator.async_request_refresh = AsyncMock()
        entities = await _setup_integration(hass, coordinator)

        await entities[0].async_turn_on()

        coordinator.client.patch_monitor.assert_awaited_once_with(
            MONITOR_TYPES_BY_KEY["http"], 1, {"enabled": True}
        )
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_turn_off_patches_http_monitor(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        coordinator.async_request_refresh = AsyncMock()
        entities = await _setup_integration(hass, coordinator)

        await entities[0].async_turn_off()

        coordinator.client.patch_monitor.assert_awaited_once_with(
            MONITOR_TYPES_BY_KEY["http"], 1, {"enabled": False}
        )
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_turn_on_patches_push_monitor(self, hass):
        coordinator = _make_coordinator(hass, [{**PUSH_MONITOR_UP, "enabled": False}])
        coordinator.async_request_refresh = AsyncMock()
        entities = await _setup_integration(hass, coordinator)

        await entities[0].async_turn_on()

        coordinator.client.patch_monitor.assert_awaited_once_with(
            MONITOR_TYPES_BY_KEY["push"], 20, {"enabled": True}
        )
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_turn_off_patches_push_monitor(self, hass):
        coordinator = _make_coordinator(hass, [PUSH_MONITOR_UP])
        coordinator.async_request_refresh = AsyncMock()
        entities = await _setup_integration(hass, coordinator)

        await entities[0].async_turn_off()

        coordinator.client.patch_monitor.assert_awaited_once_with(
            MONITOR_TYPES_BY_KEY["push"], 20, {"enabled": False}
        )
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_turn_on_patches_icmp_monitor(self, hass):
        coordinator = _make_coordinator(hass, [{**ICMP_MONITOR_UP, "enabled": False}])
        coordinator.async_request_refresh = AsyncMock()
        entities = await _setup_integration(hass, coordinator)

        await entities[0].async_turn_on()

        coordinator.client.patch_monitor.assert_awaited_once_with(
            MONITOR_TYPES_BY_KEY["icmp"], 30, {"enabled": True}
        )
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_turn_off_patches_icmp_monitor(self, hass):
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_UP])
        coordinator.async_request_refresh = AsyncMock()
        entities = await _setup_integration(hass, coordinator)

        await entities[0].async_turn_off()

        coordinator.client.patch_monitor.assert_awaited_once_with(
            MONITOR_TYPES_BY_KEY["icmp"], 30, {"enabled": False}
        )
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_no_switch_when_icmp_read_only(self, hass):
        coordinator = _make_coordinator(
            hass, [ICMP_MONITOR_UP], read_only_types={"icmp"}
        )
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == 0

    async def test_icmp_unique_id_format(self, hass):
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)
        assert (
            entities[0].unique_id == "kuvasz_uptime_test_entry_icmp_30_enabled_switch"
        )


class TestTcpSwitch:
    async def test_turn_on_patches_tcp_monitor(self, hass):
        coordinator = _make_coordinator(hass, [{**TCP_MONITOR_UP, "enabled": False}])
        coordinator.async_request_refresh = AsyncMock()
        entities = await _setup_integration(hass, coordinator)

        await entities[0].async_turn_on()

        coordinator.client.patch_monitor.assert_awaited_once_with(
            MONITOR_TYPES_BY_KEY["tcp"], 40, {"enabled": True}
        )
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_turn_off_patches_tcp_monitor(self, hass):
        coordinator = _make_coordinator(hass, [TCP_MONITOR_UP])
        coordinator.async_request_refresh = AsyncMock()
        entities = await _setup_integration(hass, coordinator)

        await entities[0].async_turn_off()

        coordinator.client.patch_monitor.assert_awaited_once_with(
            MONITOR_TYPES_BY_KEY["tcp"], 40, {"enabled": False}
        )
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_no_switch_when_tcp_read_only(self, hass):
        coordinator = _make_coordinator(hass, [TCP_MONITOR_UP], read_only_types={"tcp"})
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == 0

    async def test_tcp_unique_id_format(self, hass):
        coordinator = _make_coordinator(hass, [TCP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)
        assert entities[0].unique_id == "kuvasz_uptime_test_entry_tcp_40_enabled_switch"


class TestDnsSwitch:
    async def test_turn_on_patches_dns_monitor(self, hass):
        coordinator = _make_coordinator(hass, [{**DNS_MONITOR_UP, "enabled": False}])
        coordinator.async_request_refresh = AsyncMock()
        entities = await _setup_integration(hass, coordinator)

        await entities[0].async_turn_on()

        coordinator.client.patch_monitor.assert_awaited_once_with(
            MONITOR_TYPES_BY_KEY["dns"], 50, {"enabled": True}
        )
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_turn_off_patches_dns_monitor(self, hass):
        coordinator = _make_coordinator(hass, [DNS_MONITOR_UP])
        coordinator.async_request_refresh = AsyncMock()
        entities = await _setup_integration(hass, coordinator)

        await entities[0].async_turn_off()

        coordinator.client.patch_monitor.assert_awaited_once_with(
            MONITOR_TYPES_BY_KEY["dns"], 50, {"enabled": False}
        )
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_no_switch_when_dns_read_only(self, hass):
        coordinator = _make_coordinator(hass, [DNS_MONITOR_UP], read_only_types={"dns"})
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == 0

    async def test_dns_unique_id_format(self, hass):
        coordinator = _make_coordinator(hass, [DNS_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)
        assert entities[0].unique_id == "kuvasz_uptime_test_entry_dns_50_enabled_switch"
