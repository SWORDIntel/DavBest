import argparse
import subprocess
import os
import time
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Any, List, Dict

# Attempt to import encryption utilities from the current directory
try:
    from encryption_utils import decrypt_log_entry
except ImportError:
    print("Error: encryption_utils.py not found in current directory. Please ensure it's present.")
    def decrypt_log_entry(enc_bytes: bytes, key: bytes) -> str: # Dummy
        raise ImportError("decrypt_log_entry not available")

# Define tool paths (assuming they are in ../tools/ relative to this test script)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(BASE_DIR, "..", "tools")
URL_GENERATOR_SCRIPT = os.path.join(TOOLS_DIR, "url_file_generator.py")
EVENT_CLIENT_SCRIPT = os.path.join(TOOLS_DIR, "event_signal_client.py")

TEMP_URL_FILENAME = "temp_test_signal.url"

def run_script(script_path: str, args: List[str]) -> bool:
    """Runs a Python script as a subprocess and checks for success."""
    try:
        print(f"Running: python {script_path} {' '.join(args)}")
        process = subprocess.run(['python', script_path] + args, capture_output=True, text=True, check=True, timeout=30)
        print(f"Output from {os.path.basename(script_path)}:\n{process.stdout}")
        if process.stderr:
            print(f"Stderr from {os.path.basename(script_path)}:\n{process.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_path}: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
    except subprocess.TimeoutExpired:
        print(f"Timeout running {script_path}.")
    except Exception as e:
        print(f"Unexpected error running {script_path}: {e}")
    return False

def verify_receiver_log(log_path: str, key_bytes: bytes,
                        start_time: datetime, end_time: datetime) -> Optional[Dict[str, Any]]:
    """
    Reads the receiver's log, decrypts entries, and looks for a specific signal.
    Returns the parsed log entry if found and verified, otherwise None.
    """
    print(f"Verifying receiver log: {log_path}")
    if not os.path.exists(log_path):
        print(f"Receiver log file {log_path} not found.")
        return None

    try:
        with open(log_path, 'rb') as f:
            # Read all lines at once. For very large logs, iterative reading might be better.
            encrypted_lines = f.readlines()

        for line_bytes in reversed(encrypted_lines): # Check newest entries first
            line_bytes = line_bytes.strip()
            if not line_bytes:
                continue

            try:
                decrypted_json_str = decrypt_log_entry(line_bytes, key_bytes)
                log_entry = json.loads(decrypted_json_str)

                if 'raw_data' in log_entry and log_entry['raw_data'].startswith("SIM_ACTIVE_TIMESTAMP:"):
                    if 'reception_timestamp' in log_entry:
                        # Ensure reception_timestamp is offset-aware for comparison
                        reception_dt = datetime.fromisoformat(log_entry['reception_timestamp'])
                        if reception_dt.tzinfo is None: # Should be ISO from receiver
                             # This case should ideally not happen if receiver sets tz
                            reception_dt = reception_dt.replace(tzinfo=timezone.utc)

                        # Check if reception_dt is within the client's signal sending window
                        # Add a small buffer to account for clock differences/latency
                        if (start_time - timedelta(seconds=5)) <= reception_dt <= (end_time + timedelta(seconds=5)):
                            print(f"Found matching log entry: {log_entry}")
                            return log_entry
            except json.JSONDecodeError:
                print(f"Skipping line, JSON decode error: {decrypted_json_str[:100]}...") # Show partial
            except ValueError as e: # Decryption or other errors
                # This is expected for lines encrypted with different keys or if it's not an encrypted line
                # print(f"Skipping line, decryption/value error: {e}")
                pass # Common, so don't be too verbose unless debugging
            except Exception as e:
                print(f"Unexpected error processing log line: {e}")
        print("No matching signal found in the specified timeframe.")
        return None
    except IOError as e:
        print(f"Error reading log file {log_path}: {e}")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NEBULA_AUDIT D.4.1 Integration Test Script.")
    parser.add_argument("receiver_ip", help="Remote Event Log Receiver IP.")
    parser.add_argument("receiver_port", type=int, help="Remote Event Log Receiver port.")
    parser.add_argument("key", help="Hex-encoded AES-256 key for encryption/decryption.")
    parser.add_argument("receiver_log_file", help="Path to the receiver's encrypted log file.")
    parser.add_argument("--url_icon_path", default=None, help="Optional UNC path for IconFile in .url (e.g., \\server\share\icon.ico)")

    args = parser.parse_args()

    try:
        key_bytes_val = bytes.fromhex(args.key)
        if len(key_bytes_val) != 32:
            raise ValueError("Key must be 32 bytes (64 hex chars).")
    except ValueError as e:
        print(f"Invalid key: {e}")
        exit(1)

    temp_url_full_path = os.path.join(BASE_DIR, TEMP_URL_FILENAME)
    test_success = False

    try:
        # Step 1: Generate .url file
        print("\n--- Step 1: Generating .url file ---")
        # The URL target simulates a local action; actual client is run directly.
        url_target_for_file = "file:///C:/Windows/System32/calc.exe" # Dummy target
        url_gen_args = [temp_url_full_path, url_target_for_file]
        if args.url_icon_path:
            # Ensure backslashes are used for UNC paths if that's what url_file_generator expects
            url_gen_args.extend(["--icon-file-path", args.url_icon_path.replace("\\", "\\\\")])

        if not run_script(URL_GENERATOR_SCRIPT, url_gen_args):
            print("Failed to generate .url file. Aborting test.")
            exit(1)
        print(f"Note: .url file generated at {temp_url_full_path}. Its activation is simulated next.")
        print("If --url_icon_path was provided, the Mock Remote Content Server should be running and its logs checked manually for IconFile access attempts.")

        # Step 2: Simulate .url activation (run event_signal_client)
        print("\n--- Step 2: Simulating .url activation (running event signal client) ---")
        # Timestamps must be UTC and offset-aware for proper comparison
        time_before_signal = datetime.now(timezone.utc)
        client_args = [args.receiver_ip, str(args.receiver_port), args.key]
        if not run_script(EVENT_CLIENT_SCRIPT, client_args):
            print("Event signal client script failed. Aborting test.")
            exit(1)
        time.sleep(2) # Give a moment for signal to be processed by receiver
        time_after_signal = datetime.now(timezone.utc)

        # Step 3: Verify Receiver Log
        print("\n--- Step 3: Verifying Receiver Log ---")
        # Wait a bit longer for logs to flush, especially if receiver batches
        print("Waiting a few seconds for log propagation...")
        time.sleep(5)

        verified_entry = verify_receiver_log(args.receiver_log_file, key_bytes_val,
                                             time_before_signal, time_after_signal)

        # Step 4: Report Results
        print("\n--- Step 4: Test Results ---")
        if verified_entry:
            print("SUCCESS: End-to-end test passed!")
            print(f"Verified Signal Content (raw_data): {verified_entry.get('raw_data')}")
            print(f"Receiver Logged Timestamp: {verified_entry.get('reception_timestamp')}")
            print(f"Receiver Logged Source IP: {verified_entry.get('source_ip')}")
            test_success = True
        else:
            print("FAILURE: End-to-end test failed. Signal not found or not verified in receiver log.")
            print(f"Expected signal between: {time_before_signal.isoformat()} and {time_after_signal.isoformat()}")

    finally:
        # Clean up
        if os.path.exists(temp_url_full_path):
            print(f"Cleaning up temporary .url file: {temp_url_full_path}")
            os.remove(temp_url_full_path)

        print("\nIntegration test finished.")
        if not test_success:
            exit(1)
