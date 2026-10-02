"""Sensors for Kuvasz monitor statistics and status timestamps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, override

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfInformation, UnitOfTime
from homeassistant.util import dt as dt_util

from .const import (
    MONITOR_TYPE_DNS,
    MONITOR_TYPE_DOCKER,
    MONITOR_TYPE_HTTP,
    MONITOR_TYPE_ICMP,
    MONITOR_TYPE_PUSH,
    MONITOR_TYPE_TCP,
)
from .entity import KuvaszMonitorEntity

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime

    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import StateType

    from .coordinator import KuvaszConfigEntry, KuvaszCoordinator

PARALLEL_UPDATES = 0

type _Monitor = dict[str, Any]
type _Stats = dict[str, Any]


@dataclass(frozen=True, kw_only=True)
class KuvaszSensorEntityDescription(SensorEntityDescription):
    """Describes a Kuvasz sensor: which monitors get it and how to read it."""

    exists_fn: Callable[[_Monitor], bool]
    value_fn: Callable[[_Monitor, _Stats], StateType | datetime]


# Monitor types that record latency, and the field gating their history.
# Push and Docker monitors record no latency at all.
_LATENCY_HISTORY_FIELD: dict[str, str] = {
    MONITOR_TYPE_HTTP: "latencyHistoryEnabled",
    MONITOR_TYPE_ICMP: "metricsHistoryEnabled",
    MONITOR_TYPE_TCP: "metricsHistoryEnabled",
    MONITOR_TYPE_DNS: "metricsHistoryEnabled",
}


def _tracks_latency(monitor: _Monitor) -> bool:
    """Return True if the monitor records a latency history to average over."""
    field = _LATENCY_HISTORY_FIELD.get(monitor["_type"])
    return bool(field and monitor.get(field))


def _has_metrics(monitor_type: str) -> Callable[[_Monitor], bool]:
    """Match monitors of the given type that record metrics history."""
    return lambda m: m["_type"] == monitor_type and bool(m.get("metricsHistoryEnabled"))


def _stat(group: str, field: str) -> Callable[[_Monitor, _Stats], StateType]:
    """Read `field` from the `group` section of a monitor's stats."""
    return lambda _, stats: (stats.get(group) or {}).get(field)


def _timestamp(field: str) -> Callable[[_Monitor, _Stats], datetime | None]:
    """Parse a datetime field of the monitor; malformed values read as None."""

    def _parse(monitor: _Monitor, _: _Stats) -> datetime | None:
        raw = monitor.get(field)
        return dt_util.parse_datetime(raw) if raw else None

    return _parse


def _uptime_percentage(_: _Monitor, stats: _Stats) -> float | None:
    ratio: float | None = (stats.get("uptimeHistory") or {}).get("uptimeRatio")
    if ratio is None:
        return None
    return round(ratio * 100, 4)


SENSOR_DESCRIPTIONS: tuple[KuvaszSensorEntityDescription, ...] = (
    KuvaszSensorEntityDescription(
        key="uptime_ratio",
        translation_key="uptime_ratio",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        exists_fn=lambda _: True,
        value_fn=_uptime_percentage,
    ),
    KuvaszSensorEntityDescription(
        key="average_latency_in_ms",
        translation_key="average_latency_in_ms",
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
        exists_fn=_tracks_latency,
        value_fn=_stat("latencyStats", "averageLatencyInMs"),
    ),
    KuvaszSensorEntityDescription(
        key="average_packet_loss",
        translation_key="average_packet_loss",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        exists_fn=_has_metrics(MONITOR_TYPE_ICMP),
        value_fn=_stat("packetLossStats", "averagePacketLossPercentage"),
    ),
    KuvaszSensorEntityDescription(
        key="average_cpu_usage",
        translation_key="average_cpu_usage",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        exists_fn=_has_metrics(MONITOR_TYPE_DOCKER),
        value_fn=_stat("cpuStats", "averageCpuUsagePercentage"),
    ),
    KuvaszSensorEntityDescription(
        key="average_memory_usage",
        translation_key="average_memory_usage",
        native_unit_of_measurement=UnitOfInformation.BYTES,
        suggested_unit_of_measurement=UnitOfInformation.MEBIBYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        exists_fn=_has_metrics(MONITOR_TYPE_DOCKER),
        value_fn=_stat("memoryStats", "averageMemoryUsageBytes"),
    ),
    KuvaszSensorEntityDescription(
        key="ssl_valid_until",
        translation_key="ssl_valid_until",
        device_class=SensorDeviceClass.TIMESTAMP,
        exists_fn=lambda m: (
            m["_type"] == MONITOR_TYPE_HTTP and bool(m.get("sslCheckEnabled"))
        ),
        value_fn=_timestamp("sslValidUntil"),
    ),
    KuvaszSensorEntityDescription(
        key="last_heartbeat",
        translation_key="last_heartbeat",
        device_class=SensorDeviceClass.TIMESTAMP,
        exists_fn=lambda m: m["_type"] == MONITOR_TYPE_PUSH,
        value_fn=_timestamp("lastHeartbeat"),
    ),
)


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: KuvaszConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kuvasz sensors for a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        KuvaszSensor(coordinator, monitor, description)
        for monitor in coordinator.data.monitors
        for description in SENSOR_DESCRIPTIONS
        if description.exists_fn(monitor)
    )


class KuvaszSensor(KuvaszMonitorEntity, SensorEntity):
    """A sensor reading one value from a monitor's details or statistics."""

    entity_description: KuvaszSensorEntityDescription

    def __init__(
        self,
        coordinator: KuvaszCoordinator,
        monitor: dict[str, Any],
        description: KuvaszSensorEntityDescription,
    ) -> None:
        """Initialize the sensor from its description."""
        super().__init__(coordinator, monitor)
        self.entity_description = description
        self._attr_unique_id = self._build_unique_id(description.key)
        self.entity_id = self._build_entity_id("sensor", description.key)

    @property
    @override
    def native_value(self) -> StateType | datetime:
        """Return the sensor value from the monitor's details or statistics."""
        return self.entity_description.value_fn(self._monitor_data, self._monitor_stats)
