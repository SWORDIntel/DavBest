# OP_SDWAN/davbest_integration/davbest_sensor_analysis_rules.py

import json
import binascii
import argparse
import sys # Added for sys.path manipulation
import os  # Added for os.path manipulation

# Add the project root to sys.path to allow absolute imports like OP_SDWAN.davbest_integration
# Assuming this script is in OP_SDWAN/davbest_integration/
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import from the new alert manager
from OP_SDWAN.davbest_integration.davbest_alert_manager import generate_critical_integrity_alert

try:
    from OP_SDWAN.event_receiver.encryption_utils import ENCRYPTION_KEY as PYTHON_RECEIVER_KEY
except ImportError:
    PYTHON_RECEIVER_KEY = None

DAVBEST_SENSOR_AES_KEY = b"0123456789abcdef0123456789abcdef"
ENCRYPTED_LOG_PREFIX = "DAVBEST_ENCRYPTED_LOG_HEX: "

def conceptual_aes_gcm_decrypt(hex_encrypted_packet: str, key: bytes) -> dict: # Returns dict
    if not hex_encrypted_packet.startswith(ENCRYPTED_LOG_PREFIX):
        return None
    actual_hex_data = hex_encrypted_packet[len(ENCRYPTED_LOG_PREFIX):].strip()
    try:
        encrypted_bytes = binascii.unhexlify(actual_hex_data)
    except binascii.Error:
        return None
    if len(encrypted_bytes) < (12 + 16):
        return None
    if key == DAVBEST_SENSOR_AES_KEY:
        # Return a dictionary directly
        return {"timestamp": "YYYY-MM-DDTHH:MM:SSZ", "module": "DavBestSensorModule", "probe_type": "FILE_WRITE_ATTEMPT", "target": "/host_root/etc/passwd", "status": "CRITICAL_SUCCESS", "details": "Conceptual: Host path modification was unexpectedly permitted (Simulated Decryption from file line).", "errno": 0}
    else:
        return None

def parse_sensor_log(decrypted_log_data: dict) -> dict: # Expects dict
    # Input is now already a dictionary from conceptual_aes_gcm_decrypt
    log_entry = decrypted_log_data
    if not log_entry: # Check if it_s None or empty
        return None

    # Ensure essential keys for alerting are present
    if not all(k in log_entry for k in ["timestamp", "status", "target", "details"]):
        # print(f"Warning: Log entry missing one or more essential fields for alerting (timestamp, status, target, details): {log_entry}")
        return None
    if log_entry.get("module") != "DavBestSensorModule": # .get() is safer
        # This is a warning, not a critical parsing error for the alert itself
        # print(f"Warning: Log is not from DavBestSensorModule: {log_entry.get("module")}")
        pass
    return log_entry

def analyze_log_entry_for_anomalies(log_entry: dict): # No longer returns list, calls alert manager directly
    if not log_entry:
        return

    if log_entry.get("status") == "CRITICAL_SUCCESS":
        # Call the new alert manager function
        generate_critical_integrity_alert(
            timestamp=log_entry.get("timestamp", "N/A"),
            probe_path=log_entry.get("target", "N/A"),
            outcome=log_entry.get("status", "N/A"), # Should be "CRITICAL_SUCCESS"
            details=log_entry.get("details", "N/A")
            # source_ip could be passed if available, e.g. from container metadata
        )
    # Other statuses like "INFO" or "SKIPPING" are not generating alerts via the manager for now
    # else:
        # print(f"Debug: Log entry status is not CRITICAL_SUCCESS: {log_entry.get("status")}")


def process_raw_sensor_input_line(raw_input_line: str):
    decrypted_data_dict = conceptual_aes_gcm_decrypt(raw_input_line, DAVBEST_SENSOR_AES_KEY) # Renamed for clarity
    if not decrypted_data_dict:
        # print(f"Debug: Failed to decrypt: {raw_input_line[:100]}")
        return

    log_entry = parse_sensor_log(decrypted_data_dict) # Pass the dict
    if not log_entry:
        # print(f"Debug: Failed to parse: {decrypted_data_dict}") # Print dict if needed
        return

    analyze_log_entry_for_anomalies(log_entry) # This now calls the alert manager

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DavBest Sensor Log Analyzer. Processes encrypted logs from a file.")
    parser.add_argument("logfile", type=str, help="Path to the log file containing hex-encoded encrypted sensor logs.")

    args = parser.parse_args()

    processed_lines = 0
    try:
        # print(f"Python sys.path: {sys.path}") # For debugging import issues
        # print(f"Current working directory: {os.getcwd()}")
        with open(args.logfile, "r") as f:
            for line_num, line in enumerate(f, 1):
                stripped_line = line.strip()
                if stripped_line:
                    process_raw_sensor_input_line(stripped_line)
                    processed_lines +=1
        if processed_lines == 0:
            # This might be normal if the log file is empty or only has non-log lines
            # print(f"Warning: No non-empty lines found or processed in {args.logfile}.")
            pass
    except FileNotFoundError:
        # Standard error output is better for scripting
        # import sys # Already imported
        sys.stderr.write(f"Error: Log file not found: {args.logfile}\n")
        exit(1)
    except Exception as e:
        # import sys # Already imported
        sys.stderr.write(f"Error processing log file {args.logfile}: {e}\n")
        exit(1)
