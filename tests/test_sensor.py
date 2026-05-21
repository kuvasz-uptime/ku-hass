"""Tests for Kuvasz sensors."""
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import PERCENTAGE

from custom_components.kuvasz_uptime.api import KuvaszClient
from custom_components.kuvasz_uptime.const import DOMAIN
from custom_components.kuvasz_uptime.coordinator import KuvaszCoordinator, KuvaszCoordinatorData
from tests.conftest import (
    HTTP_MONITOR_UP,
    HTTP_MONITOR_DOWN,
    HTTP_MONITOR_NO_SSL,
    ICMP_MONITOR_UP,
    ICMP_MONITOR_STATS,
    PUSH_MONITOR_UP,
    HTTP_MONITOR_STATS,
    HTTP_MONITOR_STATS_NO_LATENCY,
    PUSH_MONITOR_STATS,
)

# Entity counts per monitor type (from sensor.py only):
#   HTTP with SSL:             uptime_pct + avg_response + 7 timestamp sensors = 9
#   HTTP without SSL:          uptime_pct + avg_response + 3 timestamp sensors = 5
#   Push:                      uptime_pct + 4 timestamp sensors               = 5
#   ICMP (metrics enabled):    uptime_pct + avg_response + avg_pkt_loss + 3 timestamp sensors = 6
#   ICMP (metrics disabled):   uptime_pct + 3 timestamp sensors               = 4
HTTP_SSL_SENSOR_COUNT = 9
HTTP_NO_SSL_SENSOR_COUNT = 5
PUSH_SENSOR_COUNT = 5
ICMP_METRICS_SENSOR_COUNT = 6
ICMP_NO_METRICS_SENSOR_COUNT = 4


def _make_coordinator(hass, monitors, stats_map=None):
    client = MagicMock(spec=KuvaszClient)
    coordinator = KuvaszCoordinator(hass, client, scan_interval=30)
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

    from custom_components.kuvasz_uptime.sensor import async_setup_entry
    entities = []
    async_add = lambda ents: entities.extend(ents)
    await async_setup_entry(hass, entry, async_add)
    return entities


