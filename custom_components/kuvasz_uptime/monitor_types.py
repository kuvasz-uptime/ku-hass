"""Registry describing how each Kuvasz monitor type differs from the others."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .const import (
    API_HTTP_MONITORS,
    API_ICMP_MONITORS,
    API_PUSH_MONITORS,
    API_TCP_MONITORS,
    MONITOR_TYPE_HTTP,
    MONITOR_TYPE_ICMP,
    MONITOR_TYPE_PUSH,
    MONITOR_TYPE_TCP,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True)
class MonitorType:
    """Everything that varies between the Kuvasz monitor types."""

    key: str
    api_path: str
    device_label: str
    read_only_setting: str
    # Types introduced after the oldest supported Kuvasz release. Their
    # endpoints only exist when the instance announces them in its settings.
    optional: bool = False


MONITOR_TYPES: tuple[MonitorType, ...] = (
    MonitorType(
        key=MONITOR_TYPE_HTTP,
        api_path=API_HTTP_MONITORS,
        device_label="HTTP",
        read_only_setting="areHttpMonitorsReadOnly",
    ),
    MonitorType(
        key=MONITOR_TYPE_PUSH,
        api_path=API_PUSH_MONITORS,
        device_label="Push",
        read_only_setting="arePushMonitorsReadOnly",
    ),
    MonitorType(
        key=MONITOR_TYPE_ICMP,
        api_path=API_ICMP_MONITORS,
        device_label="ICMP",
        read_only_setting="areIcmpMonitorsReadOnly",
        optional=True,
    ),
    MonitorType(
        key=MONITOR_TYPE_TCP,
        api_path=API_TCP_MONITORS,
        device_label="TCP",
        read_only_setting="areTcpMonitorsReadOnly",
        optional=True,
    ),
)

MONITOR_TYPES_BY_KEY: dict[str, MonitorType] = {m.key: m for m in MONITOR_TYPES}


def _editability(settings: Mapping[str, Any]) -> Mapping[str, Any]:
    return settings.get("app", {}).get("editabilityState", {})


def supported_monitor_types(settings: Mapping[str, Any]) -> tuple[MonitorType, ...]:
    """
    Return the monitor types the instance described by `settings` supports.

    An optional type counts as supported only when the instance names its
    read-only flag, which is how older Kuvasz versions are detected without
    probing endpoints that do not exist there.
    """
    editability = _editability(settings)
    return tuple(
        m for m in MONITOR_TYPES if not m.optional or m.read_only_setting in editability
    )


def read_only_monitor_types(settings: Mapping[str, Any]) -> frozenset[str]:
    """Return the keys of the monitor types that cannot be modified via the API."""
    editability = _editability(settings)
    return frozenset(
        m.key for m in MONITOR_TYPES if editability.get(m.read_only_setting, False)
    )
