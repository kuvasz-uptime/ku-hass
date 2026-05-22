"""Tests for the Kuvasz update entity."""

from unittest.mock import MagicMock

import pytest
from homeassistant.components.update import UpdateEntity
from homeassistant.config_entries import ConfigEntry

from custom_components.kuvasz_uptime.api import KuvaszClient
from custom_components.kuvasz_uptime.const import DOMAIN
from custom_components.kuvasz_uptime.coordinator import (
    KuvaszCoordinator,
    KuvaszCoordinatorData,
)

VERSION_INFO_UPDATE_AVAILABLE = {
    "installedVersion": "2.1.0",
    "latestVersion": "2.2.0",
    "latestVersionDetails": "https://example.com/releases/v2.2.0",
    "isUpToDate": False,
}

VERSION_INFO_UP_TO_DATE = {
    "installedVersion": "2.2.0",
    "latestVersion": "2.2.0",
    "latestVersionDetails": "https://example.com/releases/v2.2.0",
    "isUpToDate": True,
}

VERSION_INFO_CHECKS_DISABLED = {
    "installedVersion": "2.1.0",
    "latestVersion": None,
    "latestVersionDetails": None,
    "isUpToDate": True,
}


def _make_coordinator(hass, version_info=None, update_checks_enabled=True):
    client = MagicMock(spec=KuvaszClient)
    coordinator = KuvaszCoordinator(
        hass, client, scan_interval=30, entry_id="test_entry"
    )
    coordinator.data = KuvaszCoordinatorData(
        monitors=[],
        stats={},
        version_info=version_info,
        update_checks_enabled=update_checks_enabled,
    )
    return coordinator


def _make_entry(entry_id="test_entry"):
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = entry_id
    entry.domain = DOMAIN
    return entry


async def _setup_integration(hass, coordinator):
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN]["test_entry"] = coordinator

    entry = _make_entry()

    from custom_components.kuvasz_uptime.update import async_setup_entry

    entities = []

    def async_add(ents):
        return entities.extend(ents)

    await async_setup_entry(hass, entry, async_add)
    return entities


class TestKuvaszUpdateEntity:
    async def test_one_entity_created_per_entry(self, hass):
        coordinator = _make_coordinator(hass, VERSION_INFO_UPDATE_AVAILABLE)
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == 1

    async def test_no_entity_created_when_update_checks_disabled(self, hass):
        coordinator = _make_coordinator(
            hass, VERSION_INFO_UPDATE_AVAILABLE, update_checks_enabled=False
        )
        entities = await _setup_integration(hass, coordinator)
        assert len(entities) == 0

    async def test_entity_is_update_entity(self, hass):
        coordinator = _make_coordinator(hass, VERSION_INFO_UPDATE_AVAILABLE)
        entities = await _setup_integration(hass, coordinator)
        assert isinstance(entities[0], UpdateEntity)

    async def test_installed_version(self, hass):
        coordinator = _make_coordinator(hass, VERSION_INFO_UPDATE_AVAILABLE)
        entities = await _setup_integration(hass, coordinator)
        assert entities[0].installed_version == "2.1.0"

    async def test_latest_version(self, hass):
        coordinator = _make_coordinator(hass, VERSION_INFO_UPDATE_AVAILABLE)
        entities = await _setup_integration(hass, coordinator)
        assert entities[0].latest_version == "2.2.0"

    async def test_release_url(self, hass):
        coordinator = _make_coordinator(hass, VERSION_INFO_UPDATE_AVAILABLE)
        entities = await _setup_integration(hass, coordinator)
        assert entities[0].release_url == "https://example.com/releases/v2.2.0"

    async def test_up_to_date_latest_version_matches_installed(self, hass):
        coordinator = _make_coordinator(hass, VERSION_INFO_UP_TO_DATE)
        entities = await _setup_integration(hass, coordinator)
        entity = entities[0]
        assert entity.installed_version == entity.latest_version

    async def test_update_checks_disabled_latest_version_is_none(self, hass):
        coordinator = _make_coordinator(hass, VERSION_INFO_CHECKS_DISABLED)
        entities = await _setup_integration(hass, coordinator)
        assert entities[0].latest_version is None

    async def test_update_checks_disabled_release_url_is_none(self, hass):
        coordinator = _make_coordinator(hass, VERSION_INFO_CHECKS_DISABLED)
        entities = await _setup_integration(hass, coordinator)
        assert entities[0].release_url is None

    async def test_missing_version_info_returns_none(self, hass):
        coordinator = _make_coordinator(hass, version_info=None)
        entities = await _setup_integration(hass, coordinator)
        entity = entities[0]
        assert entity.installed_version is None
        assert entity.latest_version is None
        assert entity.release_url is None

    async def test_unique_id_format(self, hass):
        coordinator = _make_coordinator(hass, VERSION_INFO_UPDATE_AVAILABLE)
        entities = await _setup_integration(hass, coordinator)
        assert entities[0].unique_id == f"{DOMAIN}_test_entry_update"

    async def test_device_info_identifier(self, hass):
        coordinator = _make_coordinator(hass, VERSION_INFO_UPDATE_AVAILABLE)
        entities = await _setup_integration(hass, coordinator)
        device_info = entities[0].device_info
        assert (DOMAIN, "test_entry_server") in device_info["identifiers"]

    async def test_device_info_name(self, hass):
        coordinator = _make_coordinator(hass, VERSION_INFO_UPDATE_AVAILABLE)
        entities = await _setup_integration(hass, coordinator)
        assert entities[0].device_info["name"] == "Kuvasz Server"

    async def test_has_entity_name(self, hass):
        coordinator = _make_coordinator(hass, VERSION_INFO_UPDATE_AVAILABLE)
        entities = await _setup_integration(hass, coordinator)
        assert entities[0].has_entity_name is True

    @pytest.mark.parametrize(
        ("entry_id", "expected_uid"),
        [
            ("entry_a", f"{DOMAIN}_entry_a_update"),
            ("entry_b", f"{DOMAIN}_entry_b_update"),
        ],
    )
    async def test_unique_id_uses_entry_id(self, hass, entry_id, expected_uid):
        client = MagicMock(spec=KuvaszClient)
        coordinator = KuvaszCoordinator(
            hass, client, scan_interval=30, entry_id=entry_id
        )
        coordinator.data = KuvaszCoordinatorData(
            monitors=[],
            stats={},
            version_info=VERSION_INFO_UPDATE_AVAILABLE,
            update_checks_enabled=True,
        )
        hass.data.setdefault(DOMAIN, {})
        hass.data[DOMAIN][entry_id] = coordinator

        entry = _make_entry(entry_id)

        from custom_components.kuvasz_uptime.update import async_setup_entry

        entities = []

        def async_add(ents):
            entities.extend(ents)

        await async_setup_entry(hass, entry, async_add)
        assert entities[0].unique_id == expected_uid
