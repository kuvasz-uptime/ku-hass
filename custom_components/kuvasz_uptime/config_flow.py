"""Config flow for Kuvasz Uptime integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .api import KuvaszApiError, KuvaszAuthError, KuvaszClient
from .const import (
    CONF_API_KEY,
    CONF_SCAN_INTERVAL,
    CONF_SELECTED_MONITORS,
    CONF_STATS_PERIOD,
    CONF_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_STATS_PERIOD,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    STATS_PERIOD_OPTIONS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): BooleanSelector(),
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            int, vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
        ),
        vol.Required(CONF_STATS_PERIOD, default=DEFAULT_STATS_PERIOD): SelectSelector(
            SelectSelectorConfig(
                options=STATS_PERIOD_OPTIONS,
                mode=SelectSelectorMode.DROPDOWN,
            )
        ),
    }
)


def _monitor_key(monitor: dict[str, Any]) -> str:
    return f"{monitor['_type']}_{monitor['id']}"


def _build_monitors_schema(
    monitors: list[dict[str, Any]],
    current_scan_interval: int,
    current_selected: list[str] | None,
    current_stats_period: str,
    *,
    include_settings: bool,
) -> vol.Schema:
    options = [
        {
            "value": _monitor_key(m),
            "label": f"{m['name']} ({m['_type'].upper()})",
        }
        for m in monitors
    ]
    all_keys = [opt["value"] for opt in options]
    default_selected = current_selected if current_selected is not None else all_keys

    fields: dict[vol.Marker, Any] = {}
    if include_settings:
        scan_key = vol.Required(CONF_SCAN_INTERVAL, default=current_scan_interval)
        fields[scan_key] = vol.All(
            int, vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL)
        )
        period_key = vol.Required(CONF_STATS_PERIOD, default=current_stats_period)
        fields[period_key] = SelectSelector(
            SelectSelectorConfig(
                options=STATS_PERIOD_OPTIONS,
                mode=SelectSelectorMode.DROPDOWN,
            )
        )
    monitors_key = vol.Required(CONF_SELECTED_MONITORS, default=default_selected)
    fields[monitors_key] = SelectSelector(
        SelectSelectorConfig(
            options=options,
            multiple=True,
            mode=SelectSelectorMode.LIST,
        )
    )
    return vol.Schema(fields)


class KuvaszConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Kuvasz Uptime integration."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._host: str = ""
        self._api_key: str = ""
        self._verify_ssl: bool = DEFAULT_VERIFY_SSL
        self._scan_interval: int = DEFAULT_SCAN_INTERVAL
        self._stats_period: str = DEFAULT_STATS_PERIOD
        self._monitors: list[dict[str, Any]] = []

    @staticmethod
    @callback
    def async_get_options_flow(_config_entry: ConfigEntry) -> KuvaszOptionsFlowHandler:
        """Return the options flow handler."""
        return KuvaszOptionsFlowHandler()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial credentials step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].rstrip("/")
            api_key = user_input[CONF_API_KEY]
            verify_ssl = user_input[CONF_VERIFY_SSL]
            scan_interval = user_input[CONF_SCAN_INTERVAL]

            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            session = async_get_clientsession(self.hass, verify_ssl=verify_ssl)
            client = KuvaszClient(host=host, api_key=api_key, session=session)

            try:
                await client.verify_connection()
                self._monitors = await client.get_all_monitors()
            except KuvaszAuthError:
                errors["base"] = "invalid_auth"
            except KuvaszApiError:
                _LOGGER.exception("Failed to connect to Kuvasz instance at %s", host)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during Kuvasz Uptime setup")
                errors["base"] = "unknown"
            else:
                self._host = host
                self._api_key = api_key
                self._verify_ssl = verify_ssl
                self._scan_interval = scan_interval
                self._stats_period = user_input[CONF_STATS_PERIOD]
                return await self.async_step_monitors()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
        )

    async def async_step_monitors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the monitor selection step."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._host,
                data={
                    CONF_HOST: self._host,
                    CONF_API_KEY: self._api_key,
                    CONF_VERIFY_SSL: self._verify_ssl,
                    CONF_SCAN_INTERVAL: self._scan_interval,
                    CONF_STATS_PERIOD: self._stats_period,
                    CONF_SELECTED_MONITORS: user_input[CONF_SELECTED_MONITORS],
                },
            )

        return self.async_show_form(
            step_id="monitors",
            data_schema=_build_monitors_schema(
                self._monitors,
                self._scan_interval,
                None,
                self._stats_period,
                include_settings=False,
            ),
        )


class KuvaszOptionsFlowHandler(OptionsFlow):
    """Options flow for updating scan interval and monitor selection."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the options init step."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL],
                    CONF_STATS_PERIOD: user_input[CONF_STATS_PERIOD],
                    CONF_SELECTED_MONITORS: user_input[CONF_SELECTED_MONITORS],
                }
            )

        entry = self.config_entry
        verify_ssl = entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
        session = async_get_clientsession(self.hass, verify_ssl=verify_ssl)
        client = KuvaszClient(
            host=entry.data[CONF_HOST],
            api_key=entry.data[CONF_API_KEY],
            session=session,
        )
        try:
            monitors = await client.get_all_monitors()
        except KuvaszApiError:
            return self.async_abort(reason="cannot_connect")

        def _current(key: str, default: Any = None) -> Any:
            return entry.options.get(key, entry.data.get(key, default))

        return self.async_show_form(
            step_id="init",
            data_schema=_build_monitors_schema(
                monitors,
                _current(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                _current(CONF_SELECTED_MONITORS),
                _current(CONF_STATS_PERIOD, DEFAULT_STATS_PERIOD),
                include_settings=True,
            ),
        )
