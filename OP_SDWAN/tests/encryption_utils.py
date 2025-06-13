import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.exceptions import InvalidTag

# Placeholder for secure key management:
# In a real application, this key should be fetched from a secure key vault or configuration.
# For this example, we generate a key when the module is loaded.
# WARNING: This means the key changes every time the application restarts if not stored persistently.
ENCRYPTION_KEY = os.urandom(32)  # 256-bit key for AES

def encrypt_log_entry(plaintext_log: str, key: bytes) -> bytes:
    """
    Encrypts a plaintext log string using AES-256-GCM.

    Args:
        plaintext_log: The string to encrypt.
        key: The 256-bit (32 bytes) encryption key.

    Returns:
        Bytes in the format: nonce (12 bytes) || ciphertext || tag.
        The tag is appended to the ciphertext by AESGCM.encrypt itself.
    """
    if not isinstance(key, bytes) or len(key) != 32:
        raise ValueError("Encryption key must be 32 bytes.")
    if not isinstance(plaintext_log, str):
        raise TypeError("Plaintext log must be a string.")

    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce, recommended for GCM

    plaintext_bytes = plaintext_log.encode('utf-8')

    # encrypt() returns ciphertext which includes the authentication tag
    ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext_bytes, None) # No AAD

    return nonce + ciphertext_with_tag

def decrypt_log_entry(encrypted_log_with_nonce: bytes, key: bytes) -> str:
    """
    Decrypts an AES-256-GCM encrypted log entry.

    Args:
        encrypted_log_with_nonce: Bytes in the format: nonce || ciphertext || tag.
        key: The 256-bit (32 bytes) decryption key.

    Returns:
        The decrypted plaintext string.

    Raises:
        ValueError: If the key is invalid, data is malformed, or decryption fails (e.g., InvalidTag).
        TypeError: If inputs are not of the correct type.
    """
    if not isinstance(key, bytes) or len(key) != 32:
        raise ValueError("Decryption key must be 32 bytes.")
    if not isinstance(encrypted_log_with_nonce, bytes):
        raise TypeError("Encrypted log must be bytes.")

    # Nonce is 12 bytes, GCM tag is 16 bytes. Ciphertext can be empty.
    # So, minimum length is 12 (nonce) + 16 (tag) = 28 bytes.
    if len(encrypted_log_with_nonce) < 12 + 16:
        raise ValueError("Encrypted data is too short to be valid (must include 12-byte nonce and 16-byte tag).")

    nonce = encrypted_log_with_nonce[:12]
    ciphertext_with_tag = encrypted_log_with_nonce[12:]

    aesgcm = AESGCM(key)

    try:
        decrypted_bytes = aesgcm.decrypt(nonce, ciphertext_with_tag, None) # No AAD
        return decrypted_bytes.decode('utf-8')
    except InvalidTag:
        raise ValueError("Decryption failed: Invalid authentication tag. Data may have been tampered or wrong key used.")
    except Exception as e:
        # Catching other potential errors during decryption though InvalidTag is the most common.
        raise ValueError(f"Decryption failed due to an unexpected error: {e}")


if __name__ == '__main__':
    # Example Usage (for testing purposes)
    print(f"Generated ENCRYPTION_KEY: {ENCRYPTION_KEY.hex()}")

    test_key = ENCRYPTION_KEY
    wrong_key = os.urandom(32)
    test_plaintext = "This is a secret log message."
    print(f"Plaintext: {test_plaintext}")

    try:
        encrypted_data = encrypt_log_entry(test_plaintext, test_key)
        print(f"Encrypted (hex): {encrypted_data.hex()}")
        print(f"Nonce (first 12 bytes, hex): {encrypted_data[:12].hex()}")
        print(f"Ciphertext + Tag (rest, hex): {encrypted_data[12:].hex()}")
        print(f"Total length: {len(encrypted_data)} bytes")

        decrypted_text = decrypt_log_entry(encrypted_data, test_key)
        print(f"Decrypted: {decrypted_text}")
        assert decrypted_text == test_plaintext
        print("Encryption and decryption with correct key successful.")

        # Test decryption with wrong key
        print("\nAttempting decryption with WRONG key:")
        try:
            decrypt_log_entry(encrypted_data, wrong_key)
        except ValueError as e:
            print(f"Caught expected error for wrong key: {e}")
            assert "Invalid authentication tag" in str(e)

        # Test decryption with tampered data (e.g., flip a bit in ciphertext)
        print("\nAttempting decryption with TAMPERED data:")
        tampered_data_list = list(encrypted_data)
        if len(tampered_data_list) > 12: # Ensure there's ciphertext to tamper
            tampered_data_list[-1] = tampered_data_list[-1] ^ 0x01 # Flip last bit of ciphertext_with_tag
        tampered_data = bytes(tampered_data_list)
        try:
            decrypt_log_entry(tampered_data, test_key)
        except ValueError as e:
            print(f"Caught expected error for tampered data: {e}")
            assert "Invalid authentication tag" in str(e)

        # Test with too short data
        print("\nAttempting decryption with TOO SHORT data:")
        try:
            decrypt_log_entry(b"short", test_key)
        except ValueError as e:
            print(f"Caught expected error for too short data: {e}")
            assert "too short" in str(e)


    except Exception as e:
        print(f"An unexpected error occurred during testing: {e}")
        raise

    # Test encrypt with incorrect key length
    print("\nTesting encrypt error handling:")
    try:
        encrypt_log_entry("test", os.urandom(16))
    except ValueError as e:
        print(f"Caught expected error for wrong key size (encrypt): {e}")

    # Test encrypt with non-string input
    try:
        encrypt_log_entry(12345, test_key) # type: ignore
    except TypeError as e:
        print(f"Caught expected error for wrong input type (encrypt): {e}")

    # Test decrypt with incorrect key length
    print("\nTesting decrypt error handling:")
    try:
        decrypt_log_entry(encrypted_data, os.urandom(16))
    except ValueError as e:
        print(f"Caught expected error for wrong key size (decrypt): {e}")

    # Test decrypt with non-bytes input
    try:
        decrypt_log_entry("not bytes", test_key) # type: ignore
    except TypeError as e:
        print(f"Caught expected error for wrong input type (decrypt): {e}")
