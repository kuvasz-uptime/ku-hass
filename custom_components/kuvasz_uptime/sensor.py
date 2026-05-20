"""Sensors for Kuvasz monitor statistics and status timestamps."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MONITOR_TYPE_HTTP, MONITOR_TYPE_PUSH
from .coordinator import KuvaszCoordinator
from .entity import KuvaszMonitorEntity


@dataclass(frozen=True)
class KuvaszTimestampSensorDescription:
    key: str
    translation_key: str
    monitor_data_key: str
    applicable_types: tuple[str, ...]
    requires_ssl_check: bool = False


TIMESTAMP_SENSOR_DESCRIPTIONS: tuple[KuvaszTimestampSensorDescription, ...] = (
    KuvaszTimestampSensorDescription(
        key="uptime_status_started_at",
        translation_key="uptime_status_started_at",
        monitor_data_key="uptimeStatusStartedAt",
        applicable_types=(MONITOR_TYPE_HTTP, MONITOR_TYPE_PUSH),
    ),
    KuvaszTimestampSensorDescription(
        key="last_uptime_check",
        translation_key="last_uptime_check",
        monitor_data_key="lastUptimeCheck",
        applicable_types=(MONITOR_TYPE_HTTP, MONITOR_TYPE_PUSH),
    ),
    KuvaszTimestampSensorDescription(
        key="next_uptime_check",
        translation_key="next_uptime_check",
        monitor_data_key="nextUptimeCheck",
        applicable_types=(MONITOR_TYPE_HTTP,),
    ),
    KuvaszTimestampSensorDescription(
        key="ssl_status_started_at",
        translation_key="ssl_status_started_at",
        monitor_data_key="sslStatusStartedAt",
        applicable_types=(MONITOR_TYPE_HTTP,),
        requires_ssl_check=True,
    ),
    KuvaszTimestampSensorDescription(
        key="last_ssl_check",
        translation_key="last_ssl_check",
        monitor_data_key="lastSSLCheck",
        applicable_types=(MONITOR_TYPE_HTTP,),
        requires_ssl_check=True,
    ),
    KuvaszTimestampSensorDescription(
        key="next_ssl_check",
        translation_key="next_ssl_check",
        monitor_data_key="nextSSLCheck",
        applicable_types=(MONITOR_TYPE_HTTP,),
        requires_ssl_check=True,
    ),
    KuvaszTimestampSensorDescription(
        key="ssl_valid_until",
        translation_key="ssl_valid_until",
        monitor_data_key="sslValidUntil",
        applicable_types=(MONITOR_TYPE_HTTP,),
        requires_ssl_check=True,
    ),
    KuvaszTimestampSensorDescription(
        key="last_heartbeat",
        translation_key="last_heartbeat",
        monitor_data_key="lastHeartbeat",
        applicable_types=(MONITOR_TYPE_PUSH,),
    ),
    KuvaszTimestampSensorDescription(
        key="next_expected_heartbeat",
        translation_key="next_expected_heartbeat",
        monitor_data_key="nextExpectedHeartbeat",
        applicable_types=(MONITOR_TYPE_PUSH,),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: KuvaszCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    for monitor in coordinator.data.monitors:
        monitor_type = monitor["_type"]
        entities.append(KuvaszUptimePercentageSensor(coordinator, monitor))
        if monitor_type == MONITOR_TYPE_HTTP and monitor.get("latencyHistoryEnabled"):
            entities.append(KuvaszAvgResponseTimeSensor(coordinator, monitor))
        for desc in TIMESTAMP_SENSOR_DESCRIPTIONS:
            if monitor_type not in desc.applicable_types:
                continue
            if desc.requires_ssl_check and not monitor.get("sslCheckEnabled"):
                continue
            entities.append(KuvaszTimestampSensor(coordinator, monitor, desc))

    async_add_entities(entities)


class KuvaszUptimePercentageSensor(KuvaszMonitorEntity, SensorEntity):
    """Sensor reporting uptime percentage over the last 24 hours."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 2
    _attr_translation_key = "uptime_ratio"

    def __init__(self, coordinator: KuvaszCoordinator, monitor: dict[str, Any]) -> None:
        super().__init__(coordinator, monitor)
        self._attr_unique_id = f"{DOMAIN}_{self._monitor_type}_{self._monitor_id}_uptime_ratio"
        self.entity_id = self._build_entity_id("sensor", "uptime_ratio")

    @property
    def native_value(self) -> float | None:
        ratio = self._monitor_stats.get("uptimeHistory", {}).get("uptimeRatio")
        if ratio is None:
            return None
        return round(ratio * 100, 4)


class KuvaszAvgResponseTimeSensor(KuvaszMonitorEntity, SensorEntity):
    """Sensor reporting average response time for HTTP monitors."""

    _attr_native_unit_of_measurement = UnitOfTime.MILLISECONDS
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
    _attr_translation_key = "average_latency_in_ms"

    def __init__(self, coordinator: KuvaszCoordinator, monitor: dict[str, Any]) -> None:
        super().__init__(coordinator, monitor)
        self._attr_unique_id = f"{DOMAIN}_{self._monitor_type}_{self._monitor_id}_average_latency_in_ms"
        self.entity_id = self._build_entity_id("sensor", "average_latency_in_ms")

    @property
    def native_value(self) -> float | None:
        latency_stats = self._monitor_stats.get("latencyStats")
        if latency_stats is None:
            return None
        return latency_stats.get("averageLatencyInMs")


class KuvaszTimestampSensor(KuvaszMonitorEntity, SensorEntity):
    """Sensor reporting a datetime field from a monitor's details."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: KuvaszCoordinator,
        monitor: dict[str, Any],
        description: KuvaszTimestampSensorDescription,
    ) -> None:
        super().__init__(coordinator, monitor)
        self._description = description
        self._attr_unique_id = f"{DOMAIN}_{self._monitor_type}_{self._monitor_id}_{description.key}"
        self._attr_translation_key = description.translation_key
        self.entity_id = self._build_entity_id("sensor", description.key)

    @property
    def native_value(self) -> datetime | None:
        raw = self._monitor_data.get(self._description.monitor_data_key)
        if raw is None:
            return None
        return datetime.fromisoformat(raw)
