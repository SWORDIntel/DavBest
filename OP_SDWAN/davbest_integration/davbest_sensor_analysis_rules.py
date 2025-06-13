# OP_SDWAN/davbest_integration/davbest_sensor_analysis_rules.py

import json
import binascii # For converting hex string to bytes

# Attempt to import the existing encryption_utils for context, though we'll define
# a more specific AES GCM decryption placeholder here for the sensor's output.
try:
    from OP_SDWAN.event_receiver.encryption_utils import ENCRYPTION_KEY as PYTHON_RECEIVER_KEY
    # Note: PYTHON_RECEIVER_KEY from encryption_utils.py is os.urandom(32) and
    # the decrypt_log_entry function there is a placeholder (Base64/UTF-8 decode).
    # The DavBestSensorModule uses a *fixed* AES key and actual AES-256-GCM.
except ImportError:
    print("Warning: Could not import encryption_utils.py. Using standalone key for sensor analysis.")
    PYTHON_RECEIVER_KEY = None # Indicates it's not available

# --- Configuration for DavBest Sensor Analysis ---

# This MUST match the key used in davbest_sensor_core.c
# For design purposes, this is the placeholder key. In production, this must be managed securely.
DAVBEST_SENSOR_AES_KEY = b"0123456789abcdef0123456789abcdef" # 32-byte key

# Expected log prefix from the C sensor module when printing hex-encoded encrypted logs
ENCRYPTED_LOG_PREFIX = "DAVBEST_ENCRYPTED_LOG_HEX: "

# --- Conceptual AES-256-GCM Decryption for Sensor Logs ---

def conceptual_aes_gcm_decrypt(hex_encrypted_packet: str, key: bytes) -> str:
    """
    Conceptual placeholder for AES-256-GCM decryption.
    The C module outputs: [12-byte Nonce][Ciphertext][16-byte Auth Tag] as a hex string.
    This function simulates the decryption process.

    Args:
        hex_encrypted_packet: The hex-encoded string of (Nonce + Ciphertext + Tag).
        key: The 32-byte AES key.

    Returns:
        The decrypted plaintext (JSON log string) if successful, else None.
    """
    if not hex_encrypted_packet.startswith(ENCRYPTED_LOG_PREFIX):
        print(f"Error: Log data missing expected prefix '{ENCRYPTED_LOG_PREFIX}'.")
        return None

    actual_hex_data = hex_encrypted_packet[len(ENCRYPTED_LOG_PREFIX):].strip()

    try:
        encrypted_bytes = binascii.unhexlify(actual_hex_data)
    except binascii.Error as e:
        print(f"Error: Could not convert hex string to bytes: {e}")
        return None

    if len(encrypted_bytes) < (12 + 16): # Nonce + Tag
        print(f"Error: Encrypted data too short to contain Nonce and Tag. Length: {len(encrypted_bytes)}")
        return None

    # --- Placeholder for OpenSSL EVP decryption ---
    # In a real Python implementation, you'd use a library like `cryptography`
    # from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    #
    # nonce = encrypted_bytes[:12]
    # ciphertext_with_tag = encrypted_bytes[12:]
    # tag = encrypted_bytes[-16:] # More accurately, tag is part of ciphertext_with_tag
    # ciphertext = ciphertext_with_tag[:-16]
    #
    # try:
    #     aesgcm = AESGCM(key)
    #     decrypted_payload = aesgcm.decrypt(nonce, ciphertext_with_tag, None) # No associated data (AAD)
    #     return decrypted_payload.decode('utf-8')
    # except InvalidTag: # from cryptography.exceptions import InvalidTag
    #     print("ERROR: AES-GCM decryption failed - Invalid Tag. Data may be tampered or key is wrong.")
    #     return None
    # except Exception as e:
    #     print(f"ERROR: AES-GCM decryption failed due to: {e}")
    #     return None
    # --- End of Placeholder ---

    # For this conceptual script, since we don't have OpenSSL or cryptography bindings
    # readily available in this environment for actual decryption, we'll simulate a
    # successful decryption IF the key matches the expected sensor key.
    # This is a MAJOR simplification for demonstration purposes.
    if key == DAVBEST_SENSOR_AES_KEY:
        # Simulate finding a JSON string. In reality, this part is the output of aesgcm.decrypt.
        # We can't actually get the plaintext without real decryption.
        # Let's assume if the key is right, we *would* get a JSON.
        # We will return a placeholder JSON indicating it was "conceptually decrypted".
        # This allows the rest of the parsing and rule logic to be demonstrated.

        # To make it slightly more realistic for testing, if the hex string contains
        # a known pattern that would be part of the *plaintext* JSON, we can use that.
        # For example, if we know logs contain `{"module":"DavBestSensorModule"}`
        # This is still a hack, real decryption is needed.

        # For now, return a fixed placeholder if key is correct.
        # In a real scenario, this would be the actual decrypted JSON.
        return '{"timestamp": "YYYY-MM-DDTHH:MM:SSZ", "module": "DavBestSensorModule", "probe_type": "FILE_WRITE_ATTEMPT", "target": "/host_root/etc/passwd", "status": "CRITICAL_SUCCESS", "details": "Conceptual: Host path modification was unexpectedly permitted (Simulated Decryption).", "errno": 0}'
    else:
        print("Error: Conceptual decryption failed - Key mismatch (simulated).")
        return None

