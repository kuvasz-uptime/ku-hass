# Kuvasz Uptime - Home Assistant Integration

[![CI](https://github.com/kuvasz-uptime/ku-hass/actions/workflows/tests.yml/badge.svg)](https://github.com/kuvasz-uptime/ku-hass/actions/workflows/tests.yml)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-blue.svg)](https://github.com/hacs/integration)

A [Home Assistant](https://www.home-assistant.io/) integration for [Kuvasz Uptime](https://kuvasz-uptime.dev) - a self-hosted, open-source uptime and SSL monitoring service.

Each monitor from your Kuvasz Uptime instance becomes a device in Home Assistant, with sensors reflecting its current status and statistics. Use them in dashboards, automations, and alerts.

## Features

| Entity               | Type                           | Monitors                                                |
|----------------------|--------------------------------|---------------------------------------------------------|
| Uptime Status        | Binary sensor (`connectivity`) | HTTP, Push, ICMP, TCP, DNS, Docker                      |
| SSL Status           | Binary sensor (`safety`)       | HTTP (when SSL check is enabled)                        |
| Enabled              | Binary sensor                  | HTTP, Push, ICMP, TCP, DNS, Docker                      |
| Enabled              | Switch                         | HTTP, Push, ICMP, TCP, DNS, Docker (writable only)      |
| Uptime Ratio         | Sensor (`%`)                   | HTTP, Push, ICMP, TCP, DNS, Docker                      |
| Average Latency      | Sensor (`ms`, `duration`)      | HTTP; ICMP, TCP, DNS (when metrics history is enabled)  |
| Average Packet Loss  | Sensor (`%`)                   | ICMP (when metrics history is enabled)                  |
| Average CPU Usage    | Sensor (`%`)                   | Docker (when metrics history is enabled)                |
| Average Memory Usage | Sensor (`MiB`, `data_size`)    | Docker (when metrics history is enabled)                |
| SSL Valid Until      | Sensor (`timestamp`)           | HTTP (when SSL check is enabled)                        |
| Last Heartbeat       | Sensor (`timestamp`)           | Push                                                    |
| Server version       | Update                         | Integration (when update checks are enabled)            |

**Uptime binary sensor** is `on` when the monitor is `UP` and `off` otherwise. Extra attributes:

| Attribute                                                                                                                                                                                                                              | Monitors                           |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------|
| `uptime_status_started_at`, `last_uptime_check`, `failure_count_threshold`, `uptime_error`, `created_at`, `updated_at`                                                                                                                 | HTTP, Push, ICMP, TCP, DNS, Docker |
| `next_uptime_check`, `uptime_check_interval`                                                                                                                                                                                           | HTTP, ICMP, TCP, DNS, Docker       |
| `url`, `request_method`, `follow_redirects`, `force_no_cache`, `latency_history_enabled`, `expected_status_codes`, `response_time_threshold_millis`, `expected_keyword`, `expected_keyword_case_sensitive`, `expected_keyword_negated` | HTTP                               |
| `next_expected_heartbeat`, `heartbeat_interval`, `grace_period`                                                                                                                                                                        | Push                               |
| `host`, `packet_count`, `timeout_seconds`, `packet_loss_threshold`, `metrics_history_enabled`                                                                                                                                          | ICMP                               |
| `host`, `port`, `timeout_ms`, `latency_threshold_ms`, `metrics_history_enabled`                                                                                                                                                        | TCP                                |
| `host`, `resolver_host`, `resolver_port`, `transport`, `record_matchers`, `expected_response_code`, `drift_detection_enabled`, `drift_record_types`, `timeout_ms`, `latency_threshold_ms`, `metrics_history_enabled`                   | DNS                                |
| `docker_host`, `container`, `image`, `timeout_ms`, `metrics_history_enabled`                                                                                                                                                           | Docker                             |

For DNS monitors, `record_matchers` is a list of readable `"<record type> <match type> <value>"` strings, e.g. `["A CONTAINS 93.184.216.34"]`. An empty list means the monitor asserts nothing about the records themselves and only checks that the lookup returns `expected_response_code`: with the default `NOERROR` that makes it `UP` whenever the name resolves, while a monitor expecting `NXDOMAIN`, `SERVFAIL` or `REFUSED` (which Kuvasz only allows with no matchers) is `UP` in exactly the opposite case.

`drift_detection_enabled` and `drift_record_types` are configuration only - drift is reported by your Kuvasz instance's notification integrations and never changes the `UP`/`DOWN` state. An empty `drift_record_types` does not mean drift detection is watching nothing: while enabled, it watches exactly the record types the matchers cover. Listing types there replaces that default, which is how a monitor watches a record it does not assert on.

For Docker monitors, `image` is the image the container was created from, as the latest check reported it, and is `null` when the container could not be inspected. Docker monitors record no latency; with metrics history enabled, the CPU and memory usage of the container is sampled instead.

**SSL binary sensor** is `on` when the certificate is `INVALID` (problem detected) and `off` otherwise (`VALID` or `WILL_EXPIRE`). Extra attributes: `ssl_status`, `ssl_error`, `ssl_expiry_threshold`, `ssl_status_started_at`, `last_ssl_check`, `next_ssl_check`, `ssl_valid_until`.

**Enabled binary sensor** reflects whether the monitor is currently enabled. It is present for every monitor regardless of whether the monitor type is writable.

**Enabled switch** lets you pause and resume a monitor directly from Home Assistant. It is only created for monitor types that are writable in your Kuvasz instance. Read-only monitor types (e.g. managed via YAML/GitOps) only get the binary sensor.

**Server version update entity** tracks the installed and latest available version of your Kuvasz instance. It belongs to the server device and takes its name. It is only created when update checks are enabled on your Kuvasz instance.

Every integration entry also has a server device, named after the entry (e.g. **Home Kuvasz**), which shows the installed Kuvasz version and links to your instance's web UI. The monitor devices are listed as connected through it.

## Requirements

- Home Assistant 2026.8 or newer
- Kuvasz Uptime 3.2.0 or newer
- A running [Kuvasz](https://kuvasz-uptime.dev) instance (self-hosted)
- Your [API key](https://kuvasz-uptime.dev/setup/configuration/#api-key) for your Kuvasz instance

## Installation

### Via HACS (recommended)

This integration is available in the default HACS store - no custom repository needed.

1. In Home Assistant, open **HACS**.
2. Search for **Kuvasz Uptime** and open it.
3. Click **Download**.
4. Restart Home Assistant.

Or use the direct link: [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=kuvasz-uptime&repository=ku-hass&category=integration)

### Manual

1. Copy `custom_components/kuvasz_uptime/` into your HA `config/custom_components/` directory.
2. Restart Home Assistant.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Kuvasz Uptime**.
3. Fill in the connection details (see below).
4. Select which monitors to expose as devices (all are selected by default).

| Parameter              | Description                                                                                                                             |
|------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| Instance name          | A name for this Kuvasz instance, used as the title of the integration entry. Must be unique across your Kuvasz entries.                 |
| Host URL               | The base URL of your Kuvasz instance, including the scheme and port, e.g. `http://192.168.1.10:8080`.                                    |
| API key                | The [API key](https://kuvasz-uptime.dev/setup/configuration/#api-key) of your instance. Leave it empty if your instance does not require one. |
| Verify SSL certificate | Turn this off if your instance uses a self-signed certificate (default: on).                                                            |
| Polling interval       | How often to refresh monitor state, in seconds (default: 30, min: 10, max: 3600).                                                       |
| Statistics period      | The time window for uptime ratio and average sensors: 1 hour, 6 hours, 12 hours, 1 day, 7 days or 30 days (default: 1 day).            |

Multiple instances can be added by repeating the setup with a different name and host. The same host can only be added once.

You can change options later via the **Configure** button on the integration card:

- **Polling interval** - how often to refresh monitor state (default: 30 s, min: 10 s, max: 3600 s)
- **Stats period** - the time window used for uptime percentage and response time stats (default: 24 h)
- **Monitor selection** - add or remove monitors without re-adding the integration

Monitors that are deselected, or deleted in Kuvasz, are removed from the HA device registry (including all their entities).

To change the instance URL, API key or SSL verification, choose **Reconfigure** from the integration entry's menu. If your API key is rotated or revoked, Home Assistant prompts you to re-authenticate with the new key under **Settings → Devices & Services**.

## Data updates

The integration polls your Kuvasz instance once per polling interval. Each poll fetches the instance settings, the monitor list, and the statistics of every selected monitor (at most 4 statistics requests run at the same time). Turning an **Enabled** switch on or off triggers an immediate refresh.

Kuvasz runs its own checks on each monitor's schedule, so a status change shows up in Home Assistant within one polling interval after Kuvasz detects it.

## Use cases

- Get a phone notification or a voice announcement when a website, server or container goes down.
- Flash a light or change a dashboard colour while any monitor is down.
- Get a reminder well before an SSL certificate expires.
- Pause monitors from an automation during planned maintenance, so Kuvasz does not alert on expected downtime.
- Track container CPU and memory usage of Docker monitors on Home Assistant dashboards.

## Examples

Entity IDs follow the pattern `<platform>.kuvasz_<monitor type>_<monitor name>_<entity>`, e.g. `binary_sensor.kuvasz_http_my_website_uptime_status`.

Notify when a monitor has been down for two minutes:

```yaml
automation:
  - alias: "Notify when My Website is down"
    triggers:
      - trigger: state
        entity_id: binary_sensor.kuvasz_http_my_website_uptime_status
        to: "off"
        for: "00:02:00"
    actions:
      - action: notify.notify
        data:
          message: >
            My Website is down: {{ state_attr(trigger.entity_id, 'uptime_error') }}
```

Get a reminder when an SSL certificate expires in less than 14 days:

```yaml
automation:
  - alias: "SSL certificate of My Website expires soon"
    triggers:
      - trigger: template
        value_template: >
          {% set valid_until = as_datetime(states('sensor.kuvasz_http_my_website_ssl_valid_until'), None) %}
          {{ valid_until is not none and valid_until < now() + timedelta(days=14) }}
    actions:
      - action: notify.notify
        data:
          message: "The SSL certificate of My Website expires on {{ states('sensor.kuvasz_http_my_website_ssl_valid_until') }}."
```

Pause a monitor during a nightly maintenance window:

```yaml
automation:
  - alias: "Pause My Website during maintenance"
    triggers:
      - trigger: time
        at: "02:00:00"
    actions:
      - action: switch.turn_off
        target:
          entity_id: switch.kuvasz_http_my_website_enabled
      - delay: "00:30:00"
      - action: switch.turn_on
        target:
          entity_id: switch.kuvasz_http_my_website_enabled
```

## Known limitations

- Monitors created in Kuvasz after the integration was set up are not added automatically. Select them via **Configure**.
- Entities are created when the integration loads. If you enable SSL checks or metrics history on a monitor, or change which monitor types are read-only in Kuvasz, reload the integration to add or remove the matching entities.
- The **Enabled** switch is only available for monitor types that are writable in your Kuvasz instance.
- Status pages and notification integrations configured in Kuvasz are not exposed in Home Assistant.
- Each poll makes one statistics request per selected monitor. With many monitors, consider a longer polling interval.

## Troubleshooting

**"Failed to connect to the given instance"**

- Make sure the host URL includes the scheme and port, e.g. `http://192.168.1.10:8080`.
- Check that the Kuvasz instance is reachable from the machine running Home Assistant (not just from your browser), especially when either runs in a container.
- If your instance uses a self-signed certificate, turn off **Verify SSL certificate**. For an existing entry, use **Reconfigure**.

**"Invalid API key"**

Check the API key in your Kuvasz configuration. If the key changed after setup, Home Assistant asks you to re-authenticate.

**A monitor or one of its entities is missing**

- Check that the monitor is selected under **Configure**.
- Average latency, packet loss, CPU and memory sensors only exist when latency or metrics history is enabled on the monitor. SSL sensors only exist when the SSL check is enabled. Reload the integration after changing these in Kuvasz.
- The **Enabled** switch is missing when the monitor type is read-only in Kuvasz.
- The update entity of the server device only exists when update checks are enabled on your instance.

**Collecting information for a bug report**

Enable debug logging from the integration page (**Enable debug logging**), or add this to `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.kuvasz_uptime: debug
```

You can also download diagnostics from the integration entry's menu (**Download diagnostics**). The API key, hosts, URLs and request headers and bodies are redacted from the file, but review it before attaching it to a public issue.

## Removal

1. Go to **Settings → Devices & Services → Kuvasz Uptime**.
2. Open the menu of the entry and choose **Delete**. This removes all of its devices and entities. Nothing changes on your Kuvasz instance.
3. To uninstall the integration itself, open **HACS**, find **Kuvasz Uptime**, choose **Remove** from its menu, and restart Home Assistant. For a manual installation, delete `config/custom_components/kuvasz_uptime/` and restart.

## Contributing

See [DEVELOPMENT.md](DEVELOPMENT.md).

## License

Apache 2.0
