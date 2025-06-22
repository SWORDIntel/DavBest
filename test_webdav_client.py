import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import shutil
import requests # <--- Import requests here

# Assuming webdav_client.py is in the same directory or accessible via PYTHONPATH
from webdav_client import WebDAVClient

class TestWebDAVClient(unittest.TestCase):
    base_url = "http://mockdav.example.com/webdav/"
    test_output_dir = "./test_webdav_client_output" # For downloaded files

    def setUp(self):
        # Create a dummy file for upload tests
        self.local_file_content = "This is a test file for WebDAV client."
        self.local_file_path = "dummy_upload_file.txt"
        with open(self.local_file_path, "w") as f:
            f.write(self.local_file_content)

        # Ensure test output dir for downloads is clean
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)
        os.makedirs(self.test_output_dir, exist_ok=True)


    def tearDown(self):
        # Clean up dummy file and download dir
        if os.path.exists(self.local_file_path):
            os.remove(self.local_file_path)
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    @patch('webdav_client.requests.Session')
    def test_put_file_success(self, MockSession):
        """Test successful file upload (PUT)."""
        mock_session_instance = MockSession.return_value
        mock_response = MagicMock()
        mock_response.status_code = 201 # Created
        mock_response.reason = "Created"
        mock_session_instance.put.return_value = mock_response

        client = WebDAVClient(self.base_url, "user", "pass")
        remote_path = "test_dir/remote_file.txt"
        success = client.put_file(self.local_file_path, remote_path)

        self.assertTrue(success)
        expected_url = self.base_url + "test_dir/remote_file.txt" # base_url ends with /
        mock_session_instance.put.assert_called_once()
        args, kwargs = mock_session_instance.put.call_args
        self.assertEqual(args[0], expected_url) # Check URL
        self.assertEqual(kwargs['data'], self.local_file_content.encode('utf-8')) # Check data
        self.assertIn('Content-Type', kwargs['headers']) # Check Content-Type was attempted

    @patch('webdav_client.requests.Session')
    def test_put_file_failure_status(self, MockSession):
        """Test PUT failure due to server error status."""
        mock_session_instance = MockSession.return_value
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.reason = "Internal Server Error"
        mock_response.text = "Server Error Details"
        # Make raise_for_status raise an HTTPError like requests does
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Error", response=mock_response)
        mock_session_instance.put.return_value = mock_response

        client = WebDAVClient(self.base_url)
        with self.assertLogs(client.logger.name, level='ERROR') as cm: # Check that an error is logged
            success = client.put_file(self.local_file_path, "fail.txt")
        self.assertFalse(success)
        self.assertTrue(any("Upload failed: 500" in log_msg for log_msg in cm.output))


    @patch('webdav_client.requests.Session')
    def test_put_file_request_exception(self, MockSession):
        """Test PUT failure due to requests.exceptions.RequestException."""
        mock_session_instance = MockSession.return_value
        mock_session_instance.put.side_effect = requests.exceptions.Timeout("Connection timed out")

        client = WebDAVClient(self.base_url)
        with self.assertLogs(client.logger.name, level='ERROR') as cm:
            success = client.put_file(self.local_file_path, "timeout.txt")
        self.assertFalse(success)
        self.assertTrue(any("Error during PUT request" in log_msg and "Connection timed out" in log_msg for log_msg in cm.output))

    def test_put_file_local_file_not_found(self):
        """Test PUT failure if local file does not exist."""
        client = WebDAVClient(self.base_url)
        with self.assertLogs(client.logger.name, level='ERROR') as cm:
            success = client.put_file("non_existent_file.txt", "remote.txt")
        self.assertFalse(success)
        self.assertTrue(any("Local file not found" in log_msg for log_msg in cm.output))


    @patch('webdav_client.requests.Session')
    def test_get_file_success(self, MockSession):
        """Test successful file download (GET)."""
        mock_session_instance = MockSession.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.reason = "OK"
        mock_response.content = b"Downloaded file content."
        mock_session_instance.get.return_value = mock_response

        client = WebDAVClient(self.base_url)
        remote_path = "files/retrieved.txt"
        content = client.get_file(remote_path)

        self.assertEqual(content, b"Downloaded file content.")
        expected_url = self.base_url + remote_path
        mock_session_instance.get.assert_called_once_with(expected_url, timeout=client.timeout)

    @patch('webdav_client.requests.Session')
    def test_get_file_and_save_success(self, MockSession):
        """Test successful GET and save to local file."""
        mock_session_instance = MockSession.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"Save this content."
        mock_session_instance.get.return_value = mock_response

        client = WebDAVClient(self.base_url)
        local_save_path = os.path.join(self.test_output_dir, "saved_download.txt")

        # Mock open for saving the file to avoid actual file I/O here,
        # or let it write to test_output_dir which is cleaned up.
        # For this test, let's allow the write as setUp/tearDown handles the dir.
        content = client.get_file("files/to_save.txt", local_save_path=local_save_path)

        self.assertEqual(content, b"Save this content.")
        self.assertTrue(os.path.exists(local_save_path))
        with open(local_save_path, "rb") as f:
            saved_data = f.read()
        self.assertEqual(saved_data, b"Save this content.")


    @patch('webdav_client.requests.Session')
    def test_delete_file_success(self, MockSession):
        """Test successful file deletion (DELETE)."""
        mock_session_instance = MockSession.return_value
        mock_response = MagicMock()
        mock_response.status_code = 204 # No Content
        mock_response.reason = "No Content"
        mock_session_instance.delete.return_value = mock_response

        client = WebDAVClient(self.base_url)
        remote_path = "files_to_delete/item.txt"
        success = client.delete_file(remote_path)

        self.assertTrue(success)
        expected_url = self.base_url + remote_path
        mock_session_instance.delete.assert_called_once_with(expected_url, timeout=client.timeout)

    @patch('webdav_client.requests.Session')
    @patch('webdav_client.ET.fromstring') # Mock ElementTree parsing
    def test_list_directory_success(self, mock_fromstring, MockSession):
        """Test successful directory listing (PROPFIND)."""
        mock_session_instance = MockSession.return_value
        mock_propfind_response = MagicMock()
        mock_propfind_response.status_code = 207 # Multi-Status
        mock_propfind_response.reason = "Multi-Status"
        # Simplified XML content for response
        xml_content = b"""<?xml version="1.0"?>
        <d:multistatus xmlns:d="DAV:">
          <d:response>
            <d:href>/webdav/test_dir/</d:href>
            <d:propstat><d:prop><d:displayname>test_dir</d:displayname></d:prop></d:propstat>
          </d:response>
          <d:response>
            <d:href>/webdav/test_dir/file1.txt</d:href>
            <d:propstat><d:prop><d:displayname>file1.txt</d:displayname></d:prop></d:propstat>
          </d:response>
          <d:response>
            <d:href>/webdav/test_dir/subdir/</d:href>
            <d:propstat><d:prop><d:displayname>subdir</d:displayname></d:prop></d:propstat>
          </d:response>
        </d:multistatus>
        """
        mock_propfind_response.content = xml_content
        mock_session_instance.request.return_value = mock_propfind_response

        # Mock the ET.fromstring parsing part
        mock_xml_root = MagicMock()
        # This needs to simulate the structure ET.fromstring would return for the findall
        # Simulating findall for './/d:response'
        mock_resp_elem1 = MagicMock()
        mock_href1 = MagicMock()
        mock_href1.text = self.base_url + "test_dir/" # URL for the directory itself
        mock_resp_elem1.find.return_value = mock_href1

        mock_resp_elem2 = MagicMock()
        mock_href2 = MagicMock()
        mock_href2.text = self.base_url + "test_dir/file1.txt"
        mock_resp_elem2.find.return_value = mock_href2

        mock_resp_elem3 = MagicMock()
        mock_href3 = MagicMock()
        mock_href3.text = self.base_url + "test_dir/subdir/" # Note the trailing slash
        mock_resp_elem3.find.return_value = mock_href3

        mock_xml_root.findall.return_value = [mock_resp_elem1, mock_resp_elem2, mock_resp_elem3]
        mock_fromstring.return_value = mock_xml_root

        client = WebDAVClient(self.base_url)
        dir_path = "test_dir/" # Test with trailing slash
        resources = client.list_directory(dir_path)

        self.assertIsNotNone(resources)
        # The client's list_directory logic tries to make names relative and unique
        # Given base_url = "http://mockdav.example.com/webdav/"
        # and dir_path = "test_dir/"
        # Hrefs:
        #   http://mockdav.example.com/webdav/test_dir/ -> "" (effectively, after stripping)
        #   http://mockdav.example.com/webdav/test_dir/file1.txt -> "file1.txt"
        #   http://mockdav.example.com/webdav/test_dir/subdir/ -> "subdir/"
        # The current _construct_url and href processing in list_directory might need refinement
        # For now, let's check if expected items are present

        # Expected after client's processing:
        # It strips base_url, then strips the query path, then strips leading slash
        # href1: "http://mockdav.example.com/webdav/test_dir/" -> "" -> "" -> "" (filtered out)
        # href2: "http://mockdav.example.com/webdav/test_dir/file1.txt" -> "file1.txt" -> "file1.txt" -> "file1.txt"
        # href3: "http://mockdav.example.com/webdav/test_dir/subdir/" -> "subdir/" -> "subdir/" -> "subdir/"
        self.assertIn("file1.txt", resources)
        self.assertIn("subdir/", resources)
        self.assertEqual(len(resources), 2) # Should not include the directory itself in this simplified output

        expected_url = self.base_url + dir_path.replace('//','/') # Normalize slashes
        mock_session_instance.request.assert_called_once()
        args, kwargs = mock_session_instance.request.call_args
        self.assertEqual(args[0], 'PROPFIND')
        self.assertEqual(args[1], expected_url)
        self.assertEqual(kwargs['headers']['Depth'], '1')

    def test_construct_url_various_paths(self):
        """Test _construct_url with different path styles."""
        client = WebDAVClient("http://localhost/dav/")
        self.assertEqual(client._construct_url("file.txt"), "http://localhost/dav/file.txt")
        self.assertEqual(client._construct_url("/file.txt"), "http://localhost/dav/file.txt")
        self.assertEqual(client._construct_url("dir/file.txt"), "http://localhost/dav/dir/file.txt")
        self.assertEqual(client._construct_url("/dir/file.txt"), "http://localhost/dav/dir/file.txt")
        self.assertEqual(client._construct_url("a b/c d.txt"), "http://localhost/dav/a%20b/c%20d.txt") # Check quoting

        client_no_slash = WebDAVClient("http://localhost/dav") # Base URL without trailing slash
        self.assertEqual(client_no_slash._construct_url("file.txt"), "http://localhost/dav/file.txt")


if __name__ == '__main__':
    unittest.main()
