# Kuvasz Uptime - Home Assistant Integration

[![CI](https://github.com/kuvasz-uptime/ku-hass/actions/workflows/tests.yml/badge.svg)](https://github.com/kuvasz-uptime/ku-hass/actions/workflows/tests.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A [Home Assistant](https://www.home-assistant.io/) integration for [Kuvasz Uptime](https://kuvasz-uptime.dev) - a self-hosted, open-source uptime and SSL monitoring service.

Each monitor from your Kuvasz Uptime instance becomes a device in Home Assistant, with sensors reflecting its current status and statistics. Use them in dashboards, automations, and alerts.

## Features

| Entity | Type | Monitors |
|---|---|---|
| Uptime Status | Binary sensor (`connectivity`) | HTTP, Push, ICMP |
| SSL Status | Binary sensor (`safety`) | HTTP (when SSL check is enabled) |
| Enabled | Binary sensor | HTTP, Push, ICMP |
| Enabled | Switch | HTTP, Push, ICMP (writable monitors only) |
| Uptime Ratio | Sensor (`%`) | HTTP, Push, ICMP |
| Average Latency | Sensor (`ms`, `duration`) | HTTP; ICMP (when metrics history is enabled) |
| Average Packet Loss | Sensor (`%`) | ICMP (when metrics history is enabled) |
| Uptime Status Started At | Sensor (`timestamp`) | HTTP, Push, ICMP |
| Last Uptime Check | Sensor (`timestamp`) | HTTP, Push, ICMP |
| Next Uptime Check | Sensor (`timestamp`) | HTTP, ICMP |
| SSL Status Started At | Sensor (`timestamp`) | HTTP (when SSL check is enabled) |
| Last SSL Check | Sensor (`timestamp`) | HTTP (when SSL check is enabled) |
| Next SSL Check | Sensor (`timestamp`) | HTTP (when SSL check is enabled) |
| SSL Valid Until | Sensor (`timestamp`) | HTTP (when SSL check is enabled) |
| Last Heartbeat | Sensor (`timestamp`) | Push |
| Next Expected Heartbeat | Sensor (`timestamp`) | Push |

**Uptime binary sensor** is `on` when the monitor is `UP` and `off` otherwise.

**SSL binary sensor** is `on` when the certificate is `INVALID` (problem detected) and `off` otherwise (`VALID` or `WILL_EXPIRE`). The raw `ssl_status` string is available as an extra attribute.

**Enabled binary sensor** reflects whether the monitor is currently enabled. It is present for every monitor regardless of whether the monitor type is writable.

**Enabled switch** lets you pause and resume a monitor directly from Home Assistant. It is only created for monitor types that are writable in your Kuvasz instance. Read-only monitor types (e.g. managed via YAML/GitOps) only get the binary sensor.

## Requirements

- Home Assistant 2026.3 or newer
- Kuvasz Uptime 3.2.0 or newer
- A running [Kuvasz](https://kuvasz-uptime.dev) instance (self-hosted)
- Your [API key](https://kuvasz-uptime.dev/setup/configuration/#api-key) for your Kuvasz instance

## Installation

### Via HACS (recommended)

1. In Home Assistant, open **HACS → Integrations**.
2. Click the three-dot menu → **Custom repositories**.
3. Add `https://github.com/kuvasz-uptime/ku-hass` with category **Integration**.
4. Search for **Kuvasz Uptime** and install it.
5. Restart Home Assistant.

### Manual

1. Copy `custom_components/kuvasz_uptime/` into your HA `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Kuvasz Uptime**.
3. Enter your Kuvasz Uptime instance URL (e.g. `http://192.168.1.10:8080`) and API key.
4. Select which monitors to expose as devices (all are selected by default).

You can change options later via the **Configure** button on the integration card:

- **Polling interval** - how often to refresh monitor state (default: 30 s, min: 10 s, max: 300 s)
- **Stats period** - the time window used for uptime percentage and response time stats (default: 24 h)
- **Monitor selection** - add or remove monitors without re-adding the integration

Monitors that are deselected are removed from the HA device registry (including all their entities).

## Contributing

See [DEVELOPMENT.md](DEVELOPMENT.md).

## License

Apache 2.0
