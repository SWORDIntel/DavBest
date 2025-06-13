import os

# A dummy key for testing purposes. In a real scenario, this would be securely managed.
ENCRYPTION_KEY = os.urandom(32) # Creates a random 32-byte key

def decrypt_log_entry(encrypted_content: bytes, key: bytes) -> str:
    """
    Placeholder for log decryption logic.
    For now, it will just try to decode assuming it's plain text or simple encoding.
    A real implementation would use cryptography.
    """
    if key != ENCRYPTION_KEY:
        raise ValueError("Decryption failed: Incorrect key")
    try:
        # Try to decode as UTF-8. If it's actual encrypted binary, this will likely fail.
        # For testing, we might place base64 encoded strings or plain JSON strings in .enc_log files.
        import base64
        try:
            # First attempt base64 decoding, then utf-8
            return base64.b64decode(encrypted_content).decode('utf-8')
        except Exception:
            # If not base64, try direct utf-8
            return encrypted_content.decode('utf-8')
    except UnicodeDecodeError as e:
        raise ValueError(f"Decryption failed: Content not valid UTF-8 after dummy decryption. {e}")
    except Exception as e:
        raise ValueError(f"Dummy decryption encountered an error: {e}")

if __name__ == '__main__':
    # Example usage (not part of the module's normal use, but for testing this file)
    print(f"ENCRYPTION_KEY (hex): {ENCRYPTION_KEY.hex()}")
    test_content_plain = '{"message": "hello world"}'
    print(f"Original: {test_content_plain}")

    # For testing, let's assume content is base64 encoded before "encryption"
    import base64
    test_content_encrypted = base64.b64encode(test_content_plain.encode('utf-8'))
    print(f"Encrypted (base64): {test_content_encrypted}")

    try:
        decrypted = decrypt_log_entry(test_content_encrypted, ENCRYPTION_KEY)
        print(f"Decrypted: {decrypted}")
        assert decrypted == test_content_plain
    except ValueError as e:
        print(f"Error: {e}")

    # Test with wrong key
    wrong_key = os.urandom(32)
    try:
        decrypt_log_entry(test_content_encrypted, wrong_key)
    except ValueError as e:
        print(f"Correctly failed with wrong key: {e}")
