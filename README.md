# Kuvasz Uptime - Home Assistant Integration

[![CI](https://github.com/kuvasz-uptime/ku-hass/actions/workflows/tests.yml/badge.svg)](https://github.com/kuvasz-uptime/ku-hass/actions/workflows/tests.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A [Home Assistant](https://www.home-assistant.io/) integration for [Kuvasz Uptime](https://kuvasz-uptime.dev) - a self-hosted, open-source uptime and SSL monitoring service.

Each monitor from your Kuvasz Uptime instance becomes a device in Home Assistant, with sensors reflecting its current status and statistics. Use them in dashboards, automations, and alerts.

## Features

| Entity | Type | Monitors |
|---|---|---|
| Uptime Status | Binary sensor (`connectivity`) | HTTP, Push, ICMP, TCP |
| SSL Status | Binary sensor (`safety`) | HTTP (when SSL check is enabled) |
| Enabled | Binary sensor | HTTP, Push, ICMP, TCP |
| Enabled | Switch | HTTP, Push, ICMP, TCP (writable monitors only) |
| Uptime Ratio | Sensor (`%`) | HTTP, Push, ICMP, TCP |
| Average Latency | Sensor (`ms`, `duration`) | HTTP; ICMP, TCP (when metrics history is enabled) |
| Average Packet Loss | Sensor (`%`) | ICMP (when metrics history is enabled) |
| SSL Valid Until | Sensor (`timestamp`) | HTTP (when SSL check is enabled) |
| Last Heartbeat | Sensor (`timestamp`) | Push |
| Kuvasz Update | Update | Integration (when update checks are enabled) |

**Uptime binary sensor** is `on` when the monitor is `UP` and `off` otherwise. Extra attributes:

| Attribute | Monitors |
|---|---|
| `uptime_status_started_at`, `last_uptime_check`, `failure_count_threshold`, `uptime_error`, `created_at`, `updated_at` | HTTP, Push, ICMP, TCP |
| `next_uptime_check`, `uptime_check_interval` | HTTP, ICMP, TCP |
| `url`, `request_method`, `follow_redirects`, `force_no_cache`, `latency_history_enabled`, `expected_status_codes`, `response_time_threshold_millis`, `expected_keyword`, `expected_keyword_case_sensitive`, `expected_keyword_negated` | HTTP |
| `next_expected_heartbeat`, `heartbeat_interval`, `grace_period` | Push |
| `host`, `packet_count`, `timeout_seconds`, `packet_loss_threshold`, `metrics_history_enabled` | ICMP |
| `host`, `port`, `timeout_ms`, `latency_threshold_ms`, `metrics_history_enabled` | TCP |

**SSL binary sensor** is `on` when the certificate is `INVALID` (problem detected) and `off` otherwise (`VALID` or `WILL_EXPIRE`). Extra attributes: `ssl_status`, `ssl_error`, `ssl_expiry_threshold`, `ssl_status_started_at`, `last_ssl_check`, `next_ssl_check`, `ssl_valid_until`.

**Enabled binary sensor** reflects whether the monitor is currently enabled. It is present for every monitor regardless of whether the monitor type is writable.

**Enabled switch** lets you pause and resume a monitor directly from Home Assistant. It is only created for monitor types that are writable in your Kuvasz instance. Read-only monitor types (e.g. managed via YAML/GitOps) only get the binary sensor.

**Kuvasz Update** tracks the installed and latest available version of your Kuvasz instance. It is only created when update checks are enabled on your Kuvasz instance. The entity belongs to a separate **Kuvasz Server** device.

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
3. Enter an **Instance name**, your instance URL (e.g. `http://192.168.1.10:8080`), and API key.
4. Select which monitors to expose as devices (all are selected by default).

The instance name must be unique across all configured Kuvasz entries. It is used to scope every entity and device identifier, so two monitors with the same numeric ID on different hosts never collide. Multiple instances can be added by repeating the setup with a different name and host.

You can change options later via the **Configure** button on the integration card:

- **Polling interval** - how often to refresh monitor state (default: 30 s, min: 10 s, max: 300 s)
- **Stats period** - the time window used for uptime percentage and response time stats (default: 24 h)
- **Monitor selection** - add or remove monitors without re-adding the integration

Monitors that are deselected are removed from the HA device registry (including all their entities).

## Contributing

See [DEVELOPMENT.md](DEVELOPMENT.md).

## License

Apache 2.0
