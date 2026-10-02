"""Config flow for Kuvasz Uptime integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_HOST, CONF_NAME
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
from .monitor_types import supported_monitor_types

if TYPE_CHECKING:
    from collections.abc import Mapping

    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): str,
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_API_KEY): str,
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

STEP_REAUTH_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})

STEP_RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_API_KEY): str,
        vol.Required(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): BooleanSelector(),
    }
)


async def _async_fetch_monitors(
    hass: HomeAssistant, host: str, api_key: str | None, *, verify_ssl: bool
) -> list[dict[str, Any]]:
    """Connect to a Kuvasz instance and return every monitor it supports."""
    session = async_get_clientsession(hass, verify_ssl=verify_ssl)
    client = KuvaszClient(host=host, api_key=api_key, session=session)
    settings = await client.get_settings()
    return await client.get_all_monitors(supported_monitor_types(settings))


async def _async_validate_connection(
    hass: HomeAssistant, host: str, api_key: str | None, *, verify_ssl: bool
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Return form errors (empty on success) and the monitors that were fetched."""
    try:
        monitors = await _async_fetch_monitors(
            hass, host, api_key, verify_ssl=verify_ssl
        )
    except KuvaszAuthError:
        return {"base": "invalid_auth"}, []
    except KuvaszApiError:
        _LOGGER.exception("Failed to connect to Kuvasz instance at %s", host)
        return {"base": "cannot_connect"}, []
    except Exception:
        _LOGGER.exception("Unexpected error while connecting to Kuvasz Uptime")
        return {"base": "unknown"}, []
    return {}, monitors


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
    # Drop monitors that were deleted in Kuvasz since the selection was saved,
    # otherwise the selector rejects its own default value.
    default_selected = (
        [key for key in current_selected if key in all_keys]
        if current_selected is not None
        else all_keys
    )

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
        self._name: str = ""
        self._host: str = ""
        self._api_key: str | None = None
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
            name = user_input[CONF_NAME].strip()
            host = user_input[CONF_HOST].rstrip("/")
            api_key = user_input.get(CONF_API_KEY) or None
            verify_ssl = user_input[CONF_VERIFY_SSL]
            scan_interval = user_input[CONF_SCAN_INTERVAL]

            existing_names = {
                e.data.get(CONF_NAME) for e in self._async_current_entries()
            }
            if name in existing_names:
                errors[CONF_NAME] = "name_already_used"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()

                errors, self._monitors = await _async_validate_connection(
                    self.hass, host, api_key, verify_ssl=verify_ssl
                )
                if not errors:
                    self._name = name
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
                title=self._name,
                data={
                    CONF_NAME: self._name,
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

    async def async_step_reauth(
        self, _entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication after the API key was rejected."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new API key and verify it against the instance."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            api_key = user_input[CONF_API_KEY]
            errors, _ = await _async_validate_connection(
                self.hass,
                entry.data[CONF_HOST],
                api_key,
                verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_API_KEY: api_key}
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            errors=errors,
            description_placeholders={"name": entry.title},
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the connection details of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].rstrip("/")
            api_key = user_input.get(CONF_API_KEY) or None
            verify_ssl = user_input[CONF_VERIFY_SSL]

            if host != entry.data[CONF_HOST]:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()

            errors, _ = await _async_validate_connection(
                self.hass, host, api_key, verify_ssl=verify_ssl
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    unique_id=host,
                    data_updates={
                        CONF_HOST: host,
                        CONF_API_KEY: api_key,
                        CONF_VERIFY_SSL: verify_ssl,
                    },
                )

        suggested = user_input if user_input is not None else entry.data
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_RECONFIGURE_SCHEMA,
                {k: v for k, v in suggested.items() if v is not None},
            ),
            errors=errors,
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
        try:
            monitors = await _async_fetch_monitors(
                self.hass,
                entry.data[CONF_HOST],
                entry.data.get(CONF_API_KEY) or None,
                verify_ssl=entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            )
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