# --- Log Parsing and Analysis ---

def parse_sensor_log(decrypted_log_json: str) -> dict:
    """
    Parses the decrypted JSON log string into a Python dictionary.

    Args:
        decrypted_log_json: The JSON string from the sensor.

    Returns:
        A dictionary representing the log entry, or None if parsing fails.
    """
    try:
        log_entry = json.loads(decrypted_log_json)
        # Basic validation of expected fields (can be expanded)
        if not all(k in log_entry for k in ["timestamp", "module", "status", "target"]):
            print(f"Error: Parsed log missing essential fields: {log_entry}")
            return None
        if log_entry["module"] != "DavBestSensorModule":
            print(f"Warning: Log is not from DavBestSensorModule: {log_entry.get('module')}")
            # Decide if this should be an error or just a filter
        return log_entry
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse JSON from sensor log: {e}")
        return None

# --- Anomaly Detection Rules ---

def analyze_log_entry_for_anomalies(log_entry: dict) -> list:
    """
    Analyzes a parsed log entry to detect integrity violations.

    Args:
        log_entry: A dictionary representing the parsed log data.

    Returns:
        A list of alert messages for any detected anomalies.
    """
    alerts = []
    if not log_entry:
        return alerts

    # Rule: Detect CRITICAL_SUCCESS status for integrity probes
    # These indicate that a write attempt to a protected host path was permitted.
    if log_entry.get("status") == "CRITICAL_SUCCESS":
        alert_message = (
            f"CRITICAL INTEGRITY VIOLATION: DavBest Sensor reported unexpected success. "
            f"Target: '{log_entry.get('target', 'N/A')}', "
            f"Details: '{log_entry.get('details', 'N/A')}', "
            f"Timestamp: {log_entry.get('timestamp', 'N/A')}"
        )
        alerts.append(alert_message)
        # Potentially add more context or severity scoring here

    # Rule: Detect other interesting events (e.g., module lifecycle, errors)
    elif log_entry.get("status") == "INFO" and "Module loaded" in log_entry.get("details", ""):
        print(f"Info: DavBest Sensor Module '{log_entry.get('target')}' loaded at {log_entry.get('timestamp')}")
    elif log_entry.get("status") == "SKIPPING" and "Mount point not accessible" in log_entry.get("details", ""):
         print(f"Warning: DavBest Sensor Module could not access mount point '{log_entry.get('target')}' at {log_entry.get('timestamp')}")


    # Add more rules here as needed, e.g., for:
    # - Unexpected errors reported by the sensor.
    # - Failures in the sensor's own operations (e.g., cleanup).

    return alerts

# --- Alerting (Conceptual) ---

def generate_davbest_alerts(alerts: list):
    """
    Conceptual function for generating high-priority alerts within DavBest.
    In a real system, this would integrate with DavBest's alerting framework
    (e.g., send to a SIEM, dashboard, notification service).
    """
    if not alerts:
        return

    print("\n--- DAVBEST HIGH-PRIORITY ALERTS ---")
    for alert in alerts:
        print(f"[ALERT] {alert}")
    print("--- END OF ALERTS ---\n")
    # Here, you would integrate with actual alert mechanisms:
    # - push_to_davbest_dashboard(alert)
    # - send_email_notification(alert)
    # - create_jira_ticket(alert)

