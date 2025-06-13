# OP_SDWAN/davbest_integration/davbest_alert_manager.py

import json

DEFAULT_SOURCE_IP = "sensor_host_N/A" # Placeholder for source IP/hostname
DEFAULT_SEVERITY = "CRITICAL"

def generate_critical_integrity_alert(timestamp: str, probe_path: str, outcome: str, details: str, source_ip: str = None, severity: str = None):
    if source_ip is None:
        source_ip = DEFAULT_SOURCE_IP
    if severity is None:
        severity = DEFAULT_SEVERITY

    alert_data = {
        "alert_type": "CriticalIntegrityAlert",
        "timestamp": timestamp,
        "source_system": source_ip,
        "severity": severity,
        "probe_target": probe_path,
        "probe_outcome": outcome,
        "description": details,
        "remediation_guidance": "Investigate immediately: A sensor reported an unexpected successful modification attempt on a critical host path."
    }
    print(f"DAVBEST_ALERT_JSON: {json.dumps(alert_data)}")

if __name__ == "__main__":
    print("Testing davbest_alert_manager.py...")
    generate_critical_integrity_alert(
        timestamp="2023-01-01T12:00:00Z",
        probe_path="/host_root/etc/passwd",
        outcome="CRITICAL_SUCCESS",
        details="Write attempt was unexpectedly permitted.",
        source_ip="container_test_01"
    )
    generate_critical_integrity_alert(
        timestamp="2023-01-01T12:05:00Z",
        probe_path="/host_root/root/.ssh/authorized_keys",
        outcome="CRITICAL_SUCCESS",
        details="Append operation succeeded unexpectedly."
    )
    print("davbest_alert_manager.py test complete.")
