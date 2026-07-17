"""Constants for the Kuvasz Uptime integration."""

DOMAIN = "kuvasz_uptime"

CONF_API_KEY = "api_key"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SELECTED_MONITORS = "selected_monitors"
CONF_STATS_PERIOD = "stats_period"
CONF_VERIFY_SSL = "verify_ssl"

DEFAULT_VERIFY_SSL = True

DEFAULT_SCAN_INTERVAL = 30  # seconds
MIN_SCAN_INTERVAL = 10
MAX_SCAN_INTERVAL = 3600

DEFAULT_STATS_PERIOD = "P1D"
STATS_PERIOD_OPTIONS = [
    {"value": "PT1H", "label": "1 hour"},
    {"value": "PT6H", "label": "6 hours"},
    {"value": "PT12H", "label": "12 hours"},
    {"value": "P1D", "label": "1 day"},
    {"value": "P7D", "label": "7 days"},
    {"value": "P30D", "label": "30 days"},
]

API_BASE = "/api/v2"
API_HTTP_MONITORS = f"{API_BASE}/http-monitors"
API_PUSH_MONITORS = f"{API_BASE}/push-monitors"
API_ICMP_MONITORS = f"{API_BASE}/icmp-monitors"
API_TCP_MONITORS = f"{API_BASE}/tcp-monitors"

MONITOR_TYPE_HTTP = "http"
MONITOR_TYPE_PUSH = "push"
MONITOR_TYPE_ICMP = "icmp"
MONITOR_TYPE_TCP = "tcp"

UPTIME_STATUS_UP = "UP"

SSL_STATUS_INVALID = "INVALID"