# --- Main Processing Logic ---

def process_raw_sensor_input(raw_input_line: str):
    """
    Processes a single line of raw input, which is expected to be
    the hex-encoded encrypted log from the DavBest Sensor Module.
    """
    print(f"Received Raw Input: {raw_input_line.strip()}")

    # 1. Decrypt (Conceptual AES-GCM)
    # Using the DAVBEST_SENSOR_AES_KEY defined in this script.
    decrypted_json = conceptual_aes_gcm_decrypt(raw_input_line, DAVBEST_SENSOR_AES_KEY)

    if not decrypted_json:
        print("Failed to decrypt sensor log. No further processing.")
        # Potentially generate an alert about decryption failure if it's unexpected
        # generate_davbest_alerts(["DECRYPTION_FAILURE: Could not decrypt a sensor log."])
        return

    print(f"Conceptually Decrypted JSON: {decrypted_json}") # For demonstration

    # 2. Parse
    log_entry = parse_sensor_log(decrypted_json)
    if not log_entry:
        print("Failed to parse sensor log. No further processing.")
        # generate_davbest_alerts(["PARSING_FAILURE: Could not parse a decrypted sensor log."])
        return

    print(f"Parsed Log Entry: {log_entry}")


    # 3. Analyze for Anomalies
    anomalies = analyze_log_entry_for_anomalies(log_entry)

    # 4. Generate Alerts
    if anomalies:
        generate_davbest_alerts(anomalies)
    else:
        print("No critical anomalies detected in this log entry.")


if __name__ == "__main__":
    print("Starting DavBest Sensor Analysis Rules Processor (Conceptual Test)...")

    # Example raw input lines (simulating what might be captured from C module's stdout)
    # This is a placeholder for actual encrypted data.
    # The conceptual_aes_gcm_decrypt function will return a fixed JSON if the key is right.
    # To make this test runnable, we'll use a simple string that matches the prefix.

    # Scenario 1: Critical Success (Simulated)
    # A real hex string would be very long. This is just to trigger the prefix logic.
    # The actual content of the hex string is ignored by the current conceptual_aes_gcm_decrypt,
    # which returns a fixed "CRITICAL_SUCCESS" JSON if the key matches.
    example_hex_log_critical = f"{ENCRYPTED_LOG_PREFIX}aabbccddeeff... (real hex would be here)"

    # Scenario 2: Expected Failure (Simulated by modifying the conceptual_aes_gcm_decrypt output for testing)
    # To test other scenarios, we would need to make conceptual_aes_gcm_decrypt more flexible
    # or have example pre-canned encrypted hex strings that decrypt to different JSONs.
    # For now, the conceptual decryptor always outputs a "CRITICAL_SUCCESS" or fails.
    # Let's simulate a log that *would not* be a critical success after parsing.

    # To demonstrate parsing of a non-critical log, we can directly call parse_sensor_log
    # with a sample JSON string.
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

    print("\n--- Test Case 1: Processing a 'CRITICAL_SUCCESS' (Simulated Decryption) ---")
    process_raw_sensor_input(example_hex_log_critical)

    print("\n--- Test Case 2: Processing an 'EXPECTED_FAILURE' (Direct JSON) ---")
    # Directly test parsing and analysis for a non-critical log
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

    print("\n--- Test Case 4: Incorrect Key (Simulated Decryption Failure) ---")
    # Temporarily use a wrong key for conceptual_aes_gcm_decrypt
    original_key = DAVBEST_SENSOR_AES_KEY
    DAVBEST_SENSOR_AES_KEY = b"wrongkeyforthismodulecantdecrypt!" # Must be 32 bytes
    process_raw_sensor_input(example_hex_log_critical) # Should fail decryption
    DAVBEST_SENSOR_AES_KEY = original_key # Reset key

    print("\nDavBest Sensor Analysis Rules Processor (Conceptual Test) Finished.")

```
