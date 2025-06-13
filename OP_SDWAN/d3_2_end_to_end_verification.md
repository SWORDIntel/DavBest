# End-to-End Verification Protocol for Remote Event Logging

This document outlines a comprehensive test scenario to verify the entire chain: from the activation of a crafted `.url` file on a client, through the generation and transmission of an encrypted event signal, to the successful receipt and decryption of the log entry on the Remote Event Log Receiver. This protocol assumes the components designed in D.1.3 (remote fetch) and D.3.1 (signal integration) are implemented.

## Test Objectives:

1.  Verify that activating a specially crafted `.url` file can trigger a client-side script.
2.  Verify that the client-side script generates the `SIM_ACTIVE_TIMESTAMP` signal, encrypts it using the shared AES-256-GCM key, and sends it to the Remote Event Log Receiver.
3.  Verify that the Remote Event Log Receiver correctly receives, logs (in encrypted form), and allows decryption of the signal.
4.  Verify that the remote fetch capability of the `.url` file (e.g., `IconFile=`) also attempts a network connection (observable separately).

## Prerequisites:

1.  **Remote Event Log Receiver:** Operational and configured with a known AES-256-GCM key and listening on a known IP/port. Its log file is `event_receiver/config_deploy_test.enc_log`.
2.  **Client System:** A system (e.g., Windows VM) capable of:
    *   Handling `.url` files.
    *   Executing the client-side signalling script (designed in D.3.1). This script must be configured with the correct receiver IP/port and the shared encryption key.
    *   Network connectivity to the Remote Event Log Receiver.
    *   Network connectivity to the target of the `IconFile=` parameter (if testing that part simultaneously).
3.  **Shared Encryption Key:** The 32-byte AES key must be securely distributed to both the client-side script and the event receiver.
4.  **Test Files & Scripts:**
    *   The client-side signalling script (e.g., `signal_sender.py` from D.3.1).
    *   A batch file or mechanism to invoke the signalling script (e.g., `trigger_signal.bat`).
    *   A dummy remote resource for `IconFile=` if this is being tested (e.g., a share serving `test_icon.ico`).

## Test Steps:

**Phase 1: Setup**

1.  **Configure Receiver:**
    *   Ensure the Remote Event Log Receiver is running using the designated shared `ENCRYPTION_KEY`.
    *   Note the path to its encrypted log file (e.g., `event_receiver/config_deploy_test.enc_log`). Clear or backup existing logs for a clean test.
    *   Example command to start receiver (adjust as per actual implementation):
        ```bash
        # Ensure encryption_utils.py and event_receiver_core.py are in the 'event_receiver' directory
        # The key should be the hex representation of the 32-byte shared key
        python -m event_receiver.event_receiver_core --port 12345 --log-file event_receiver/config_deploy_test.enc_log --encryption-key YOUR_HEX_ENCODED_SHARED_KEY
        ```

2.  **Configure Client:**
    *   Deploy the client-side signalling script (e.g., `signal_sender.py`) and its trigger mechanism (e.g., `trigger_signal.bat`) to the client system.
    *   Update `signal_sender.py` with the correct `RECEIVER_IP`, `RECEIVER_PORT`, and `ENCRYPTION_KEY`.
    *   `trigger_signal.bat` (example):
        ```batch
        @echo off
        python C:\path\to\signal_sender.py
        ```

3.  **Create Test `.url` File:**
    *   Create a file named `test_signal.url` on the client system with the following content (adjust paths as needed):
        ```ini
        [InternetShortcut]
        URL=file:///C:/path/to/trigger_signal.bat
        IconFile=\\\\REMOTE_SERVER\\share\\test_icon.ico  ; Optional: For testing remote icon fetch
        IconIndex=0
        ```
        *   Replace `C:/path/to/trigger_signal.bat` with the actual path to the batch file on the client.
        *   Replace `\\\\REMOTE_SERVER\\share\\test_icon.ico` with a valid UNC path to a dummy icon file on a test server if testing `IconFile` interaction. If not testing this, `IconFile` can be omitted or pointed to a local non-critical resource.

