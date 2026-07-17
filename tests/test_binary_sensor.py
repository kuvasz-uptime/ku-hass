"""Tests for Kuvasz binary sensors."""

from unittest.mock import MagicMock

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from custom_components.kuvasz_uptime.api import KuvaszClient
from custom_components.kuvasz_uptime.const import DOMAIN
from custom_components.kuvasz_uptime.coordinator import (
    KuvaszCoordinator,
    KuvaszCoordinatorData,
)
from tests.conftest import (
    HTTP_MONITOR_DOWN,
    HTTP_MONITOR_NO_SSL,
    HTTP_MONITOR_UP,
    ICMP_MONITOR_DOWN,
    ICMP_MONITOR_UP,
    PUSH_MONITOR_UP,
    TCP_MONITOR_DOWN,
    TCP_MONITOR_UP,
)


def _make_coordinator(hass, monitors, stats_map=None):
    client = MagicMock(spec=KuvaszClient)
    coordinator = KuvaszCoordinator(
        hass, client, scan_interval=30, entry_id="test_entry"
    )
    coordinator.data = KuvaszCoordinatorData(
        monitors=monitors,
        stats=stats_map or {},
    )
    return coordinator


async def _setup_integration(hass, coordinator):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["test_entry"] = coordinator

    from homeassistant.config_entries import ConfigEntry

    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry"
    entry.domain = DOMAIN

    from custom_components.kuvasz_uptime.binary_sensor import async_setup_entry

    entities = []

    def async_add(ents):
        return entities.extend(ents)

    await async_setup_entry(hass, entry, async_add)
    return entities


