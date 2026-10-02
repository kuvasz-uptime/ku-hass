"""Snapshot tests for every entity the integration creates."""

import pytest
from homeassistant.const import Platform
from pytest_homeassistant_custom_component.common import snapshot_platform

from tests.conftest import setup_full_integration


@pytest.mark.parametrize(
    "platform",
    [Platform.BINARY_SENSOR, Platform.SENSOR, Platform.SWITCH, Platform.UPDATE],
)
async def test_entities(hass, entity_registry, snapshot, platform):
    entry = await setup_full_integration(hass, [platform])

    await snapshot_platform(hass, entity_registry, snapshot, entry.entry_id)
