# OP_SDWAN/davbest_integration/davbest_sensor_analysis_rules.py

import json
import binascii # For converting hex string to bytes
import argparse # Added for command-line argument parsing

# Attempt to import the existing encryption_utils for context, though we'll define
# a more specific AES GCM decryption placeholder here for the sensor's output.
try:
    from OP_SDWAN.event_receiver.encryption_utils import ENCRYPTION_KEY as PYTHON_RECEIVER_KEY
except ImportError:
    print("Warning: Could not import encryption_utils.py. Using standalone key for sensor analysis.")
    PYTHON_RECEIVER_KEY = None

DAVBEST_SENSOR_AES_KEY = b"0123456789abcdef0123456789abcdef"
ENCRYPTED_LOG_PREFIX = "DAVBEST_ENCRYPTED_LOG_HEX: "

def conceptual_aes_gcm_decrypt(hex_encrypted_packet: str, key: bytes) -> str:
    if not hex_encrypted_packet.startswith(ENCRYPTED_LOG_PREFIX):
        # print(f"Debug: Line does not start with prefix: {hex_encrypted_packet[:100]}") # Keep short
        return None

    actual_hex_data = hex_encrypted_packet[len(ENCRYPTED_LOG_PREFIX):].strip()

    try:
        encrypted_bytes = binascii.unhexlify(actual_hex_data)
    except binascii.Error as e:
        print(f"Error: Could not convert hex string to bytes for line '{actual_hex_data[:50]}...': {e}")
        return None

    if len(encrypted_bytes) < (12 + 16): # Nonce + Tag
        print(f"Error: Encrypted data too short. Length: {len(encrypted_bytes)} for line '{actual_hex_data[:50]}...'")
        return None

    if key == DAVBEST_SENSOR_AES_KEY:
        # SIMULATED DECRYPTION for demonstration if key matches
        # In a real scenario, this would be actual decryption logic returning diverse plaintexts.
        # This placeholder returns a fixed CRITICAL_SUCCESS JSON.
        # For robust testing of parsing various log types, this function would need to be
        # replaced with actual decryption or a more sophisticated mock.
        return '{"timestamp": "YYYY-MM-DDTHH:MM:SSZ", "module": "DavBestSensorModule", "probe_type": "FILE_WRITE_ATTEMPT", "target": "/host_root/etc/passwd", "status": "CRITICAL_SUCCESS", "details": "Conceptual: Host path modification was unexpectedly permitted (Simulated Decryption from file line).", "errno": 0}'
    else:
        print(f"Error: Conceptual decryption failed - Key mismatch (simulated) for line '{actual_hex_data[:50]}...'.")
        return None

def parse_sensor_log(decrypted_log_json: str) -> dict:
    try:
        log_entry = json.loads(decrypted_log_json)
        if not all(k in log_entry for k in ["timestamp", "module", "status", "target"]):
            print(f"Error: Parsed log missing essential fields: {log_entry}")
            return None
        if log_entry["module"] != "DavBestSensorModule":
            print(f"Warning: Log is not from DavBestSensorModule: {log_entry.get('module')}")
        return log_entry
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON from sensor log: {e} (Source: '{decrypted_log_json[:100]}...')")
        return None

def analyze_log_entry_for_anomalies(log_entry: dict) -> list:
    alerts = []
    if not log_entry:
        return alerts

    if log_entry.get("status") == "CRITICAL_SUCCESS":
        alert_message = (
            f"CRITICAL INTEGRITY VIOLATION: DavBest Sensor reported unexpected success. "
            f"Target: '{log_entry.get('target', 'N/A')}', "
            f"Details: '{log_entry.get('details', 'N/A')}', "
            f"Timestamp: {log_entry.get('timestamp', 'N/A')}"
        )
        alerts.append(alert_message)
    elif log_entry.get("status") == "INFO" and "Module loaded" in log_entry.get("details", ""):
        print(f"Info: DavBest Sensor Module '{log_entry.get('target')}' loaded at {log_entry.get('timestamp')}")
    elif log_entry.get("status") == "SKIPPING":
         print(f"Warning: DavBest Sensor Module reported issue: Target '{log_entry.get('target')}', Details: '{log_entry.get('details', '')}' at {log_entry.get('timestamp')}")
    # Add more rules for other statuses like EXPECTED_FAILURE if detailed non-critical reporting is desired.
    # For now, focusing on CRITICAL_SUCCESS for alerts.
    return alerts

def generate_davbest_alerts(alerts: list):
    if not alerts:
        return

    print("\n--- DAVBEST HIGH-PRIORITY ALERTS ---")
    for alert in alerts:
        print(f"[ALERT] {alert}")
    print("--- END OF ALERTS ---\n")