class TestUptimePercentageSensor:
    async def test_http_monitor_uptime_percentage(self, hass):
        stats = {"http_1": HTTP_MONITOR_STATS}
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP], stats_map=stats)
        entities = await _setup_integration(hass, coordinator)

        pct = next(e for e in entities if "uptime_ratio" in e.unique_id)
        assert pct.native_value == pytest.approx(99.87, abs=0.001)

    async def test_uptime_ratio_of_1_gives_100_percent(self, hass):
        stats = {"push_20": {"uptimeHistory": {"uptimeRatio": 1.0}}}
        coordinator = _make_coordinator(hass, [PUSH_MONITOR_UP], stats_map=stats)
        entities = await _setup_integration(hass, coordinator)

        pct = next(e for e in entities if "uptime_ratio" in e.unique_id)
        assert pct.native_value == pytest.approx(100.0)

    async def test_uptime_ratio_none_returns_none(self, hass):
        stats = {"push_20": PUSH_MONITOR_STATS}
        coordinator = _make_coordinator(hass, [PUSH_MONITOR_UP], stats_map=stats)
        entities = await _setup_integration(hass, coordinator)

        pct = next(e for e in entities if "uptime_ratio" in e.unique_id)
        assert pct.native_value is None

    async def test_missing_stats_returns_none(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP], stats_map={})
        entities = await _setup_integration(hass, coordinator)

        pct = next(e for e in entities if "uptime_ratio" in e.unique_id)
        assert pct.native_value is None

    async def test_unit_is_percentage(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        pct = next(e for e in entities if "uptime_ratio" in e.unique_id)
        assert pct.native_unit_of_measurement == PERCENTAGE

    async def test_state_class_is_measurement(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        pct = next(e for e in entities if "uptime_ratio" in e.unique_id)
        assert pct.state_class == SensorStateClass.MEASUREMENT

    async def test_unique_id_format(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        pct = next(e for e in entities if "uptime_ratio" in e.unique_id)
        assert pct.unique_id == "kuvasz_uptime_http_1_uptime_ratio"

    async def test_uptime_created_for_all_monitor_types(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP, PUSH_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        pct_sensors = [e for e in entities if "uptime_ratio" in e.unique_id]
        assert len(pct_sensors) == 2


class TestAvgResponseTimeSensor:
    async def test_http_monitor_avg_response_time(self, hass):
        stats = {"http_1": HTTP_MONITOR_STATS}
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP], stats_map=stats)
        entities = await _setup_integration(hass, coordinator)

        rt = next(e for e in entities if "average_latency_in_ms" in e.unique_id)
        assert rt.native_value == 123

    async def test_no_latency_stats_returns_none(self, hass):
        stats = {"http_2": HTTP_MONITOR_STATS_NO_LATENCY}
        monitor = {**HTTP_MONITOR_DOWN, "id": 2}
        coordinator = _make_coordinator(hass, [monitor], stats_map=stats)
        entities = await _setup_integration(hass, coordinator)

        rt = next(e for e in entities if "average_latency_in_ms" in e.unique_id)
        assert rt.native_value is None

    async def test_missing_stats_returns_none(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP], stats_map={})
        entities = await _setup_integration(hass, coordinator)

        rt = next(e for e in entities if "average_latency_in_ms" in e.unique_id)
        assert rt.native_value is None

    async def test_device_class_is_duration(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        rt = next(e for e in entities if "average_latency_in_ms" in e.unique_id)
        assert rt.device_class == SensorDeviceClass.DURATION

    async def test_unique_id_format(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        rt = next(e for e in entities if "average_latency_in_ms" in e.unique_id)
        assert rt.unique_id == "kuvasz_uptime_http_1_average_latency_in_ms"

    async def test_only_created_for_http_monitors(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP, PUSH_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        rt_sensors = [e for e in entities if "average_latency_in_ms" in e.unique_id]
        assert len(rt_sensors) == 1
        assert "http" in rt_sensors[0].unique_id

    async def test_not_created_when_latency_history_disabled(self, hass):
        monitor = {**HTTP_MONITOR_UP, "latencyHistoryEnabled": False}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        rt_sensors = [e for e in entities if "average_latency_in_ms" in e.unique_id]
        assert len(rt_sensors) == 0


class TestTimestampSensors:
    async def test_http_monitor_creates_all_timestamp_sensors(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        expected_keys = {
            "uptime_status_started_at", "last_uptime_check", "next_uptime_check",
            "ssl_status_started_at", "last_ssl_check", "next_ssl_check", "ssl_valid_until",
        }
        ts_ids = {e.unique_id for e in entities if e.device_class == SensorDeviceClass.TIMESTAMP}
        assert all(f"http_1_{k}" in uid for k in expected_keys for uid in ts_ids if k in uid)
        assert len(ts_ids) == 7

    async def test_http_monitor_no_ssl_skips_ssl_timestamp_sensors(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_NO_SSL])
        entities = await _setup_integration(hass, coordinator)

        ts_entities = [e for e in entities if e.device_class == SensorDeviceClass.TIMESTAMP]
        ts_keys = [e.unique_id for e in ts_entities]
        assert len(ts_entities) == 3
        assert not any("ssl" in uid for uid in ts_keys)

    async def test_push_monitor_creates_heartbeat_timestamp_sensors(self, hass):
        coordinator = _make_coordinator(hass, [PUSH_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        ts_entities = [e for e in entities if e.device_class == SensorDeviceClass.TIMESTAMP]
        ts_keys = [e.unique_id for e in ts_entities]
        assert len(ts_entities) == 4
        assert any("last_heartbeat" in uid for uid in ts_keys)
        assert any("next_expected_heartbeat" in uid for uid in ts_keys)

    async def test_timestamp_sensor_parses_iso_string(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        last_check = next(e for e in entities if "last_uptime_check" in e.unique_id)
        value = last_check.native_value
        assert isinstance(value, datetime)
        assert value.tzinfo is not None

    async def test_timestamp_sensor_returns_none_for_null_field(self, hass):
        monitor = {**HTTP_MONITOR_UP, "lastUptimeCheck": None}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        last_check = next(e for e in entities if "last_uptime_check" in e.unique_id)
        assert last_check.native_value is None

    async def test_ssl_expires_sensor_value(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        ssl_exp = next(e for e in entities if "ssl_valid_until" in e.unique_id)
        assert ssl_exp.native_value == datetime.fromisoformat("2025-01-01T00:00:00Z")

    async def test_push_last_heartbeat_sensor_value(self, hass):
        coordinator = _make_coordinator(hass, [PUSH_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        heartbeat = next(e for e in entities if "last_heartbeat" in e.unique_id)
        assert heartbeat.native_value == datetime.fromisoformat("2024-01-01T01:00:00Z")

    async def test_push_next_expected_heartbeat_sensor_value(self, hass):
        coordinator = _make_coordinator(hass, [PUSH_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        neh = next(e for e in entities if "next_expected_heartbeat" in e.unique_id)
        assert neh.native_value == datetime.fromisoformat("2024-01-01T01:05:00Z")

    async def test_timestamp_sensor_device_class(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        ts = next(e for e in entities if "last_uptime_check" in e.unique_id)
        assert ts.device_class == SensorDeviceClass.TIMESTAMP


class TestSensorEntityCount:
    async def test_http_monitor_with_ssl_sensor_count(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == HTTP_SSL_SENSOR_COUNT

    async def test_http_monitor_without_ssl_sensor_count(self, hass):
        coordinator = _make_coordinator(hass, [HTTP_MONITOR_NO_SSL])
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == HTTP_NO_SSL_SENSOR_COUNT

    async def test_push_monitor_sensor_count(self, hass):
        coordinator = _make_coordinator(hass, [PUSH_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == PUSH_SENSOR_COUNT

    async def test_sensor_unique_ids_are_unique_across_all_monitors(self, hass):
        coordinator = _make_coordinator(
            hass, [HTTP_MONITOR_UP, HTTP_MONITOR_DOWN, PUSH_MONITOR_UP, ICMP_MONITOR_UP]
        )
        entities = await _setup_integration(hass, coordinator)
        ids = [e.unique_id for e in entities]
        assert len(ids) == len(set(ids))

    async def test_icmp_monitor_with_metrics_sensor_count(self, hass):
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == ICMP_METRICS_SENSOR_COUNT

    async def test_icmp_monitor_without_metrics_sensor_count(self, hass):
        monitor = {**ICMP_MONITOR_UP, "metricsHistoryEnabled": False}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == ICMP_NO_METRICS_SENSOR_COUNT


class TestIcmpSensors:
    async def test_icmp_uptime_percentage(self, hass):
        stats = {"icmp_30": ICMP_MONITOR_STATS}
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_UP], stats_map=stats)
        entities = await _setup_integration(hass, coordinator)

        pct = next(e for e in entities if "uptime_ratio" in e.unique_id)
        assert pct.native_value == pytest.approx(99.99, abs=0.001)

    async def test_icmp_avg_latency_sensor(self, hass):
        stats = {"icmp_30": ICMP_MONITOR_STATS}
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_UP], stats_map=stats)
        entities = await _setup_integration(hass, coordinator)

        rt = next(e for e in entities if "average_latency_in_ms" in e.unique_id)
        assert rt.native_value == 10

    async def test_icmp_avg_latency_not_created_when_metrics_disabled(self, hass):
        monitor = {**ICMP_MONITOR_UP, "metricsHistoryEnabled": False}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        rt_sensors = [e for e in entities if "average_latency_in_ms" in e.unique_id]
        assert len(rt_sensors) == 0

    async def test_icmp_avg_packet_loss_sensor(self, hass):
        stats = {"icmp_30": ICMP_MONITOR_STATS}
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_UP], stats_map=stats)
        entities = await _setup_integration(hass, coordinator)

        pkt = next(e for e in entities if "average_packet_loss" in e.unique_id)
        assert pkt.native_value == 0

    async def test_icmp_avg_packet_loss_not_created_when_metrics_disabled(self, hass):
        monitor = {**ICMP_MONITOR_UP, "metricsHistoryEnabled": False}
        coordinator = _make_coordinator(hass, [monitor])
        entities = await _setup_integration(hass, coordinator)

        pkt_sensors = [e for e in entities if "average_packet_loss" in e.unique_id]
        assert len(pkt_sensors) == 0

    async def test_icmp_avg_packet_loss_none_when_no_stats(self, hass):
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_UP], stats_map={})
        entities = await _setup_integration(hass, coordinator)

        pkt = next(e for e in entities if "average_packet_loss" in e.unique_id)
        assert pkt.native_value is None

    async def test_icmp_timestamp_sensors_created(self, hass):
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        ts_ids = {e.unique_id for e in entities if e.device_class == SensorDeviceClass.TIMESTAMP}
        assert any("uptime_status_started_at" in uid for uid in ts_ids)
        assert any("last_uptime_check" in uid for uid in ts_ids)
        assert any("next_uptime_check" in uid for uid in ts_ids)
        assert len(ts_ids) == 3

    async def test_icmp_unique_id_format(self, hass):
        coordinator = _make_coordinator(hass, [ICMP_MONITOR_UP])
        entities = await _setup_integration(hass, coordinator)

        pct = next(e for e in entities if "uptime_ratio" in e.unique_id)
        assert pct.unique_id == "kuvasz_uptime_icmp_30_uptime_ratio"

        pkt = next(e for e in entities if "average_packet_loss" in e.unique_id)
        assert pkt.unique_id == "kuvasz_uptime_icmp_30_average_packet_loss"