**Phase 2: Execution and Observation**

4.  **Monitor Network (Optional but Recommended):**
    *   On the client system or network gateway, start a network monitor (e.g., Wireshark, tcpdump) filtering for traffic to the `REMOTE_SERVER` (for `IconFile`) and the `RECEIVER_IP` on the `RECEIVER_PORT`.

5.  **Activate `.url` File:**
    *   On the client system, double-click or otherwise activate `test_signal.url`.
    *   Observe:
        *   The `trigger_signal.bat` script should execute.
        *   The `signal_sender.py` script should run, printing its log messages (e.g., "Generated signal...", "Encrypted signal sent...").

6.  **Observe Receiver:**
    *   Check the console output of the Remote Event Log Receiver for connection messages and log processing messages.
    *   Monitor the specified encrypted log file (`event_receiver/config_deploy_test.enc_log`) for new entries. The file size should increase.

7.  **Verify Network Traffic (if monitored):**
    *   Check network logs for:
        *   An attempted SMB connection from the client to `REMOTE_SERVER` (if `IconFile` was used and points to a remote resource).
        *   A TCP connection from the client to the `RECEIVER_IP:RECEIVER_PORT`, containing the encrypted payload.

**Phase 3: Verification and Decryption**

8.  **Retrieve Encrypted Log Entry:**
    *   Copy the newly added lines from `event_receiver/config_deploy_test.enc_log`. Each line is a JSON object.
    *   Extract the `encrypted_payload` (hex string) and `raw_data` (original plaintext signal) from the relevant JSON log entry.

9.  **Decrypt Log Entry:**
    *   Use a script based on `encryption_utils.py`'s `decrypt_log_entry` function and the *same shared `ENCRYPTION_KEY`* to decrypt the extracted `encrypted_payload`.
    *   **Conceptual Decryption Script (Python):**
        ```python
        from event_receiver.encryption_utils import decrypt_log_entry # Ensure this path is correct

        # Key must be the same bytes object used by receiver and client script
        SHARED_KEY_BYTES = bytes.fromhex("YOUR_HEX_ENCODED_SHARED_KEY")
        ENCRYPTED_PAYLOAD_HEX = "the_hex_string_from_log_file" # From encrypted_payload field

        try:
            encrypted_payload_bytes = bytes.fromhex(ENCRYPTED_PAYLOAD_HEX)
            decrypted_signal = decrypt_log_entry(encrypted_payload_bytes, SHARED_KEY_BYTES)
            print(f"Decrypted Signal: {decrypted_signal}")
            # Further verification against the 'raw_data' field can be done here
        except Exception as e:
            print(f"Decryption failed: {e}")
        ```

## Success Criteria:

1.  **Client-Side Execution:** The `.url` file activation successfully executes the `trigger_signal.bat` and subsequently the `signal_sender.py` script without errors.
2.  **Signal Transmission:** Network monitoring (if active) confirms TCP traffic to the receiver containing an encrypted payload shortly after client script execution.
3.  **Receiver Log Entry:** The Remote Event Log Receiver logs a new entry in `event_receiver/config_deploy_test.enc_log` corresponding to the client's signal. The JSON entry includes `source_ip`, `reception_timestamp`, `raw_data`, and `encrypted_payload`.
4.  **Successful Decryption:** The `encrypted_payload` from the log can be successfully decrypted using the shared key, and the decrypted content matches the `raw_data` field in the log (which should be `SIM_ACTIVE_TIMESTAMP:<timestamp_value>\n`).
5.  **(Optional) `IconFile` Interaction:** Network monitoring confirms an attempted connection to the `IconFile` resource if this was part of the test.

## Failure Conditions:

*   Client script fails to execute.
*   No network traffic to the receiver is observed.
*   No new log entry appears in the receiver's log file.
*   The log entry is present but cannot be decrypted, or the decrypted content does not match the expected signal format or the `raw_data` field (indicating key mismatch or data corruption).