def process_raw_sensor_input_line(raw_input_line: str): # Renamed to avoid confusion
    # print(f"Processing Raw Input Line: {raw_input_line.strip()}") # Can be verbose
    decrypted_json = conceptual_aes_gcm_decrypt(raw_input_line, DAVBEST_SENSOR_AES_KEY)
    if not decrypted_json:
        # print(f"Failed to decrypt sensor log line: {raw_input_line.strip()}") # Already printed in decrypt
        return

    # print(f"Conceptually Decrypted JSON: {decrypted_json}")
    log_entry = parse_sensor_log(decrypted_json)
    if not log_entry:
        # print(f"Failed to parse sensor log line: {decrypted_json}") # Already printed in parse
        return

    # print(f"Parsed Log Entry: {log_entry}")
    anomalies = analyze_log_entry_for_anomalies(log_entry)
    if anomalies:
        generate_davbest_alerts(anomalies)
    # else:
        # print("No critical anomalies detected in this log entry.") # Can be verbose

def run_example_tests():
    print("Running built-in example tests...")
    # Scenario 1: Critical Success (Simulated)
    example_hex_log_critical = f"{ENCRYPTED_LOG_PREFIX}aabbccddeeff... (real hex would be here)"

    example_json_expected_failure = '''
    {
        "timestamp": "2023-10-27T10:00:00Z",
        "module": "DavBestSensorModule",
        "probe_type": "FILE_WRITE_ATTEMPT",
        "target": "/host_root/etc/shadow",
        "status": "EXPECTED_FAILURE",
        "details": "Host path modification denied as expected.",
        "errno": 13
    }
    '''
    example_json_module_load = '''
    {
        "timestamp": "2023-10-27T09:59:00Z",
        "module": "DavBestSensorModule",
        "probe_type": "MODULE_LIFECYCLE",
        "target": "DavBestSensorModule.so",
        "status": "INFO",
        "details": "Module loaded, starting integrity scan.",
        "errno": 0
    }
    '''

    print("\n--- Test Case 1: Processing a 'CRITICAL_SUCCESS' (Simulated Decryption from string) ---")
    process_raw_sensor_input_line(example_hex_log_critical)

    print("\n--- Test Case 2: Processing an 'EXPECTED_FAILURE' (Direct JSON) ---")
    parsed_log_expected = parse_sensor_log(example_json_expected_failure)
    if parsed_log_expected:
        anomalies_expected = analyze_log_entry_for_anomalies(parsed_log_expected)
        generate_davbest_alerts(anomalies_expected)
        if not anomalies_expected:
             print("No critical anomalies detected in 'EXPECTED_FAILURE' log, as expected.")
    else:
        print("Failed to parse example_json_expected_failure")

    print("\n--- Test Case 3: Processing a 'MODULE_LIFECYCLE' (Direct JSON) ---")
    parsed_log_lifecycle = parse_sensor_log(example_json_module_load)
    if parsed_log_lifecycle:
        anomalies_lifecycle = analyze_log_entry_for_anomalies(parsed_log_lifecycle)
        generate_davbest_alerts(anomalies_lifecycle)
        if not anomalies_lifecycle:
             print("No critical anomalies detected in 'MODULE_LIFECYCLE' log, as expected.")
    else:
        print("Failed to parse example_json_module_load")

    print("\n--- Test Case 4: Incorrect Key (Simulated Decryption Failure from string) ---")
    # global DAVBEST_SENSOR_AES_KEY # Allow modification for test
    original_key = DAVBEST_SENSOR_AES_KEY # This will now refer to the module-level global
    # DAVBEST_SENSOR_AES_KEY = b"wrongkeyforthismodulecantdecrypt!" # Must be 32 bytes
    process_raw_sensor_input_line(example_hex_log_critical) # Should fail decryption (if key was changed)
    # DAVBEST_SENSOR_AES_KEY = original_key # Reset key
    print("\nBuilt-in example tests finished.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DavBest Sensor Log Analyzer. Processes encrypted logs from a file.")
    parser.add_argument("logfile", type=str, nargs='?', help="Path to the log file containing hex-encoded encrypted sensor logs.")

    args = parser.parse_args()

    if args.logfile:
        print(f"Starting DavBest Sensor Analysis Rules Processor for log file: {args.logfile}")
        try:
            with open(args.logfile, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    stripped_line = line.strip()
                    if stripped_line: # Ensure line is not empty
                        # print(f"Processing line {line_num} from {args.logfile}...") # Verbose
                        process_raw_sensor_input_line(stripped_line)
            print(f"Finished processing log file: {args.logfile}")
        except FileNotFoundError:
            print(f"Error: Log file not found: {args.logfile}")
        except Exception as e:
            print(f"Error processing log file {args.logfile}: {e}")
    else:
        print("No log file provided. Running built-in example tests instead.")
        run_example_tests()

```
