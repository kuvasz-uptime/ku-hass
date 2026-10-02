"""Tests for integration setup and stale device/entity cleanup."""

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kuvasz_uptime.__init__ import _remove_stale_devices
from custom_components.kuvasz_uptime.api import KuvaszApiError, KuvaszAuthError
from custom_components.kuvasz_uptime.const import DOMAIN
from tests.conftest import (
    HTTP_MONITOR_UP,
    MONITORS,
    PUSH_MONITOR_UP,
    SETTINGS_RESPONSE,
    TCP_MONITOR_UP,
    setup_full_integration,
)


def _make_entry(hass, selected=None):
    entry = MockConfigEntry(
        domain=DOMAIN,
        entry_id="test_entry",
        data={
            "name": "Test Instance",
            "host": "http://kuvasz.local:8080",
            "api_key": "test-key",
            "scan_interval": 30,
            "stats_period": "P1D",
            "selected_monitors": selected or ["http_1", "push_20"],
        },
    )
    entry.add_to_hass(hass)
    return entry


def _register_device(hass, entry, monitor_key):
    dev_reg = dr.async_get(hass)
    return dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, monitor_key)},
        name=monitor_key,
    )


async def _register_entity(hass, entry, device, unique_id, platform="binary_sensor"):
    ent_reg = er.async_get(hass)
    return ent_reg.async_get_or_create(
        platform,
        DOMAIN,
        unique_id,
        config_entry=entry,
        device_id=device.id,
    )


class TestStaleDeviceCleanup:
    async def test_removes_device_for_deselected_monitor(self, hass):
        entry = _make_entry(hass)
        _register_device(hass, entry, f"{entry.entry_id}_http_1")
        push_dev = _register_device(hass, entry, f"{entry.entry_id}_push_20")

        _remove_stale_devices(hass, entry, [HTTP_MONITOR_UP])

        dev_reg = dr.async_get(hass)
        assert dev_reg.async_get(push_dev.id) is None

    async def test_keeps_device_for_active_monitor(self, hass):
        entry = _make_entry(hass)
        http_dev = _register_device(hass, entry, f"{entry.entry_id}_http_1")
        _register_device(hass, entry, f"{entry.entry_id}_push_20")

        _remove_stale_devices(hass, entry, [HTTP_MONITOR_UP])

        dev_reg = dr.async_get(hass)
        assert dev_reg.async_get(http_dev.id) is not None

    async def test_removes_entities_with_device(self, hass):
        entry = _make_entry(hass)
        push_dev = _register_device(hass, entry, f"{entry.entry_id}_push_20")
        await _register_entity(
            hass, entry, push_dev, "kuvasz_uptime_test_entry_push_20_uptime_status"
        )
        await _register_entity(
            hass,
            entry,
            push_dev,
            "kuvasz_uptime_test_entry_push_20_uptime_ratio",
            "sensor",
        )

        _remove_stale_devices(hass, entry, [HTTP_MONITOR_UP])

        ent_reg = er.async_get(hass)
        assert (
            ent_reg.async_get_entity_id(
                "binary_sensor",
                DOMAIN,
                "kuvasz_uptime_test_entry_push_20_uptime_status",
            )
            is None
        )
        assert (
            ent_reg.async_get_entity_id(
                "sensor", DOMAIN, "kuvasz_uptime_test_entry_push_20_uptime_ratio"
            )
            is None
        )

    async def test_no_op_when_all_monitors_active(self, hass):
        entry = _make_entry(hass)
        http_dev = _register_device(hass, entry, f"{entry.entry_id}_http_1")
        push_dev = _register_device(hass, entry, f"{entry.entry_id}_push_20")

        _remove_stale_devices(hass, entry, [HTTP_MONITOR_UP, PUSH_MONITOR_UP])

        dev_reg = dr.async_get(hass)
        assert dev_reg.async_get(http_dev.id) is not None
        assert dev_reg.async_get(push_dev.id) is not None

    async def test_no_op_when_device_registry_is_empty(self, hass):
        entry = _make_entry(hass)

        _remove_stale_devices(hass, entry, [HTTP_MONITOR_UP])

        dev_reg = dr.async_get(hass)
        assert dr.async_entries_for_config_entry(dev_reg, entry.entry_id) == []

    async def test_removes_all_deselected_devices(self, hass):
        entry = _make_entry(hass)
        _register_device(hass, entry, f"{entry.entry_id}_http_1")
        push_dev = _register_device(hass, entry, f"{entry.entry_id}_push_20")

        _remove_stale_devices(hass, entry, [])

        dev_reg = dr.async_get(hass)
        assert dev_reg.async_get(push_dev.id) is None
        assert dr.async_entries_for_config_entry(dev_reg, entry.entry_id) == []


