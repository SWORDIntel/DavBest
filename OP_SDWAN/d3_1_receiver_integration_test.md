# Remote Event Log Receiver Integration Test Design: Event Signal

This document details the design for how the external resource inclusion protocol (specifically, `.url` file handling from Task D.1.3) would trigger an event success signal compatible with the existing Remote Event Log Receiver. The design is based on `event_receiver/event_receiver_core.py` and `event_receiver/encryption_utils.py`.

## 1. Client-Side Event Success Signal Payload

The client-side component, triggered by the `.url` file activation, must generate a signal in the following format:

```
SIM_ACTIVE_TIMESTAMP:<timestamp_value>\n
```

-   `<timestamp_value>`: An ISO 8601 timestamp or similar precise timestamp string indicating when the event (e.g., `.url` activation and potential resource fetch) was deemed successful on the client side.
-   `\n`: A literal newline character is crucial, as the `event_receiver_core.py` uses `reader.readuntil(b'\n')`.

## 2. Encryption Process

The generated plaintext signal string must be encrypted using AES-256-GCM, matching the `encrypt_log_entry` function in `encryption_utils.py`.

-   **Encryption Key:** A 256-bit (32-byte) AES key. For testing, this key must be identical to the key used by the Remote Event Log Receiver instance.
-   **Nonce:** A 12-byte (96-bit) nonce, which should be unique for each encryption. `os.urandom(12)` is suitable.
-   **Process:**
    1.  Encode the plaintext signal string to UTF-8 bytes.
    2.  Initialize AESGCM with the 256-bit key.
    3.  Encrypt the UTF-8 bytes using the nonce. AESGCM will append the 16-byte authentication tag to the ciphertext.
    4.  Prepend the 12-byte nonce to the ciphertext+tag. The final encrypted payload is `nonce (12 bytes) || ciphertext || tag (16 bytes)`.

## 3. Conceptual Client-Side Code (Signal Generation and Sending)

The following outlines a conceptual snippet (e.g., Python) that would be part of a client-side handler or script executed as a result of the `.url` file's activation. This script's responsibility is to generate the timestamp, format the signal, encrypt it, and send it over TCP to the Remote Event Log Receiver.

**Assumptions:**
*   The client environment can execute a script (e.g., Python, C#, PowerShell).
*   The script has access to the shared AES-256-GCM encryption key.
*   The Remote Event Log Receiver's IP address and port are known.

**Conceptual Python Snippet:**

```python
import socket
import datetime
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM # Requires 'cryptography' package

# --- Configuration (should be securely managed) ---
RECEIVER_IP = "RECEIVER_IP_ADDRESS"  # Placeholder
RECEIVER_PORT = 12345                # Placeholder, use receiver's listening port
ENCRYPTION_KEY = b'\x00'*32           # Placeholder - MUST MATCH RECEIVER'S KEY (32 bytes)
# --- End Configuration ---

def generate_timestamp_signal():
    timestamp = datetime.datetime.now().isoformat()
    return f"SIM_ACTIVE_TIMESTAMP:{timestamp}\n"

def encrypt_signal(plaintext_signal_str, key):
    if not isinstance(key, bytes) or len(key) != 32:
        raise ValueError("Encryption key must be 32 bytes.")
    if not isinstance(plaintext_signal_str, str):
        raise TypeError("Plaintext signal must be a string.")

    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    plaintext_bytes = plaintext_signal_str.encode('utf-8')
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext_bytes, None)
    return nonce + ciphertext_with_tag

def send_encrypted_signal(encrypted_payload_bytes):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((RECEIVER_IP, RECEIVER_PORT))
            s.sendall(encrypted_payload_bytes)
            print("Encrypted signal sent successfully.")
    except Exception as e:
        print(f"Error sending signal: {e}")
        # Handle error appropriately (e.g., log locally)

# --- Main execution flow (conceptual) ---
if __name__ == "__main__":
    # This part would be triggered by the .url file's handler mechanism
    # For example, if the .url file points to a script or a custom protocol handler
    # that executes this logic.

    # 1. Generate the signal
    signal_to_send = generate_timestamp_signal()
    print(f"Generated signal: {signal_to_send.strip()}")

    # 2. Encrypt the signal
    try:
        encrypted_signal = encrypt_signal(signal_to_send, ENCRYPTION_KEY)
        print(f"Encrypted signal (hex): {encrypted_signal.hex()}")

        # 3. Send the encrypted signal
        send_encrypted_signal(encrypted_signal)
    except Exception as e:
        print(f"Failed to encrypt or send signal: {e}")

```

**Integration with `.url` file:**
The `.url` file (as per Task D.1.3, potentially using `URL=file://` or a custom protocol) would need to invoke a mechanism that executes this client-side script.
*   **Example using `file://`:** `URL=file:///path/to/trigger_script.bat` where `trigger_script.bat` then calls the Python script.
*   **Example using custom protocol:** `URL=customprotocol:dosignal`. This requires a custom protocol handler to be registered on the client system, which then executes the necessary logic.

This design ensures that the signal sent from the client is in the format and encryption scheme expected by the `event_receiver_core.py`.
