"""Snapshot tests for every entity the integration creates."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.const import Platform
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    snapshot_platform,
)

from custom_components.kuvasz_uptime.const import DOMAIN
from tests.conftest import (
    DNS_MONITOR_STATS,
    DNS_MONITOR_UP,
    DOCKER_MONITOR_STATS,
    DOCKER_MONITOR_UP,
    HTTP_MONITOR_DOWN,
    HTTP_MONITOR_STATS,
    HTTP_MONITOR_STATS_NO_LATENCY,
    HTTP_MONITOR_UP,
    ICMP_MONITOR_STATS,
    ICMP_MONITOR_UP,
    PUSH_MONITOR_STATS,
    PUSH_MONITOR_UP,
    SETTINGS_RESPONSE,
    TCP_MONITOR_STATS,
    TCP_MONITOR_UP,
)

MONITORS = [
    HTTP_MONITOR_UP,
    HTTP_MONITOR_DOWN,
    PUSH_MONITOR_UP,
    ICMP_MONITOR_UP,
    TCP_MONITOR_UP,
    DNS_MONITOR_UP,
    DOCKER_MONITOR_UP,
]

STATS = {
    ("http", 1): HTTP_MONITOR_STATS,
    ("http", 2): HTTP_MONITOR_STATS_NO_LATENCY,
    ("push", 20): PUSH_MONITOR_STATS,
    ("icmp", 30): ICMP_MONITOR_STATS,
    ("tcp", 40): TCP_MONITOR_STATS,
    ("dns", 50): DNS_MONITOR_STATS,
    ("docker", 60): DOCKER_MONITOR_STATS,
}


@pytest.mark.parametrize(
    "platform",
    [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH, Platform.UPDATE],
)
async def test_entities(hass, entity_registry, snapshot, platform):
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry",
        unique_id="http://kuvasz.local:8080",
        data={
            "name": "Test Instance",
            "host": "http://kuvasz.local:8080",
            "api_key": "test-key",
            "scan_interval": 30,
            "stats_period": "P1D",
            "selected_monitors": [f"{m['_type']}_{m['id']}" for m in MONITORS],
        },
    )
    entry.add_to_hass(hass)

    async def _stats(spec, monitor_id, period):
        return STATS[(spec.key, monitor_id)]

    with (
        patch("custom_components.kuvasz_uptime.PLATFORMS", [platform]),
        patch("custom_components.kuvasz_uptime.KuvaszClient") as mock_client,
    ):
        instance = mock_client.return_value
        instance.get_settings = AsyncMock(return_value=SETTINGS_RESPONSE)
        instance.get_all_monitors = AsyncMock(return_value=[dict(m) for m in MONITORS])
        instance.get_monitor_stats = AsyncMock(side_effect=_stats)

        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    await snapshot_platform(hass, entity_registry, snapshot, entry.entry_id)
