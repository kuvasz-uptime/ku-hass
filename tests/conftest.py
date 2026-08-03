"""Shared fixtures for Kuvasz integration tests."""

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Allow HA to discover integrations under custom_components/."""
    return


# ---------------------------------------------------------------------------
# API response fixtures (match Kuvasz DTO field names exactly)
# ---------------------------------------------------------------------------

HTTP_MONITOR_UP = {
    "id": 1,
    "name": "My Website",
    "url": "https://example.com",
    "sensitiveUrl": False,
    "uptimeCheckInterval": 60,
    "enabled": True,
    "sslCheckEnabled": True,
    "requestMethod": "GET",
    "latencyHistoryEnabled": True,
    "forceNoCache": False,
    "followRedirects": True,
    "sslExpiryThreshold": 30,
    "failureCountThreshold": 1,
    "integrations": [],
    "expectedStatusCodes": [200],
    "requestHeaders": {},
    "expectedHeaders": {},
    "requestBody": None,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": None,
    "uptimeStatus": "UP",
    "sslStatus": "VALID",
    "uptimeStatusStartedAt": "2024-01-01T00:00:00Z",
    "lastUptimeCheck": "2024-01-01T01:00:00Z",
    "nextUptimeCheck": "2024-01-01T01:01:00Z",
    "sslStatusStartedAt": "2024-01-01T00:00:00Z",
    "lastSSLCheck": "2024-01-01T01:00:00Z",
    "nextSSLCheck": "2024-01-01T01:01:00Z",
    "uptimeError": None,
    "sslError": None,
    "sslValidUntil": "2025-01-01T00:00:00Z",
    "responseTimeThresholdMillis": None,
    "expectedKeyword": None,
    "expectedKeywordCaseSensitive": False,
    "expectedKeywordNegated": False,
    "effectiveIntegrations": [],
    "statusPages": [],
    "_type": "http",
}

HTTP_MONITOR_DOWN = {
    **HTTP_MONITOR_UP,
    "id": 2,
    "name": "Down Service",
    "uptimeStatus": "DOWN",
    "sslStatus": "INVALID",
    "sslCheckEnabled": True,
}

HTTP_MONITOR_NO_SSL = {
    **HTTP_MONITOR_UP,
    "id": 3,
    "name": "No SSL Monitor",
    "sslCheckEnabled": False,
    "sslStatus": None,
}

PUSH_MONITOR_UP = {
    "id": 20,
    "name": "My Cron Job",
    "heartbeatInterval": 300,
    "gracePeriod": 60,
    "enabled": True,
    "failureCountThreshold": 1,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": None,
    "uptimeStatus": "UP",
    "uptimeStatusStartedAt": "2024-01-01T00:00:00Z",
    "lastUptimeCheck": "2024-01-01T01:00:00Z",
    "lastHeartbeat": "2024-01-01T01:00:00Z",
    "nextExpectedHeartbeat": "2024-01-01T01:05:00Z",
    "uptimeError": None,
    "integrations": [],
    "effectiveIntegrations": [],
    "statusPages": [],
    "_type": "push",
}

HTTP_MONITOR_STATS = {
    "id": 1,
    "latencyHistoryEnabled": True,
    "latencyStats": {
        "averageLatencyInMs": 123,
        "minLatencyInMs": 80,
        "maxLatencyInMs": 200,
        "p90LatencyInMs": 180,
        "p95LatencyInMs": 195,
        "p99LatencyInMs": 199,
    },
    "uptimeHistory": {
        "period": "PT24H",
        "incidents": 0,
        "affectedMonitors": 0,
        "uptimeRatio": 0.9987,
        "totalDowntimeSeconds": 45,
    },
    "latencyLogs": [],
}

HTTP_MONITOR_STATS_NO_LATENCY = {
    "id": 2,
    "latencyHistoryEnabled": False,
    "latencyStats": None,
    "uptimeHistory": {
        "period": "PT24H",
        "incidents": 1,
        "affectedMonitors": 1,
        "uptimeRatio": 0.5,
        "totalDowntimeSeconds": 43200,
    },
    "latencyLogs": [],
}

PUSH_MONITOR_STATS = {
    "id": 20,
    "uptimeHistory": {
        "period": "PT24H",
        "incidents": 0,
        "affectedMonitors": 0,
        "uptimeRatio": None,
        "totalDowntimeSeconds": 0,
    },
}

ICMP_MONITOR_UP = {
    "id": 30,
    "name": "My Server",
    "host": "192.168.1.1",
    "uptimeCheckInterval": 60,
    "packetCount": 3,
    "timeoutSeconds": 5,
    "packetLossThreshold": 100,
    "failureCountThreshold": 1,
    "metricsHistoryEnabled": True,
    "enabled": True,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-02T00:00:00Z",
    "uptimeStatus": "UP",
    "uptimeStatusStartedAt": "2024-01-01T00:00:00Z",
    "lastUptimeCheck": "2024-01-01T01:00:00Z",
    "nextUptimeCheck": "2024-01-01T01:01:00Z",
    "uptimeError": None,
    "integrations": [],
    "effectiveIntegrations": [],
    "statusPages": [],
    "_type": "icmp",
}

ICMP_MONITOR_DOWN = {
    **ICMP_MONITOR_UP,
    "id": 31,
    "name": "Down Server",
    "uptimeStatus": "DOWN",
}

ICMP_MONITOR_STATS = {
    "id": 30,
    "metricsHistoryEnabled": True,
    "uptimeHistory": {
        "period": "PT24H",
        "incidents": 0,
        "affectedMonitors": 0,
        "uptimeRatio": 0.9999,
        "totalDowntimeSeconds": 5,
    },
    "latencyStats": {
        "averageLatencyInMs": 10,
        "minLatencyInMs": 5,
        "maxLatencyInMs": 20,
        "p90LatencyInMs": 18,
        "p95LatencyInMs": 19,
        "p99LatencyInMs": 20,
    },
    "packetLossStats": {
        "averagePacketLossPercentage": 0,
        "minPacketLossPercentage": 0,
        "maxPacketLossPercentage": 0,
        "p90PacketLossPercentage": 0,
        "p95PacketLossPercentage": 0,
        "p99PacketLossPercentage": 0,
    },
    "metricsLogs": [],
}

TCP_MONITOR_UP = {
    "id": 40,
    "name": "My Database",
    "host": "192.168.1.2",
    "port": 5432,
    "uptimeCheckInterval": 60,
    "timeoutMs": 5000,
    "latencyThresholdMs": 1000,
    "failureCountThreshold": 1,
    "metricsHistoryEnabled": True,
    "enabled": True,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-02T00:00:00Z",
    "uptimeStatus": "UP",
    "uptimeStatusStartedAt": "2024-01-01T00:00:00Z",
    "lastUptimeCheck": "2024-01-01T01:00:00Z",
    "nextUptimeCheck": "2024-01-01T01:01:00Z",
    "uptimeError": None,
    "integrations": [],
    "effectiveIntegrations": [],
    "statusPages": [],
    "maintenanceWindows": [],
    "inMaintenance": False,
    "_type": "tcp",
}

TCP_MONITOR_DOWN = {
    **TCP_MONITOR_UP,
    "id": 41,
    "name": "Down Database",
    "uptimeStatus": "DOWN",
}

TCP_MONITOR_STATS = {
    "id": 40,
    "metricsHistoryEnabled": True,
    "uptimeHistory": {
        "period": "PT24H",
        "incidents": 0,
        "affectedMonitors": 0,
        "uptimeRatio": 0.9995,
        "totalDowntimeSeconds": 10,
    },
    "latencyStats": {
        "averageLatencyInMs": 15,
        "minLatencyInMs": 8,
        "maxLatencyInMs": 30,
        "p90LatencyInMs": 25,
        "p95LatencyInMs": 28,
        "p99LatencyInMs": 30,
    },
    "metricsLogs": [],
}

DNS_MONITOR_UP = {
    "id": 50,
    "name": "My Domain",
    "host": "example.com",
    "resolverHost": "1.1.1.1",
    "resolverPort": 53,
    "transport": "UDP",
    "recordMatchers": [
        {"recordType": "A", "matchType": "CONTAINS", "value": "93.184.216.34"},
        {"recordType": "MX", "matchType": "EXACT", "value": "10 mail.example.com"},
    ],
    "expectedResponseCode": "NOERROR",
    "driftDetectionEnabled": True,
    "driftRecordTypes": ["NS", "MX"],
    "uptimeCheckInterval": 60,
    "timeoutMs": 5000,
    "latencyThresholdMs": 1000,
    "failureCountThreshold": 1,
    "metricsHistoryEnabled": True,
    "enabled": True,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-02T00:00:00Z",
    "uptimeStatus": "UP",
    "uptimeStatusStartedAt": "2024-01-01T00:00:00Z",
    "lastUptimeCheck": "2024-01-01T01:00:00Z",
    "nextUptimeCheck": "2024-01-01T01:01:00Z",
    "uptimeError": None,
    "integrations": [],
    "effectiveIntegrations": [],
    "statusPages": [],
    "maintenanceWindows": [],
    "inMaintenance": False,
    "_type": "dns",
}

# Also covers the nullable fields: no custom resolver, no latency threshold,
# and a monitor that asserts nothing (plain A lookup).
DNS_MONITOR_DOWN = {
    **DNS_MONITOR_UP,
    "id": 51,
    "name": "Down Domain",
    "resolverHost": None,
    "latencyThresholdMs": None,
    "recordMatchers": [],
    "driftDetectionEnabled": False,
    "driftRecordTypes": [],
    "uptimeStatus": "DOWN",
}

DNS_MONITOR_STATS = {
    "id": 50,
    "metricsHistoryEnabled": True,
    "uptimeHistory": {
        "period": "PT24H",
        "incidents": 0,
        "affectedMonitors": 0,
        "uptimeRatio": 0.9998,
        "totalDowntimeSeconds": 5,
    },
    "latencyStats": {
        "averageLatencyInMs": 12,
        "minLatencyInMs": 5,
        "maxLatencyInMs": 40,
        "p90LatencyInMs": 20,
        "p95LatencyInMs": 30,
        "p99LatencyInMs": 40,
    },
    "metricsLogs": [],
}

SETTINGS_RESPONSE = {
    "versionInfo": {
        "installedVersion": "2.1.0",
        "latestVersion": "2.2.0",
        "latestVersionDetails": "https://github.com/kuvasz-uptime/kuvasz/releases/tag/v2.2.0",
        "isUpToDate": False,
    },
    "app": {
        "editabilityState": {
            "areHttpMonitorsReadOnly": False,
            "areStatusPagesReadOnly": False,
            "arePushMonitorsReadOnly": False,
            "areIcmpMonitorsReadOnly": False,
            "areTcpMonitorsReadOnly": False,
            "areDnsMonitorsReadOnly": False,
        },
        "updateChecksEnabled": True,
    },
}

SETTINGS_RESPONSE_READ_ONLY = {
    **SETTINGS_RESPONSE,
    "app": {
        "editabilityState": {
            "areHttpMonitorsReadOnly": True,
            "areStatusPagesReadOnly": True,
            "arePushMonitorsReadOnly": True,
            "areIcmpMonitorsReadOnly": True,
            "areTcpMonitorsReadOnly": True,
            "areDnsMonitorsReadOnly": True,
        }
    },
}

# An instance predating ICMP, TCP and DNS monitors.
SETTINGS_RESPONSE_NO_ICMP = {
    "app": {
        "editabilityState": {
            "areHttpMonitorsReadOnly": False,
            "areStatusPagesReadOnly": False,
            "arePushMonitorsReadOnly": False,
        }
    },
}

# An instance that knows about ICMP monitors, but predates TCP and DNS ones.
SETTINGS_RESPONSE_NO_TCP = {
    "app": {
        "editabilityState": {
            "areHttpMonitorsReadOnly": False,
            "areStatusPagesReadOnly": False,
            "arePushMonitorsReadOnly": False,
            "areIcmpMonitorsReadOnly": False,
        }
    },
}

# An instance that knows about ICMP and TCP monitors, but predates DNS ones.
SETTINGS_RESPONSE_NO_DNS = {
    "app": {
        "editabilityState": {
            "areHttpMonitorsReadOnly": False,
            "areStatusPagesReadOnly": False,
            "arePushMonitorsReadOnly": False,
            "areIcmpMonitorsReadOnly": False,
            "areTcpMonitorsReadOnly": False,
        }
    },
}
