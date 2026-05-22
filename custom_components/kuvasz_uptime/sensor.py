"""Sensors for Kuvasz monitor statistics and status timestamps."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTime

from .const import DOMAIN, MONITOR_TYPE_HTTP, MONITOR_TYPE_ICMP, MONITOR_TYPE_PUSH
from .entity import KuvaszMonitorEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import KuvaszCoordinator


@dataclass(frozen=True)
class KuvaszTimestampSensorDescription:
    """Describes a timestamp sensor with its data key and visibility rule."""

    key: str
    translation_key: str
    monitor_data_key: str
    applicable_types: tuple[str, ...]
    requires_ssl_check: bool = False


TIMESTAMP_SENSOR_DESCRIPTIONS: tuple[KuvaszTimestampSensorDescription, ...] = (
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
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kuvasz sensors for a config entry."""
    coordinator: KuvaszCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = []

    for monitor in coordinator.data.monitors:
        monitor_type = monitor["_type"]
        entities.append(KuvaszUptimePercentageSensor(coordinator, monitor))
        if monitor_type == MONITOR_TYPE_HTTP and monitor.get("latencyHistoryEnabled"):
            entities.append(KuvaszAvgResponseTimeSensor(coordinator, monitor))
        if monitor_type == MONITOR_TYPE_ICMP and monitor.get("metricsHistoryEnabled"):
            entities.append(KuvaszAvgResponseTimeSensor(coordinator, monitor))
            entities.append(KuvaszAvgPacketLossSensor(coordinator, monitor))
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
        """Initialize the uptime percentage sensor."""
        super().__init__(coordinator, monitor)
        self._attr_unique_id = self._build_unique_id("uptime_ratio")
        self.entity_id = self._build_entity_id("sensor", "uptime_ratio")

    @property
    def native_value(self) -> float | None:
        """Return uptime ratio as a percentage (0-100)."""
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
        """Initialize the average response time sensor."""
        super().__init__(coordinator, monitor)
        self._attr_unique_id = self._build_unique_id("average_latency_in_ms")
        self.entity_id = self._build_entity_id("sensor", "average_latency_in_ms")

    @property
    def native_value(self) -> float | None:
        """Return average response latency in milliseconds."""
        latency_stats = self._monitor_stats.get("latencyStats")
        if latency_stats is None:
            return None
        return latency_stats.get("averageLatencyInMs")


class KuvaszAvgPacketLossSensor(KuvaszMonitorEntity, SensorEntity):
    """Sensor reporting average packet loss percentage for ICMP monitors."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
    _attr_translation_key = "average_packet_loss"

    def __init__(self, coordinator: KuvaszCoordinator, monitor: dict[str, Any]) -> None:
        """Initialize the average packet loss sensor."""
        super().__init__(coordinator, monitor)
        self._attr_unique_id = self._build_unique_id("average_packet_loss")
        self.entity_id = self._build_entity_id("sensor", "average_packet_loss")

    @property
    def native_value(self) -> float | None:
        """Return average packet loss as a percentage."""
        packet_loss_stats = self._monitor_stats.get("packetLossStats")
        if packet_loss_stats is None:
            return None
        return packet_loss_stats.get("averagePacketLossPercentage")


class KuvaszTimestampSensor(KuvaszMonitorEntity, SensorEntity):
    """Sensor reporting a datetime field from a monitor's details."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP

    def __init__(
        self,
        coordinator: KuvaszCoordinator,
        monitor: dict[str, Any],
        description: KuvaszTimestampSensorDescription,
    ) -> None:
        """Initialize the timestamp sensor from its description."""
        super().__init__(coordinator, monitor)
        self._description = description
        self._attr_unique_id = self._build_unique_id(description.key)
        self._attr_translation_key = description.translation_key
        self.entity_id = self._build_entity_id("sensor", description.key)

    @property
    def native_value(self) -> datetime | None:
        """Return the parsed datetime value from the monitor data."""
        raw = self._monitor_data.get(self._description.monitor_data_key)
        if raw is None:
            return None
        return datetime.fromisoformat(raw)
