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

## Manual end-to-end testing

Copy the integration into your HA config and restart:

```bash
cp -r custom_components/kuvasz_uptime /path/to/ha/config/custom_components/
```

Then add it via **Settings → Devices & Services → Add Integration → Kuvasz Uptime**.