class TestSetupResilience:
    """A failed fetch must never be mistaken for 'the monitor was deleted'."""

    async def test_fetch_failure_aborts_setup_and_keeps_devices(self, hass):
        """
        A monitor fetch error must abort setup rather than prune devices.

        _remove_stale_devices permanently deletes devices (and their entities)
        for monitors missing from the first refresh. If the client swallowed a
        failing monitor endpoint, that whole type would look deselected and get
        wiped from the registry, so the error has to surface instead.
        """
        entry = _make_entry(hass, selected=["http_1", "tcp_40"])
        tcp_dev = _register_device(hass, entry, f"{entry.entry_id}_tcp_40")

        with patch("custom_components.kuvasz_uptime.KuvaszClient") as MockClient:
            instance = MockClient.return_value
            instance.get_settings = AsyncMock(return_value=SETTINGS_RESPONSE)
            instance.get_all_monitors = AsyncMock(
                side_effect=KuvaszApiError("Failed to fetch tcp monitors: 503")
            )

            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.SETUP_RETRY
        dev_reg = dr.async_get(hass)
        assert dev_reg.async_get(tcp_dev.id) is not None

    async def test_successful_setup_keeps_supported_devices(self, hass):
        entry = _make_entry(hass, selected=["http_1", "tcp_40"])
        tcp_dev = _register_device(hass, entry, f"{entry.entry_id}_tcp_40")

        with patch("custom_components.kuvasz_uptime.KuvaszClient") as MockClient:
            instance = MockClient.return_value
            instance.get_settings = AsyncMock(return_value=SETTINGS_RESPONSE)
            instance.get_all_monitors = AsyncMock(
                return_value=[HTTP_MONITOR_UP, TCP_MONITOR_UP]
            )
            instance.get_monitor_stats = AsyncMock(return_value={})

            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.LOADED
        dev_reg = dr.async_get(hass)
        assert dev_reg.async_get(tcp_dev.id) is not None


class TestReauthTrigger:
    async def test_rejected_api_key_starts_reauth_flow(self, hass):
        entry = _make_entry(hass)

        with patch("custom_components.kuvasz_uptime.KuvaszClient") as MockClient:
            instance = MockClient.return_value
            instance.get_settings = AsyncMock(side_effect=KuvaszAuthError("bad key"))

            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.SETUP_ERROR
        flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
        assert len(flows) == 1
        assert flows[0]["context"]["source"] == "reauth"
        assert flows[0]["context"]["entry_id"] == entry.entry_id


def _server_device(hass, entry):
    return dr.async_get(hass).async_get_device(
        identifiers={(DOMAIN, f"{entry.entry_id}_server")}
    )


class TestDeviceHierarchy:
    async def test_server_device_describes_the_instance(self, hass):
        entry = await setup_full_integration(hass, [])

        server = _server_device(hass, entry)
        assert server is not None
        assert server.name == "Kuvasz Server"
        assert server.sw_version == "2.1.0"
        assert server.entry_type is dr.DeviceEntryType.SERVICE
        assert server.configuration_url == "http://kuvasz.local:8080"

    async def test_server_device_exists_without_update_checks(self, hass):
        settings = {
            **SETTINGS_RESPONSE,
            "app": {**SETTINGS_RESPONSE["app"], "updateChecksEnabled": False},
        }
        entry = await setup_full_integration(hass, [Platform.UPDATE], settings)

        assert _server_device(hass, entry) is not None
        assert (
            er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id) == []
        )

    async def test_monitor_devices_hang_off_the_server(self, hass):
        entry = await setup_full_integration(hass, [Platform.BINARY_SENSOR])

        server = _server_device(hass, entry)
        monitor_devices = [
            device
            for device in dr.async_entries_for_config_entry(
                dr.async_get(hass), entry.entry_id
            )
            if device.id != server.id
        ]
        assert len(monitor_devices) == len(MONITORS)
        for device in monitor_devices:
            assert device.via_device_id == server.id
            assert device.entry_type is dr.DeviceEntryType.SERVICE
            assert device.configuration_url == "http://kuvasz.local:8080"

    async def test_server_sw_version_follows_upgrades(self, hass):
        entry = await setup_full_integration(hass, [])
        coordinator = entry.runtime_data
        coordinator.client.get_settings.return_value = {
            **SETTINGS_RESPONSE,
            "versionInfo": {
                **SETTINGS_RESPONSE["versionInfo"],
                "installedVersion": "2.2.0",
            },
        }

        await coordinator.async_refresh()

        assert _server_device(hass, entry).sw_version == "2.2.0"


class TestEntryLifecycle:
    async def test_unload(self, hass):
        entry = await setup_full_integration(hass, [Platform.SENSOR])

        assert await hass.config_entries.async_unload(entry.entry_id)

        assert entry.state is ConfigEntryState.NOT_LOADED

    async def test_saving_options_reloads_the_entry(self, hass):
        entry = await setup_full_integration(hass, [])
        coordinator_before = entry.runtime_data

        with (
            patch(
                "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
            ) as flow_client,
            patch("custom_components.kuvasz_uptime.KuvaszClient") as setup_client,
            patch("custom_components.kuvasz_uptime.PLATFORMS", []),
        ):
            for client in (flow_client.return_value, setup_client.return_value):
                client.get_settings = AsyncMock(return_value=SETTINGS_RESPONSE)
                client.get_all_monitors = AsyncMock(
                    return_value=[dict(m) for m in MONITORS]
                )
                client.get_monitor_stats = AsyncMock(return_value={})

            result = await hass.config_entries.options.async_init(entry.entry_id)
            await hass.config_entries.options.async_configure(
                result["flow_id"],
                {
                    "scan_interval": 120,
                    "stats_period": "P7D",
                    "selected_monitors": ["http_1"],
                },
            )
            await hass.async_block_till_done()

        assert entry.state is ConfigEntryState.LOADED
        assert entry.runtime_data is not coordinator_before
        assert entry.runtime_data.update_interval.total_seconds() == 120
        assert [m["id"] for m in entry.runtime_data.data.monitors] == [1]
