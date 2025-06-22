import unittest
import uuid as std_uuid # Alias to avoid confusion with our class's uuid import
from dav_best import UuidEncoder # Assuming dav_best.py is in the same directory or PYTHONPATH

class TestUuidEncoder(unittest.TestCase):

    def test_encode_decode_simple_string(self):
        """Test encoding and decoding a simple ASCII string."""
        encoder = UuidEncoder()
        original_content = "Hello, WebDAV!"
        encoded_uuids = encoder.encode_to_uuids(original_content)

        # Basic check: ensure we got a list of strings (UUIDs)
        self.assertIsInstance(encoded_uuids, list)
        if encoded_uuids: # Ensure list is not empty
            self.assertIsInstance(encoded_uuids[0], str)
            try:
                std_uuid.UUID(encoded_uuids[0]) # Check if it's a valid UUID format
            except ValueError:
                self.fail("Encoded string is not a valid UUID format")

        decoded_content_bytes = encoder.decode_from_uuids(encoded_uuids, strip_null_padding=True)
        # The encoder pads with nulls, decoder should handle this.
        # Our PHP/ASP decoders effectively strip trailing nulls from the *final script string*.
        # For direct decode_from_uuids, we need to be careful.
        # If original_content.encode('utf-8') length is not a multiple of 16, it was padded.
        expected_bytes = original_content.encode('utf-8')

        # Smart strip based on how encode_to_uuids pads the last chunk
        num_chunks = (len(expected_bytes) + 15) // 16 # ceiling division
        expected_padded_len = num_chunks * 16
        padding_len = expected_padded_len - len(expected_bytes)

        # Test with strip_null_padding=True (should return original content)
        decoded_content_stripped = encoder.decode_from_uuids(encoded_uuids, strip_null_padding=True)
        self.assertEqual(decoded_content_stripped, expected_bytes)

        # Test with strip_null_padding=False (should return content with padding)
        decoded_content_raw = encoder.decode_from_uuids(encoded_uuids, strip_null_padding=False)
        if padding_len > 0:
            self.assertEqual(decoded_content_raw, expected_bytes + b'\x00' * padding_len)
        else:
            self.assertEqual(decoded_content_raw, expected_bytes)


    def test_encode_decode_utf8_string(self):
        """Test encoding and decoding a UTF-8 string with multi-byte characters."""
        encoder = UuidEncoder()
        original_content = "こんにちは WebDAV" # Hello WebDAV in Japanese
        expected_bytes = original_content.encode('utf-8')

        encoded_uuids = encoder.encode_to_uuids(original_content) # Default chunk_size = 16

        # Test with strip_null_padding=True
        decoded_content_stripped = encoder.decode_from_uuids(encoded_uuids, strip_null_padding=True)
        self.assertEqual(decoded_content_stripped, expected_bytes)

        # Test with strip_null_padding=False
        decoded_content_raw = encoder.decode_from_uuids(encoded_uuids, strip_null_padding=False)
        num_chunks = (len(expected_bytes) + 15) // 16
        expected_padded_len = num_chunks * 16
        padding_len = expected_padded_len - len(expected_bytes)
        if padding_len > 0:
            self.assertEqual(decoded_content_raw, expected_bytes + b'\x00' * padding_len)
        else:
            self.assertEqual(decoded_content_raw, expected_bytes)


    def test_encode_with_chunk_size(self):
        """Test encoding with a specific chunk size."""
        encoder = UuidEncoder()
        original_content = "1234567890abcdef" # 16 bytes (exactly 1 chunk of 16, or 2 chunks of 8)
        expected_bytes = original_content.encode('utf-8')

        # Test with chunk size 8
        encoded_uuids_chunk8 = encoder.encode_to_uuids(original_content, chunk_size=8)
        self.assertEqual(len(encoded_uuids_chunk8), 2)

        # Decode and verify (with stripping padding)
        decoded_bytes_chunk8_stripped = encoder.decode_from_uuids(encoded_uuids_chunk8, strip_null_padding=True)
        self.assertEqual(decoded_bytes_chunk8_stripped, expected_bytes)

        # Test with chunk size 16
        encoded_uuids_chunk16 = encoder.encode_to_uuids(original_content, chunk_size=16)
        self.assertEqual(len(encoded_uuids_chunk16), 1) # 16 bytes / 16 byte chunks = 1 UUID
        decoded_bytes_chunk16 = encoder.decode_from_uuids(encoded_uuids_chunk16, strip_null_padding=False)
        self.assertEqual(decoded_bytes_chunk16, original_content.encode('utf-8'))

    def test_encode_empty_string(self):
        """Test encoding an empty string."""
        encoder = UuidEncoder()
        original_content = ""
        encoded_uuids = encoder.encode_to_uuids(original_content)
        self.assertEqual(len(encoded_uuids), 0) # Should produce no UUIDs

        decoded_content_bytes = encoder.decode_from_uuids(encoded_uuids, strip_null_padding=False)
        self.assertEqual(decoded_content_bytes, b"")

    def test_decode_invalid_uuid(self):
        """Test decoding a list containing an invalid UUID string."""
        encoder = UuidEncoder()
        valid_uuid = str(std_uuid.uuid4())
        invalid_uuid_list = [valid_uuid, "not-a-uuid", valid_uuid]
        with self.assertRaises(ValueError):
            encoder.decode_from_uuids(invalid_uuid_list)

    def test_chunk_size_validation(self):
        """Test that encode_to_uuids validates chunk_size."""
        encoder = UuidEncoder()
        content = "test"
        with self.assertRaises(ValueError):
            encoder.encode_to_uuids(content, chunk_size=0)
        with self.assertRaises(ValueError):
            encoder.encode_to_uuids(content, chunk_size=17)
        # Should not raise for valid sizes
        try:
            encoder.encode_to_uuids(content, chunk_size=1)
            encoder.encode_to_uuids(content, chunk_size=16)
        except ValueError:
            self.fail("encode_to_uuids raised ValueError for valid chunk_size")

    def test_vbscript_decoder_generation(self):
        """Test VBScript decoder generation (basic structure)."""
        encoder = UuidEncoder()
        uuids = [str(std_uuid.uuid4()), str(std_uuid.uuid4())]
        script = encoder.generate_vbscript_decoder(uuids)
        self.assertIn("<%@ Language=\"VBScript\" %>", script)
        self.assertIn("Function UuidToBytes(uuidStr)", script)
        self.assertIn("ExecuteGlobal finalScript", script)
        for u in uuids:
            self.assertIn(f'"{u}"', script)

    def test_php_decoder_generation(self):
        """Test PHP decoder generation (basic structure)."""
        encoder = UuidEncoder()
        uuids = [str(std_uuid.uuid4()), str(std_uuid.uuid4())]
        script = encoder.generate_php_decoder(uuids)
        self.assertIn("<?php", script)
        self.assertIn("function uuidToBytes($uuid)", script)
        self.assertIn("@eval($decodedScript);", script)
        for u in uuids:
            self.assertIn(f'"{u}",', script)

if __name__ == '__main__':
    unittest.main()
