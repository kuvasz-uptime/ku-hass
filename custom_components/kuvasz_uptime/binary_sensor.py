"""Binary sensors for Kuvasz monitors (uptime, SSL status, and enabled state)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)

from .const import (
    DOMAIN,
    MONITOR_TYPE_HTTP,
    MONITOR_TYPE_ICMP,
    MONITOR_TYPE_PUSH,
    SSL_STATUS_INVALID,
    UPTIME_STATUS_UP,
)
from .entity import KuvaszMonitorEntity

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .coordinator import KuvaszCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Kuvasz binary sensors for a config entry."""
    coordinator: KuvaszCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []

    for monitor in coordinator.data.monitors:
        entities.append(KuvaszUptimeBinarySensor(coordinator, monitor))
        entities.append(KuvaszEnabledBinarySensor(coordinator, monitor))
        if monitor["_type"] == MONITOR_TYPE_HTTP and monitor.get("sslCheckEnabled"):
            entities.append(KuvaszSslBinarySensor(coordinator, monitor))

    async_add_entities(entities)


class KuvaszUptimeBinarySensor(KuvaszMonitorEntity, BinarySensorEntity):
    """Binary sensor representing a monitor's uptime status (UP = on)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "uptime_status"

    def __init__(self, coordinator: KuvaszCoordinator, monitor: dict[str, Any]) -> None:
        """Initialize the uptime binary sensor."""
        super().__init__(coordinator, monitor)
        self._attr_unique_id = (
            f"{DOMAIN}_{self._monitor_type}_{self._monitor_id}_uptime_status"
        )
        self.entity_id = self._build_entity_id("binary_sensor", "uptime_status")

    @property
    def is_on(self) -> bool | None:
        """Return True if the monitor's uptime status is UP."""
        status = self._monitor_data.get("uptimeStatus")
        if status is None:
            return None
        return status == UPTIME_STATUS_UP

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return monitor configuration as extra state attributes."""
        data = self._monitor_data
        attrs: dict[str, Any] = {
            "failure_count_threshold": data.get("failureCountThreshold"),
            "uptime_error": data.get("uptimeError"),
            "uptime_status_since": data.get("uptimeStatusStartedAt"),
            "created_at": data.get("createdAt"),
            "updated_at": data.get("updatedAt"),
        }
        if self._monitor_type == MONITOR_TYPE_HTTP:
            if not data.get("sensitiveUrl"):
                attrs["url"] = data.get("url")
            attrs.update(
                {
                    "uptime_check_interval": data.get("uptimeCheckInterval"),
                    "request_method": data.get("requestMethod"),
                    "follow_redirects": data.get("followRedirects"),
                    "force_no_cache": data.get("forceNoCache"),
                    "latency_history_enabled": data.get("latencyHistoryEnabled"),
                    "expected_status_codes": data.get("expectedStatusCodes"),
                    "response_time_threshold_ms": data.get(
                        "responseTimeThresholdMillis"
                    ),
                    "expected_keyword": data.get("expectedKeyword"),
                    "expected_keyword_case_sensitive": data.get(
                        "expectedKeywordCaseSensitive"
                    ),
                    "expected_keyword_negated": data.get("expectedKeywordNegated"),
                }
            )
        elif self._monitor_type == MONITOR_TYPE_PUSH:
            attrs.update(
                {
                    "heartbeat_interval": data.get("heartbeatInterval"),
                    "grace_period": data.get("gracePeriod"),
                }
            )
        elif self._monitor_type == MONITOR_TYPE_ICMP:
            attrs.update(
                {
                    "host": data.get("host"),
                    "uptime_check_interval": data.get("uptimeCheckInterval"),
                    "packet_count": data.get("packetCount"),
                    "timeout_seconds": data.get("timeoutSeconds"),
                    "packet_loss_threshold": data.get("packetLossThreshold"),
                    "metrics_history_enabled": data.get("metricsHistoryEnabled"),
                }
            )
        return attrs


class KuvaszEnabledBinarySensor(KuvaszMonitorEntity, BinarySensorEntity):
    """Binary sensor representing whether a Kuvasz monitor is enabled."""

    _attr_translation_key = "enabled"

    def __init__(self, coordinator: KuvaszCoordinator, monitor: dict[str, Any]) -> None:
        """Initialize the enabled binary sensor."""
        super().__init__(coordinator, monitor)
        self._attr_unique_id = (
            f"{DOMAIN}_{self._monitor_type}_{self._monitor_id}_enabled"
        )
        self.entity_id = self._build_entity_id("binary_sensor", "enabled")

    @property
    def is_on(self) -> bool | None:
        """Return True if the monitor is enabled."""
        enabled = self._monitor_data.get("enabled")
        if enabled is None:
            return None
        return bool(enabled)


class KuvaszSslBinarySensor(KuvaszMonitorEntity, BinarySensorEntity):
    """Binary sensor representing an HTTP monitor's SSL certificate validity."""

    _attr_device_class = BinarySensorDeviceClass.SAFETY
    _attr_translation_key = "ssl_status"

    def __init__(self, coordinator: KuvaszCoordinator, monitor: dict[str, Any]) -> None:
        """Initialize the SSL binary sensor."""
        super().__init__(coordinator, monitor)
        self._attr_unique_id = (
            f"{DOMAIN}_{self._monitor_type}_{self._monitor_id}_ssl_status"
        )
        self.entity_id = self._build_entity_id("binary_sensor", "ssl_status")

    @property
    def is_on(self) -> bool | None:
        """Return True if the SSL certificate is invalid (problem detected)."""
        status = self._monitor_data.get("sslStatus")
        if status is None:
            return None
        return status == SSL_STATUS_INVALID

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return SSL certificate details as extra state attributes."""
        data = self._monitor_data
        return {
            "ssl_status": data.get("sslStatus"),
            "ssl_error": data.get("sslError"),
            "ssl_expiry_threshold": data.get("sslExpiryThreshold"),
            "ssl_status_since": data.get("sslStatusStartedAt"),
            "ssl_valid_until": data.get("sslValidUntil"),
        }
