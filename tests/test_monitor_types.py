"""Tests for the monitor type registry and its capability detection."""

from custom_components.kuvasz_uptime.monitor_types import (
    MONITOR_TYPES,
    MONITOR_TYPES_BY_KEY,
    read_only_monitor_types,
    supported_monitor_types,
)
from tests.conftest import (
    SETTINGS_RESPONSE,
    SETTINGS_RESPONSE_NO_DNS,
    SETTINGS_RESPONSE_NO_ICMP,
    SETTINGS_RESPONSE_NO_TCP,
    SETTINGS_RESPONSE_READ_ONLY,
)


def _keys(types):
    return {m.key for m in types}


class TestRegistry:
    def test_every_type_is_indexed_by_its_key(self):
        assert set(MONITOR_TYPES_BY_KEY) == _keys(MONITOR_TYPES)
        assert len(MONITOR_TYPES_BY_KEY) == len(MONITOR_TYPES)

    def test_api_paths_are_unique(self):
        paths = [m.api_path for m in MONITOR_TYPES]
        assert len(paths) == len(set(paths))

    def test_http_and_push_are_not_optional(self):
        assert MONITOR_TYPES_BY_KEY["http"].optional is False
        assert MONITOR_TYPES_BY_KEY["push"].optional is False

    def test_icmp_tcp_and_dns_are_optional(self):
        assert MONITOR_TYPES_BY_KEY["icmp"].optional is True
        assert MONITOR_TYPES_BY_KEY["tcp"].optional is True
        assert MONITOR_TYPES_BY_KEY["dns"].optional is True


class TestSupportedMonitorTypes:
    def test_modern_instance_supports_every_type(self):
        assert _keys(supported_monitor_types(SETTINGS_RESPONSE)) == {
            "http",
            "push",
            "icmp",
            "tcp",
            "dns",
        }

    def test_instance_without_dns(self):
        assert _keys(supported_monitor_types(SETTINGS_RESPONSE_NO_DNS)) == {
            "http",
            "push",
            "icmp",
            "tcp",
        }

    def test_instance_without_tcp_or_dns(self):
        assert _keys(supported_monitor_types(SETTINGS_RESPONSE_NO_TCP)) == {
            "http",
            "push",
            "icmp",
        }

    def test_legacy_instance_without_icmp_tcp_or_dns(self):
        assert _keys(supported_monitor_types(SETTINGS_RESPONSE_NO_ICMP)) == {
            "http",
            "push",
        }

    def test_read_only_instance_still_supports_every_type(self):
        """Read-only is about writes; the monitors are still fetched."""
        assert _keys(supported_monitor_types(SETTINGS_RESPONSE_READ_ONLY)) == {
            "http",
            "push",
            "icmp",
            "tcp",
            "dns",
        }

    def test_settings_without_editability_falls_back_to_required_types(self):
        assert _keys(supported_monitor_types({"app": {}})) == {"http", "push"}

    def test_empty_settings_falls_back_to_required_types(self):
        assert _keys(supported_monitor_types({})) == {"http", "push"}


class TestReadOnlyMonitorTypes:
    def test_nothing_read_only_on_a_writable_instance(self):
        assert read_only_monitor_types(SETTINGS_RESPONSE) == frozenset()

    def test_every_type_read_only(self):
        assert read_only_monitor_types(SETTINGS_RESPONSE_READ_ONLY) == frozenset(
            {"http", "push", "icmp", "tcp", "dns"}
        )

    def test_absent_flags_are_not_read_only(self):
        assert read_only_monitor_types(SETTINGS_RESPONSE_NO_ICMP) == frozenset()

    def test_partial_read_only(self):
        settings = {
            "app": {
                "editabilityState": {
                    "areHttpMonitorsReadOnly": True,
                    "areTcpMonitorsReadOnly": False,
                }
            }
        }
        assert read_only_monitor_types(settings) == frozenset({"http"})
