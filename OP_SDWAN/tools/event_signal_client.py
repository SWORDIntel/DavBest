import argparse
import socket
import datetime
import os
from typing import Optional

# Attempt to import encryption utilities from the current directory
try:
    from encryption_utils import encrypt_log_entry
except ImportError:
    print("Error: encryption_utils.py not found. Please ensure it's in the same directory.")
    # Define a dummy function if import fails to allow basic script structure.
    # The script will not function correctly without the actual encryption_utils.
    def encrypt_log_entry(log_str: str, key: bytes) -> bytes:
        print("(Warning: Using dummy encryption - encryption_utils.py not found)")
        return log_str.encode('utf-8')


def generate_timestamp_signal() -> str:
    """Generates the standard event signal string with a current ISO timestamp."""
    timestamp = datetime.datetime.now().isoformat()
    return f"SIM_ACTIVE_TIMESTAMP:{timestamp}\n"

def encrypt_signal(plaintext_signal_str: str, key_bytes: bytes) -> bytes:
    """
    Encrypts the plaintext signal string using AES-256-GCM.
    Relies on encrypt_log_entry from encryption_utils.
    """
    if not isinstance(key_bytes, bytes) or len(key_bytes) != 32:
        raise ValueError("Encryption key must be 32 bytes.")
    if not isinstance(plaintext_signal_str, str):
        raise TypeError("Plaintext signal must be a string.")

    # encrypt_log_entry from encryption_utils handles nonce generation and prepending
    return encrypt_log_entry(plaintext_signal_str, key_bytes)

def send_encrypted_signal(receiver_ip: str, receiver_port: int,
                            encrypted_payload_bytes: bytes) -> bool:
    """
    Sends the encrypted payload to the specified receiver.

    Returns:
        True if sending was successful, False otherwise.
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(10) # 10-second timeout for connection and send
            s.connect((receiver_ip, receiver_port))
            s.sendall(encrypted_payload_bytes)
            print(f"Encrypted signal sent successfully to {receiver_ip}:{receiver_port}.")
            return True
    except socket.timeout:
        print(f"Error sending signal: Timeout connecting to or sending data to {receiver_ip}:{receiver_port}.")
    except socket.error as e:
        print(f"Error sending signal: Socket error - {e}")
    except Exception as e:
        print(f"An unexpected error occurred during sending: {e}")
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Event Signal Client Tool for NEBULA_AUDIT.")
    parser.add_argument("receiver_ip", type=str, help="IP address of the Remote Event Log Receiver.")
    parser.add_argument("receiver_port", type=int, help="Port of the Remote Event Log Receiver.")
    parser.add_argument("key", type=str, help="Hex-encoded 256-bit AES encryption key.")

    args = parser.parse_args()

    try:
        encryption_key_bytes = bytes.fromhex(args.key)
        if len(encryption_key_bytes) != 32:
            raise ValueError("Encryption key must be a 64-character hex string (32 bytes).")
    except ValueError as e:
        print(f"Invalid encryption key: {e}")
        exit(1)

    # 1. Generate the signal
    signal_to_send = generate_timestamp_signal()
    print(f"Generated signal: {signal_to_send.strip()}")

    # 2. Encrypt the signal
    try:
        encrypted_signal_payload = encrypt_signal(signal_to_send, encryption_key_bytes)
        # print(f"Encrypted signal (hex): {encrypted_signal_payload.hex()}") # Optional: for debugging
    except (ValueError, TypeError) as e:
        print(f"Failed to encrypt signal: {e}")
        exit(1)
    except Exception as e: # Catch-all for other encryption issues
        print(f"An unexpected error occurred during signal encryption: {e}")
        exit(1)

    # 3. Send the encrypted signal
    if not send_encrypted_signal(args.receiver_ip, args.receiver_port, encrypted_signal_payload):
        print("Failed to send signal.")
        exit(1)

    print("Event signal client finished successfully.")
