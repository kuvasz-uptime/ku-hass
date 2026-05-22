"""Tests for the Kuvasz config flow."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.kuvasz_uptime.const import (
    CONF_SCAN_INTERVAL,
    CONF_SELECTED_MONITORS,
    CONF_STATS_PERIOD,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from tests.conftest import HTTP_MONITOR_UP, PUSH_MONITOR_UP

CREDENTIALS = {
    "host": "http://kuvasz.local:8080",
    "api_key": "supersecretapikey1234",
    "scan_interval": 60,
    "stats_period": "P7D",
}

ALL_MONITORS = [HTTP_MONITOR_UP, PUSH_MONITOR_UP]
ALL_MONITOR_KEYS = ["http_1", "push_20"]


async def _start_flow(hass):
    return await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )


async def _complete_flow(hass, credentials=None, selected=None, monitors=None):
    """Run both steps of the config flow and return the final result."""
    credentials = credentials or CREDENTIALS
    monitors = monitors if monitors is not None else ALL_MONITORS
    selected = (
        selected
        if selected is not None
        else [f"{m['_type']}_{m['id']}" for m in monitors]
    )

    with patch(
        "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
    ) as MockClient:
        instance = MockClient.return_value
        instance.verify_connection = AsyncMock(return_value=True)
        instance.get_all_monitors = AsyncMock(return_value=monitors)

        result = await _start_flow(hass)
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], credentials
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "monitors"

        return await hass.config_entries.flow.async_configure(
            result["flow_id"], {"selected_monitors": selected}
        )


class TestConfigFlowStep1:
    async def test_shows_form_on_init(self, hass):
        result = await _start_flow(hass)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    async def test_valid_credentials_advance_to_monitor_step(self, hass):
        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.verify_connection = AsyncMock(return_value=True)
            instance.get_all_monitors = AsyncMock(return_value=ALL_MONITORS)

            result = await _start_flow(hass)
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], CREDENTIALS
            )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "monitors"

    async def test_shows_invalid_auth_error(self, hass):
        from custom_components.kuvasz_uptime.api import KuvaszAuthError

        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.verify_connection = AsyncMock(
                side_effect=KuvaszAuthError("bad key")
            )
            instance.get_all_monitors = AsyncMock(return_value=ALL_MONITORS)

            result = await _start_flow(hass)
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], CREDENTIALS
            )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"
        assert result["errors"]["base"] == "invalid_auth"

    async def test_shows_cannot_connect_error(self, hass):
        from custom_components.kuvasz_uptime.api import KuvaszApiError

        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.verify_connection = AsyncMock(
                side_effect=KuvaszApiError("timeout")
            )
            instance.get_all_monitors = AsyncMock(return_value=ALL_MONITORS)

            result = await _start_flow(hass)
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], CREDENTIALS
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "cannot_connect"

    async def test_shows_unknown_error(self, hass):
        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.verify_connection = AsyncMock(side_effect=Exception("unexpected"))
            instance.get_all_monitors = AsyncMock(return_value=ALL_MONITORS)

            result = await _start_flow(hass)
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], CREDENTIALS
            )

        assert result["type"] == FlowResultType.FORM
        assert result["errors"]["base"] == "unknown"

    async def test_can_retry_after_error(self, hass):
        from custom_components.kuvasz_uptime.api import KuvaszApiError

        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.verify_connection = AsyncMock(side_effect=KuvaszApiError("down"))
            instance.get_all_monitors = AsyncMock(return_value=ALL_MONITORS)

            result = await _start_flow(hass)
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], CREDENTIALS
            )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.verify_connection = AsyncMock(return_value=True)
            instance.get_all_monitors = AsyncMock(return_value=ALL_MONITORS)

            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], CREDENTIALS
            )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "monitors"


class TestConfigFlowStep2:
    async def test_all_monitors_selected_by_default(self, hass):
        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.verify_connection = AsyncMock(return_value=True)
            instance.get_all_monitors = AsyncMock(return_value=ALL_MONITORS)

            result = await _start_flow(hass)
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], CREDENTIALS
            )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "monitors"
        schema_keys = list(result["data_schema"].schema.keys())
        assert any("selected_monitors" in str(k) for k in schema_keys)

    async def test_creates_entry_with_all_monitors_selected(self, hass):
        result = await _complete_flow(hass, selected=ALL_MONITOR_KEYS)

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"]["host"] == CREDENTIALS["host"]
        assert result["data"]["api_key"] == CREDENTIALS["api_key"]
        assert result["data"]["scan_interval"] == 60
        assert result["data"]["stats_period"] == "P7D"
        assert set(result["data"]["selected_monitors"]) == {"http_1", "push_20"}

    async def test_creates_entry_with_subset_of_monitors(self, hass):
        result = await _complete_flow(hass, selected=["http_1"])

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"]["selected_monitors"] == ["http_1"]

    async def test_creates_entry_with_no_monitors_selected(self, hass):
        result = await _complete_flow(hass, selected=[])

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["data"]["selected_monitors"] == []

    async def test_entry_title_is_host(self, hass):
        result = await _complete_flow(hass)
        assert result["title"] == CREDENTIALS["host"]

    async def test_aborts_if_already_configured(self, hass):
        await _complete_flow(hass)

        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.verify_connection = AsyncMock(return_value=True)
            instance.get_all_monitors = AsyncMock(return_value=ALL_MONITORS)

            result = await _start_flow(hass)
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], CREDENTIALS
            )

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "already_configured"

    async def test_monitor_options_include_type_label(self, hass):
        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.verify_connection = AsyncMock(return_value=True)
            instance.get_all_monitors = AsyncMock(return_value=ALL_MONITORS)

            result = await _start_flow(hass)
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], CREDENTIALS
            )

        selector_config = next(iter(result["data_schema"].schema.values())).config
        option_labels = [o["label"] for o in selector_config["options"]]
        assert any("HTTP" in label for label in option_labels)
        assert any("PUSH" in label for label in option_labels)

    async def test_empty_monitor_list_shows_form(self, hass):
        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.verify_connection = AsyncMock(return_value=True)
            instance.get_all_monitors = AsyncMock(return_value=[])

            result = await _start_flow(hass)
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], CREDENTIALS
            )

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "monitors"


class TestConfigFlowScanInterval:
    async def test_default_scan_interval_stored(self, hass):
        result = await _complete_flow(
            hass, credentials={**CREDENTIALS, "scan_interval": DEFAULT_SCAN_INTERVAL}
        )
        assert result["data"]["scan_interval"] == DEFAULT_SCAN_INTERVAL

    async def test_custom_scan_interval_stored(self, hass):
        result = await _complete_flow(
            hass, credentials={**CREDENTIALS, "scan_interval": 120}
        )
        assert result["data"]["scan_interval"] == 120

    async def test_scan_interval_below_minimum_rejected(self, hass):
        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.verify_connection = AsyncMock(return_value=True)
            instance.get_all_monitors = AsyncMock(return_value=ALL_MONITORS)

            result = await _start_flow(hass)
            with pytest.raises(Exception):  # noqa: B017
                await hass.config_entries.flow.async_configure(
                    result["flow_id"], {**CREDENTIALS, "scan_interval": 5}
                )


class TestConfigFlowVerifySSL:
    async def test_verify_ssl_defaults_to_true(self, hass):
        result = await _complete_flow(hass)
        assert result["data"][CONF_VERIFY_SSL] is True

    async def test_verify_ssl_false_stored(self, hass):
        result = await _complete_flow(
            hass, credentials={**CREDENTIALS, "verify_ssl": False}
        )
        assert result["data"][CONF_VERIFY_SSL] is False

    async def test_verify_ssl_passed_to_client_session(self, hass):
        with (
            patch(
                "custom_components.kuvasz_uptime.config_flow.async_get_clientsession"
            ) as mock_session,
            patch(
                "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
            ) as MockClient,
        ):
            instance = MockClient.return_value
            instance.verify_connection = AsyncMock(return_value=True)
            instance.get_all_monitors = AsyncMock(return_value=ALL_MONITORS)

            result = await _start_flow(hass)
            await hass.config_entries.flow.async_configure(
                result["flow_id"], {**CREDENTIALS, "verify_ssl": False}
            )

        mock_session.assert_called_once_with(hass, verify_ssl=False)


class TestOptionsFlow:
    async def _setup_entry(self, hass, selected=None):
        """Create a config entry and return it."""
        selected = selected if selected is not None else ALL_MONITOR_KEYS
        result = await _complete_flow(hass, selected=selected)
        assert result["type"] == FlowResultType.CREATE_ENTRY
        return hass.config_entries.async_entries(DOMAIN)[0]

    async def _start_options_flow(self, hass, entry, monitors=None):
        monitors = monitors if monitors is not None else ALL_MONITORS
        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.get_all_monitors = AsyncMock(return_value=monitors)
            return await hass.config_entries.options.async_init(entry.entry_id)

    async def test_options_flow_shows_init_form(self, hass):
        entry = await self._setup_entry(hass)
        result = await self._start_options_flow(hass, entry)

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

    async def test_options_flow_prefills_current_scan_interval(self, hass):
        entry = await self._setup_entry(hass)
        result = await self._start_options_flow(hass, entry)

        schema_dict = result["data_schema"].schema
        scan_key = next(k for k in schema_dict if str(k) == CONF_SCAN_INTERVAL)
        assert scan_key.default() == CREDENTIALS["scan_interval"]

    async def test_options_flow_prefills_current_selected_monitors(self, hass):
        entry = await self._setup_entry(hass, selected=["http_1"])
        result = await self._start_options_flow(hass, entry)

        schema_dict = result["data_schema"].schema
        sel_key = next(k for k in schema_dict if str(k) == CONF_SELECTED_MONITORS)
        assert sel_key.default() == ["http_1"]

    async def test_options_flow_saves_to_entry_options(self, hass):
        entry = await self._setup_entry(hass)

        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.get_all_monitors = AsyncMock(return_value=ALL_MONITORS)
            result = await hass.config_entries.options.async_init(entry.entry_id)
            result = await hass.config_entries.options.async_configure(
                result["flow_id"],
                {
                    CONF_SCAN_INTERVAL: 120,
                    CONF_STATS_PERIOD: "P7D",
                    CONF_SELECTED_MONITORS: ["http_1"],
                },
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert entry.options[CONF_SCAN_INTERVAL] == 120
        assert entry.options[CONF_STATS_PERIOD] == "P7D"
        assert entry.options[CONF_SELECTED_MONITORS] == ["http_1"]

    async def test_options_flow_aborts_on_api_error(self, hass):
        from custom_components.kuvasz_uptime.api import KuvaszApiError

        entry = await self._setup_entry(hass)

        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.get_all_monitors = AsyncMock(side_effect=KuvaszApiError("down"))
            result = await hass.config_entries.options.async_init(entry.entry_id)

        assert result["type"] == FlowResultType.ABORT
        assert result["reason"] == "cannot_connect"

    async def test_options_flow_shows_all_current_monitors_as_options(self, hass):
        entry = await self._setup_entry(hass)
        result = await self._start_options_flow(hass, entry)

        schema_dict = result["data_schema"].schema
        sel_key = next(k for k in schema_dict if str(k) == CONF_SELECTED_MONITORS)
        selector_options = schema_dict[sel_key].config["options"]
        option_values = [o["value"] for o in selector_options]
        assert "http_1" in option_values
        assert "push_20" in option_values

    async def test_options_flow_prefills_current_stats_period(self, hass):
        entry = await self._setup_entry(hass)
        result = await self._start_options_flow(hass, entry)

        schema_dict = result["data_schema"].schema
        period_key = next(k for k in schema_dict if str(k) == CONF_STATS_PERIOD)
        assert period_key.default() == CREDENTIALS["stats_period"]

    async def test_options_flow_can_change_stats_period(self, hass):
        entry = await self._setup_entry(hass)

        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.get_all_monitors = AsyncMock(return_value=ALL_MONITORS)
            result = await hass.config_entries.options.async_init(entry.entry_id)
            result = await hass.config_entries.options.async_configure(
                result["flow_id"],
                {
                    CONF_SCAN_INTERVAL: CREDENTIALS["scan_interval"],
                    CONF_STATS_PERIOD: "P30D",
                    CONF_SELECTED_MONITORS: ALL_MONITOR_KEYS,
                },
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert entry.options[CONF_STATS_PERIOD] == "P30D"

    async def test_options_flow_can_change_selected_monitors(self, hass):
        entry = await self._setup_entry(hass, selected=ALL_MONITOR_KEYS)

        with patch(
            "custom_components.kuvasz_uptime.config_flow.KuvaszClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.get_all_monitors = AsyncMock(return_value=ALL_MONITORS)
            result = await hass.config_entries.options.async_init(entry.entry_id)
            result = await hass.config_entries.options.async_configure(
                result["flow_id"],
                {
                    CONF_SCAN_INTERVAL: CREDENTIALS["scan_interval"],
                    CONF_STATS_PERIOD: CREDENTIALS["stats_period"],
                    CONF_SELECTED_MONITORS: ["push_20"],
                },
            )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert entry.options[CONF_SELECTED_MONITORS] == ["push_20"]