class TestUptimeBinarySensor:
    async def test_http_monitor_up_is_on(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.is_on is True

    async def test_http_monitor_down_is_off(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_DOWN])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.is_on is False

    async def test_paused_uptime_status_is_not_up(self, hass):
        monitor = {**HTTP_MONITOR_UP, "uptimeStatus": "PAUSED"}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.is_on is False

    async def test_in_progress_uptime_status_is_not_up(self, hass):
        monitor = {**HTTP_MONITOR_UP, "uptimeStatus": "IN_PROGRESS"}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.is_on is False

    async def test_missing_uptime_status_returns_none(self, hass):
        monitor = {**HTTP_MONITOR_UP, "uptimeStatus": None}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.is_on is None

    async def test_push_monitor_creates_uptime_sensor(self, hass):
        coordinator = _make_coordinator(hass, [PUSH_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        # uptime + enabled = 2 entities for push monitors
        assert len(entities) == 2
        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.is_on is True

    async def test_unique_id_format(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.unique_id == "kuvasz_uptime_test_entry_http_1_uptime_status"

    async def test_device_class_is_connectivity(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.device_class == BinarySensorDeviceClass.CONNECTIVITY

    async def test_device_info_uses_monitor_name(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.device_info["name"] == "My Website"
        assert (DOMAIN, "test_entry_http_1") in uptime.device_info["identifiers"]


class TestSslBinarySensor:
    async def test_ssl_sensor_created_when_ssl_check_enabled(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        ssl_entities = [e for e in entities if "ssl" in e.unique_id]
        assert len(ssl_entities) == 1

    async def test_no_ssl_sensor_when_ssl_check_disabled(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_NO_SSL])
        entities = await _setup_integration(hass, coordinator)

        ssl_entities = [e for e in entities if "ssl" in e.unique_id]
        assert len(ssl_entities) == 0

    async def test_ssl_valid_is_off(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        ssl = next(e for e in entities if "ssl" in e.unique_id)
        assert ssl.is_on is False

    async def test_ssl_invalid_is_on(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_DOWN])
        entities = await _setup_integration(hass, coordinator)

        ssl = next(e for e in entities if "ssl" in e.unique_id)
        assert ssl.is_on is True

    async def test_ssl_will_expire_is_off(self, hass):
        monitor = {**HTTP_MONITOR_UP, "sslStatus": "WILL_EXPIRE"}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        ssl = next(e for e in entities if "ssl" in e.unique_id)
        assert ssl.is_on is False

    async def test_ssl_none_status_returns_none(self, hass):
        monitor = {**HTTP_MONITOR_UP, "sslStatus": None}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        ssl = next(e for e in entities if "ssl" in e.unique_id)
        assert ssl.is_on is None

    async def test_ssl_extra_state_attributes(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        ssl = next(e for e in entities if "ssl" in e.unique_id)
        attrs = ssl.extra_state_attributes
        assert attrs["ssl_status"] == "VALID"
        assert attrs["ssl_error"] is None
        assert attrs["ssl_expiry_threshold"] == 30
        assert attrs["ssl_status_started_at"] == "2024-01-01T00:00:00Z"
        assert attrs["last_ssl_check"] == "2024-01-01T01:00:00Z"
        assert attrs["next_ssl_check"] == "2024-01-01T01:01:00Z"
        assert attrs["ssl_valid_until"] == "2025-01-01T00:00:00Z"

    async def test_unique_id_format(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        ssl = next(e for e in entities if "ssl" in e.unique_id)
        assert ssl.unique_id == "kuvasz_uptime_test_entry_http_1_ssl_status"

    async def test_push_monitor_has_no_ssl_sensor(self, hass):
        coordinator = _make_coordinator(hass, [PUSH_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        ssl_entities = [e for e in entities if "ssl" in e.unique_id]
        assert len(ssl_entities) == 0


class TestUptimeBinarySensorAttributes:
    async def test_http_uptime_attributes_common(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        attrs = uptime.extra_state_attributes
        assert attrs["failure_count_threshold"] == 1
        assert attrs["uptime_error"] is None
        assert attrs["uptime_status_started_at"] == "2024-01-01T00:00:00Z"
        assert attrs["last_uptime_check"] == "2024-01-01T01:00:00Z"
        assert attrs["created_at"] == "2024-01-01T00:00:00Z"
        assert attrs["updated_at"] is None

    async def test_http_uptime_attributes_http_specific(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        attrs = uptime.extra_state_attributes
        assert attrs["url"] == "https://example.com"
        assert attrs["next_uptime_check"] == "2024-01-01T01:01:00Z"
        assert attrs["uptime_check_interval"] == 60
        assert attrs["request_method"] == "GET"
        assert attrs["follow_redirects"] is True
        assert attrs["force_no_cache"] is False
        assert attrs["latency_history_enabled"] is True
        assert attrs["expected_status_codes"] == [200]
        assert attrs["response_time_threshold_millis"] is None
        assert attrs["expected_keyword"] is None
        assert attrs["expected_keyword_case_sensitive"] is False
        assert attrs["expected_keyword_negated"] is False

    async def test_http_uptime_hides_url_when_sensitive(self, hass):
        monitor = {**HTTP_MONITOR_UP, "sensitiveUrl": True}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert "url" not in uptime.extra_state_attributes

    async def test_push_uptime_attributes(self, hass):
        coordinator = _make_coordinator(hass, [PUSH_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        attrs = uptime.extra_state_attributes
        assert attrs["next_expected_heartbeat"] == "2024-01-01T01:05:00Z"
        assert attrs["heartbeat_interval"] == 300
        assert attrs["grace_period"] == 60
        assert attrs["failure_count_threshold"] == 1
        assert "url" not in attrs
        assert "request_method" not in attrs

    async def test_push_uptime_attributes_no_http_fields(self, hass):
        coordinator = _make_coordinator(hass, [PUSH_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        attrs = uptime.extra_state_attributes
        assert "uptime_check_interval" not in attrs
        assert "expected_status_codes" not in attrs


class TestEnabledBinarySensor:
    async def test_enabled_monitor_is_on(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        enabled = next(e for e in entities if "enabled" in e.unique_id)
        assert enabled.is_on is True

    async def test_disabled_monitor_is_off(self, hass):
        monitor = {**HTTP_MONITOR_UP, "enabled": False}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        enabled = next(e for e in entities if "enabled" in e.unique_id)
        assert enabled.is_on is False

    async def test_none_enabled_returns_none(self, hass):
        monitor = {**HTTP_MONITOR_UP, "enabled": None}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        enabled = next(e for e in entities if "enabled" in e.unique_id)
        assert enabled.is_on is None

    async def test_unique_id_format_http(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        enabled = next(e for e in entities if "enabled" in e.unique_id)
        assert enabled.unique_id == "kuvasz_uptime_test_entry_http_1_enabled"

    async def test_unique_id_format_push(self, hass):
        coordinator = _make_coordinator(hass, [PUSH_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        enabled = next(e for e in entities if "enabled" in e.unique_id)
        assert enabled.unique_id == "kuvasz_uptime_test_entry_push_20_enabled"

    async def test_created_for_every_monitor(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP, PUSH_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        enabled_entities = [e for e in entities if "enabled" in e.unique_id]
        assert len(enabled_entities) == 2


class TestMultipleMonitors:
    async def test_mixed_monitor_types_entity_count(self, hass):
        # HTTP (SSL enabled): 3 entities (uptime + enabled + ssl)
        # Push: 2 entities (uptime + enabled)
        # ICMP: 2 entities (uptime + enabled)
        coordinator = _make_coordinator(
            hass, [HTTP_MONITOR_UP, PUSH_MONITOR_UP, ICMP_MONITOR_UP]
        )
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == 7

    async def test_entity_unique_ids_are_unique(self, hass):
        coordinator = _make_coordinator(
            hass, [HTTP_MONITOR_UP, HTTP_MONITOR_DOWN, PUSH_MONITOR_UP, ICMP_MONITOR_UP]
        )
        entities = await _setup_integration(hass, coordinator)
        ids = [e.unique_id for e in entities]
        assert len(ids) == len(set(ids))


class TestIcmpBinarySensor:
    async def test_icmp_monitor_up_is_on(self, hass):
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.is_on is True

    async def test_icmp_monitor_down_is_off(self, hass):
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_DOWN])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.is_on is False

    async def test_icmp_monitor_creates_uptime_and_enabled_sensors(self, hass):
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        assert len(entities) == 2

    async def test_icmp_monitor_has_no_ssl_sensor(self, hass):
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        ssl_entities = [e for e in entities if "ssl" in e.unique_id]
        assert len(ssl_entities) == 0

    async def test_icmp_uptime_attributes(self, hass):
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        attrs = uptime.extra_state_attributes
        assert attrs["host"] == "192.168.1.1"
        assert attrs["next_uptime_check"] == "2024-01-01T01:01:00Z"
        assert attrs["uptime_check_interval"] == 60
        assert attrs["packet_count"] == 3
        assert attrs["timeout_seconds"] == 5
        assert attrs["packet_loss_threshold"] == 100
        assert attrs["metrics_history_enabled"] is True
        assert attrs["failure_count_threshold"] == 1
        assert "url" not in attrs
        assert "heartbeat_interval" not in attrs

    async def test_icmp_unique_id_format(self, hass):
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.unique_id == "kuvasz_uptime_test_entry_icmp_30_uptime_status"


class TestTcpBinarySensor:
    async def test_tcp_monitor_up_is_on(self, hass):
        coordinator = _make_coordinator(hass, [TCP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.is_on is True

    async def test_tcp_monitor_down_is_off(self, hass):
        coordinator = _make_coordinator(hass, [TCP_MONITOR_DOWN])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.is_on is False

    async def test_tcp_monitor_creates_uptime_and_enabled_sensors(self, hass):
        coordinator = _make_coordinator(hass, [TCP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        assert len(entities) == 2

    async def test_tcp_monitor_has_no_ssl_sensor(self, hass):
        coordinator = _make_coordinator(hass, [TCP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        ssl_entities = [e for e in entities if "ssl" in e.unique_id]
        assert len(ssl_entities) == 0

    async def test_tcp_uptime_attributes(self, hass):
        coordinator = _make_coordinator(hass, [TCP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        attrs = uptime.extra_state_attributes
        assert attrs["host"] == "192.168.1.2"
        assert attrs["port"] == 5432
        assert attrs["next_uptime_check"] == "2024-01-01T01:01:00Z"
        assert attrs["uptime_check_interval"] == 60
        assert attrs["timeout_ms"] == 5000
        assert attrs["latency_threshold_ms"] == 1000
        assert attrs["metrics_history_enabled"] is True
        assert attrs["failure_count_threshold"] == 1
        assert "url" not in attrs
        assert "packet_count" not in attrs

    async def test_tcp_latency_threshold_may_be_absent(self, hass):
        """latencyThresholdMs is nullable in the API."""
        monitor = {**TCP_MONITOR_UP, "latencyThresholdMs": None}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.extra_state_attributes["latency_threshold_ms"] is None

    async def test_tcp_unique_id_format(self, hass):
        coordinator = _make_coordinator(hass, [TCP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        uptime = next(e for e in entities if "_uptime_status" in e.unique_id)
        assert uptime.unique_id == "kuvasz_uptime_test_entry_tcp_40_uptime_status"
