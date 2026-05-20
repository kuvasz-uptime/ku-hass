# Development

## Prerequisites

- Python 3.13+
- A running [Kuvasz](https://kuvasz-uptime.dev) instance (for manual end-to-end testing)

## Setup

```bash
git clone https://github.com/kuvasz-uptime/ku-hass
cd ku-hass
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements_test.txt
```

## Running tests

```bash
pytest tests/ -v
```

The test suite uses `pytest-homeassistant-custom-component`, which provides a real (but minimal) HA instance. No running Home Assistant or Kuvasz instance is needed - all HTTP calls are mocked.

## Manual end-to-end testing

Copy the integration into your HA config and restart:

```bash
cp -r custom_components/kuvasz_uptime /path/to/ha/config/custom_components/
```

Then add it via **Settings → Devices & Services → Add Integration → Kuvasz Uptime**.
