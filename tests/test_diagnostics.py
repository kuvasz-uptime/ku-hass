"""Tests for Kuvasz Uptime diagnostics."""

from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)

from tests.conftest import setup_full_integration


async def test_diagnostics(hass, hass_client, snapshot):
    entry = await setup_full_integration(hass, [])

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert diagnostics == snapshot


async def test_secrets_and_logs_are_removed(hass, hass_client):
    entry = await setup_full_integration(hass, [])

    diagnostics = await get_diagnostics_for_config_entry(hass, hass_client, entry)

    assert diagnostics["entry"]["data"]["api_key"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["host"] == "**REDACTED**"
    http = next(m for m in diagnostics["monitors"] if m["_type"] == "http")
    assert http["url"] == "**REDACTED**"
    assert http["requestHeaders"] == "**REDACTED**"
    docker = next(m for m in diagnostics["monitors"] if m["_type"] == "docker")
    assert docker["dockerHost"] == "**REDACTED**"
    assert "latencyLogs" not in diagnostics["stats"]["http_1"]
    assert "metricsLogs" not in diagnostics["stats"]["docker_60"]
    assert diagnostics["stats"]["http_1"]["latencyStats"]["averageLatencyInMs"] == 123
