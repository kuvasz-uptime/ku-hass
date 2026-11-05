# Development

## Prerequisites

- Python 3.14+
- A running [Kuvasz](https://kuvasz-uptime.dev) instance (for manual end-to-end testing)

## Setup

```bash
git clone https://github.com/kuvasz-uptime/ku-hass
cd ku-hass
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt
```

## Linting

```bash
python3 -m ruff check .
python3 -m ruff check . --fix
```

## Type checking

The integration is checked with mypy in strict mode, using the same flags as Home Assistant core (see `mypy.ini`):

```bash
python3 -m mypy
```

## Running tests

```bash
pytest tests/ -v
```

CI runs the suite with `--cov` and fails below 95% coverage (configured in `.coveragerc`).

Entity states and diagnostics are covered by snapshot tests (`tests/snapshots/`). After an intended change to entities or diagnostics output, regenerate them and review the diff:

```bash
pytest tests/ --snapshot-update
```

The test suite uses `pytest-homeassistant-custom-component`, which provides a real (but minimal) HA instance. No running Home Assistant or Kuvasz instance is needed - all HTTP calls are mocked.

## Home Assistant guidelines

The integration follows the current [developer guidelines](https://contributors.home-assistant.io/blog/) and supports the Home Assistant version in `hacs.json` (currently 2026.10) and newer:

- Write config flow schemas with `import probatio`, not voluptuous ([Probatio is our validation engine](https://contributors.home-assistant.io/blog/2026/09/30/probatio-validation-engine/)).
- Pass a `step_id` to every `async_show_form` (and menu/progress result). It becomes mandatory in 2027.5.
- Leave the `reauth_successful` and `reconfigure_successful` aborts to Home Assistant's central translations. Only add `strings.json` abort keys for reasons of our own.
- Keep `categories` in `manifest.json`. The Marketplace uses it, and the HACS action warns without it.
- `hacs.json` and the HACS validation step in CI still apply: the Home Assistant Marketplace (built in since 2026.11) uses the same catalog and `hacs.json`.

To adopt once the minimum Home Assistant version is 2026.11 or newer (and `pytest-homeassistant-custom-component` ships it):

- Return `None` from `async_setup_entry`/`async_unload_entry`, raise `ConfigEntryError` instead of returning `False`, and unload with `async_unload_platforms_or_raise` ([Config entry functions now return None](https://contributors.home-assistant.io/blog/2026/10/23/config-entry-methods-return-none/)).
- Register the server device with `async_get_or_create_from_info(device_info=...)` instead of unpacking `**server_device_info(...)` in `__init__.py`.
- Read and set `DeviceInfo` fields as attributes (`info.via_device_id = ...` in `entity.py`) instead of dict-style, which is only a compatibility layer since `DeviceInfo` became a dataclass ([DeviceInfo is now a dataclass](https://contributors.home-assistant.io/blog/2026/10/13/device-info-class/)).
- Use `Undefined` instead of `UNDEFINED`/`UndefinedType` (deprecated in 2026.12) if a sentinel is ever needed.

## Manual end-to-end testing

Copy the integration into your HA config and restart:

```bash
cp -r custom_components/kuvasz_uptime /path/to/ha/config/custom_components/
```

Then add it via **Settings → Devices & Services → Add Integration → Kuvasz Uptime**.
