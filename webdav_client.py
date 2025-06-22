import os
import logging
import requests
from requests.auth import HTTPBasicAuth # For basic authentication

logger = logging.getLogger(__name__)
# Basic config for logger if no handlers are already configured (e.g. by main app)
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] %(name)s: %(message)s')

class WebDAVClient:
    """Client for interacting with WebDAV servers."""

    def __init__(self, base_url, username=None, password=None, timeout=30, verify_ssl=True):
        """
        Initialize the WebDAV client.

        Args:
            base_url (str): The base URL of the WebDAV server.
            username (str, optional): Username for basic authentication.
            password (str, optional): Password for basic authentication.
            timeout (int, optional): Request timeout in seconds. Defaults to 30.
            verify_ssl (bool, optional): Whether to verify SSL certificates. Defaults to True.
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

        self.session = requests.Session()
        if username and password:
            self.session.auth = HTTPBasicAuth(username, password)

        self.session.verify = verify_ssl # SSL verification

        self.session.headers.update({
            'User-Agent': 'EnhancedWebDAVSecurityTester/1.0.0', # Updated User-Agent
        })

        logger.info(f"WebDAVClient initialized for target: {self.base_url}")
        if username:
            logger.info("Using Basic Authentication.")
        if not verify_ssl:
            logger.warning("SSL certificate verification is disabled.")
            # Suppress InsecureRequestWarning if not verifying SSL
            requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)


    def _construct_url(self, remote_path):
        """Helper to construct the full URL from a remote path."""
        # Ensure remote_path doesn't accidentally make the path absolute if base_url is just a host
        # Example: base_url = "http://host.com", remote_path = "/folder/file" -> "http://host.com/folder/file"
        # Example: base_url = "http://host.com/davbase", remote_path = "folder/file" -> "http://host.com/davbase/folder/file"
        # Example: base_url = "http://host.com/davbase", remote_path = "/folder/file" -> "http://host.com/davbase/folder/file" (lstrip handles this)
        return f"{self.base_url}/{remote_path.lstrip('/')}"

    def put_file(self, local_path, remote_path):
        """
        Upload a file to the WebDAV server.

        Args:
            local_path (str): The local path to the file to be uploaded.
            remote_path (str): The remote path (relative to base_url) where the file will be stored.

        Returns:
            bool: True if upload was successful (2xx status), False otherwise.
        """
        url = self._construct_url(remote_path)
        logger.info(f"Attempting to PUT file '{local_path}' to '{url}'")

        if not os.path.exists(local_path):
            logger.error(f"Local file not found: {local_path}")
            return False
        if not os.path.isfile(local_path):
            logger.error(f"Local path is not a file: {local_path}")
            return False

        content_type = 'application/octet-stream' # Default content type
        _, extension = os.path.splitext(local_path)
        extension = extension.lower()

        if extension == '.svg':
            content_type = 'image/svg+xml'
        elif extension == '.css':
            content_type = 'text/css'
        elif extension == '.xml':
            content_type = 'application/xml'
        elif extension == '.txt':
            content_type = 'text/plain'
        elif extension == '.html' or extension == '.htm':
            content_type = 'text/html'
        elif extension == '.js':
            content_type = 'application/javascript'
        elif extension == '.json':
            content_type = 'application/json'
        # Add more common types as needed

        headers = {'Content-Type': content_type}
        logger.debug(f"Setting Content-Type: {content_type}")

        try:
            with open(local_path, 'rb') as f:
                file_content = f.read()

            response = self.session.put(url, data=file_content, headers=headers, timeout=self.timeout)

            # Successful PUT typically returns 201 (Created) or 204 (No Content if overwriting without content change)
            # Also accept 200 (OK) as some servers might return it.
            if response.status_code in [200, 201, 204]:
                logger.info(f"PUT successful to '{url}'. Status: {response.status_code}")
                return True
            else:
                logger.error(f"PUT failed to '{url}'. Status: {response.status_code} - Response: {response.text[:200]}")
                response.raise_for_status() # Will raise for non-2xx if not caught above
                return False # Should not be reached if raise_for_status is effective for all non-2xx
        except requests.exceptions.HTTPError as e:
            # Already logged by the check above if status code was not 200,201,204
            # but this catches other HTTP errors if raise_for_status() is hit from other paths.
            if e.response is not None: # check if e.response exists
                 logger.error(f"HTTP error during PUT to '{url}': {e.response.status_code} - {e.response.text[:200]}")
            else:
                 logger.error(f"HTTP error during PUT to '{url}': {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during PUT to '{url}': {e}")
        except IOError as e:
            logger.error(f"IOError reading local file '{local_path}': {e}")
        except Exception as e: # Catch-all for unexpected errors
            logger.error(f"Unexpected error during PUT to '{url}': {e}", exc_info=True)

        return False

    def get_file(self, remote_path, local_save_path=None):
        """
        Download a file from the WebDAV server.

        Args:
            remote_path (str): The remote path of the file to download.
            local_save_path (str, optional): If provided, save the file to this local path.

        Returns:
            bytes: The content of the file if download is successful (HTTP 200), None otherwise.
        """
        url = self._construct_url(remote_path)
        logger.info(f"Attempting to GET file from '{url}'")

        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status() # Raises for 4xx/5xx responses

            logger.info(f"GET successful from '{url}'. Status: {response.status_code}, Content-Length: {len(response.content)}")

            if local_save_path:
                try:
                    # Ensure directory for local_save_path exists
                    save_dir = os.path.dirname(local_save_path)
                    if save_dir and not os.path.exists(save_dir): # Check if save_dir is not empty string
                        os.makedirs(save_dir, exist_ok=True)
                        logger.debug(f"Created directory for saving: {save_dir}")

                    with open(local_save_path, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"File content saved to '{local_save_path}'")
                except IOError as e:
                    logger.error(f"IOError saving downloaded file to '{local_save_path}': {e}")
                    # Optionally, still return content even if save fails

            return response.content
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error during GET from '{url}': {e.response.status_code} - {e.response.text[:200]}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during GET from '{url}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error during GET from '{url}': {e}", exc_info=True)

        return None

    def delete_file(self, remote_path):
        """
        Delete a file or collection from the WebDAV server.

        Args:
            remote_path (str): The remote path of the file/collection to delete.

        Returns:
            bool: True if deletion was successful (e.g. 204 No Content, 200 OK, or 202 Accepted). False otherwise.
        """
        url = self._construct_url(remote_path)
        logger.info(f"Attempting to DELETE resource at '{url}'")

        try:
            response = self.session.delete(url, timeout=self.timeout)

            # Successful DELETE typically returns 204 (No Content) or 200 (OK) if response body.
            # 202 (Accepted) if async.
            if response.status_code in [200, 202, 204]:
                logger.info(f"DELETE successful for '{url}'. Status: {response.status_code}")
                return True
            else:
                logger.error(f"DELETE failed for '{url}'. Status: {response.status_code} - Response: {response.text[:200]}")
                response.raise_for_status()
                return False
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                 logger.error(f"HTTP error during DELETE for '{url}': {e.response.status_code} - {e.response.text[:200]}")
            else:
                 logger.error(f"HTTP error during DELETE for '{url}': {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during DELETE for '{url}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error during DELETE for '{url}': {e}", exc_info=True)

        return False

    def list_directory(self, remote_path='/', depth='1'):
        """
        List contents of a directory using PROPFIND.

        Args:
            remote_path (str, optional): The remote directory path. Defaults to '/'.
            depth (str, optional): The Depth header value ('0', '1', or 'infinity'). Defaults to '1'.

        Returns:
            str: The XML response content as a string if successful (HTTP 207), None otherwise.
        """
        url = self._construct_url(remote_path)
        logger.info(f"Attempting PROPFIND for directory '{url}' with Depth: {depth}")

        headers = {
            'Depth': depth,
            'Content-Type': 'application/xml; charset="utf-8"'
        }

        propfind_body = """<?xml version="1.0" encoding="utf-8" ?>
<D:propfind xmlns:D="DAV:">
  <D:prop>
     <D:displayname/>
     <D:resourcetype/>
     <D:getcontentlength/>
     <D:getlastmodified/>
  </D:prop>
</D:propfind>""" # Request specific common properties instead of allprop for efficiency

        try:
            response = self.session.request('PROPFIND', url, headers=headers, data=propfind_body.encode('utf-8'), timeout=self.timeout)

            if response.status_code == 207: # Multi-Status
                logger.info(f"PROPFIND successful for '{url}'. Status: {response.status_code}")
                return response.text
            else:
                logger.error(f"PROPFIND for '{url}' failed. Status: {response.status_code} - Response: {response.text[:200]}")
                response.raise_for_status() # Raise for other non-207 statuses that are errors
                return None # Should not be reached if raise_for_status works
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                logger.error(f"HTTP error during PROPFIND for '{url}': {e.response.status_code} - {e.response.text[:200]}")
            else:
                logger.error(f"HTTP error during PROPFIND for '{url}': {e}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error during PROPFIND for '{url}': {e}")
        except Exception as e:
            logger.error(f"Unexpected error during PROPFIND for '{url}': {e}", exc_info=True)

        return None

if __name__ == '__main__':
    main_logger_wc = logging.getLogger(__name__)
    if not main_logger_wc.handlers or main_logger_wc.level > logging.DEBUG:
        if not main_logger_wc.handlers:
            logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - [%(levelname)s] %(name)s: %(message)s')
        else:
            main_logger_wc.setLevel(logging.DEBUG)

    main_logger_wc.info("WebDAVClient demonstration started.")
    main_logger_wc.warning("This demonstration requires a running WebDAV server for live tests.")
    main_logger_wc.info("Configure TEST_WEBDAV_URL, and optionally _USER, _PASS, _NO_SSL environment variables to test.")

    TEST_WEBDAV_URL = os.environ.get("TEST_WEBDAV_URL")
    TEST_WEBDAV_USER = os.environ.get("TEST_WEBDAV_USER")
    TEST_WEBDAV_PASS = os.environ.get("TEST_WEBDAV_PASS")
    TEST_WEBDAV_NO_SSL_VERIFY = os.environ.get("TEST_WEBDAV_NO_SSL_VERIFY", "false").lower() == "true"


    if not TEST_WEBDAV_URL:
        main_logger_wc.warning("TEST_WEBDAV_URL environment variable not set. Skipping live tests.")
        main_logger_wc.info("WebDAVClient demonstration finished without live tests.")
        exit()

    main_logger_wc.info(f"Using WebDAV URL: {TEST_WEBDAV_URL}")
    client = WebDAVClient(TEST_WEBDAV_URL, TEST_WEBDAV_USER, TEST_WEBDAV_PASS, verify_ssl=not TEST_WEBDAV_NO_SSL_VERIFY)

    test_dir_local = "webdav_client_test_files_local" # Local temporary files
    os.makedirs(test_dir_local, exist_ok=True)

    test_txt_content = f"Hello WebDAV - Text File Test! Timestamp: {time.time()}"
    test_txt_local_path = os.path.join(test_dir_local, "test_upload.txt")
    with open(test_txt_local_path, "w", encoding='utf-8') as f:
        f.write(test_txt_content)

    test_svg_content = f'<svg xmlns="http://www.w3.org/2000/svg"><circle cx="50" cy="50" r="40" fill="orange" /><text x="10" y="50">{time.time()}</text></svg>'
    test_svg_local_path = os.path.join(test_dir_local, "test_upload.svg")
    with open(test_svg_local_path, "w", encoding='utf-8') as f:
        f.write(test_svg_content)

    # Define remote paths for testing - ensure they are unique for each run if possible or clean up
    ts_guid = str(java.util.UUID.randomUUID()).split('-')[0] # Quick unique string
    remote_base_dir = f"dav_client_tests_{ts_guid}"
    remote_txt_path = f"{remote_base_dir}/test_file_uploaded.txt"
    remote_svg_path = f"{remote_base_dir}/test_file_uploaded.svg"

    # For collection operations, we might need to create the collection first if server doesn't auto-create parents
    # This is an advanced WebDAV feature (MKCOL) not implemented in this basic client yet.
    # For now, assume the server might create parent directories on PUT, or test against existing writable dirs.
    # For simplicity, the test will try to PUT directly. Some servers might require remote_base_dir to exist.

    try:
        main_logger_wc.info(f"Remote test directory will be: {remote_base_dir}")
        # Test PUT
        main_logger_wc.info(f"\n--- Testing PUT {test_txt_local_path} to {remote_txt_path} ---")
        put_txt_success = client.put_file(test_txt_local_path, remote_txt_path)
        if put_txt_success: main_logger_wc.info(f"PUT {remote_txt_path} reported success.")
        else: main_logger_wc.error(f"PUT {remote_txt_path} reported failure.")

        main_logger_wc.info(f"\n--- Testing PUT {test_svg_local_path} to {remote_svg_path} ---")
        put_svg_success = client.put_file(test_svg_local_path, remote_svg_path)
        if put_svg_success: main_logger_wc.info(f"PUT {remote_svg_path} reported success.")
        else: main_logger_wc.error(f"PUT {remote_svg_path} reported failure.")

        # Test GET (only if PUT was successful)
        if put_txt_success:
            main_logger_wc.info(f"\n--- Testing GET {remote_txt_path} ---")
            downloaded_txt_path = os.path.join(test_dir_local, "downloaded_file.txt")
            content_txt_bytes = client.get_file(remote_txt_path, local_save_path=downloaded_txt_path)
            if content_txt_bytes:
                match = content_txt_bytes.decode('utf-8') == test_txt_content
                main_logger_wc.info(f"GET {remote_txt_path} successful. Content matches original: {match}")
                if not match: main_logger_wc.warning(f"Content mismatch! Expected: '{test_txt_content}', Got: '{content_txt_bytes.decode('utf-8')}'")
            else: main_logger_wc.error(f"GET {remote_txt_path} failed.")

        if put_svg_success:
            main_logger_wc.info(f"\n--- Testing GET {remote_svg_path} ---")
            downloaded_svg_path = os.path.join(test_dir_local, "downloaded_file.svg")
            content_svg_bytes = client.get_file(remote_svg_path, local_save_path=downloaded_svg_path)
            if content_svg_bytes:
                 match = content_svg_bytes.decode('utf-8') == test_svg_content
                 main_logger_wc.info(f"GET {remote_svg_path} successful. Content matches original: {match}")
                 if not match: main_logger_wc.warning(f"Content mismatch! Expected: '{test_svg_content}', Got: '{content_svg_bytes.decode('utf-8')}'")
            else: main_logger_wc.error(f"GET {remote_svg_path} failed.")

        # Test LIST
        main_logger_wc.info(f"\n--- Testing LIST (PROPFIND) for {remote_base_dir} ---")
        dir_listing_xml = client.list_directory(remote_base_dir)
        if dir_listing_xml:
            main_logger_wc.info(f"LIST for '{remote_base_dir}' successful. XML (first 600 chars):\n{dir_listing_xml[:600]}")
        else:
            main_logger_wc.warning(f"LIST for '{remote_base_dir}' failed or returned no content (may be expected if dir doesn't exist or is empty).")

        main_logger_wc.info(f"\n--- Testing LIST (PROPFIND) for root '/' with Depth 0 ---")
        root_listing_xml = client.list_directory('/', depth='0')
        if root_listing_xml:
            main_logger_wc.info(f"LIST for '/' (Depth 0) successful. XML (first 600 chars):\n{root_listing_xml[:600]}")
        else:
            main_logger_wc.error(f"LIST for '/' (Depth 0) failed.")

    except Exception as e:
        main_logger_wc.error(f"An error occurred during live tests: {e}", exc_info=True)
    finally:
        # Test DELETE (cleanup) - attempt even if prior tests failed
        main_logger_wc.info(f"\n--- Attempting Cleanup ---")
        if put_txt_success: # Only try to delete if we think we created it
            main_logger_wc.info(f"--- Testing DELETE {remote_txt_path} (Cleanup) ---")
            if client.delete_file(remote_txt_path): main_logger_wc.info(f"DELETE {remote_txt_path} reported success.")
            else: main_logger_wc.warning(f"DELETE {remote_txt_path} reported failure.")

        if put_svg_success: # Only try to delete if we think we created it
            main_logger_wc.info(f"\n--- Testing DELETE {remote_svg_path} (Cleanup) ---")
            if client.delete_file(remote_svg_path): main_logger_wc.info(f"DELETE {remote_svg_path} reported success.")
            else: main_logger_wc.warning(f"DELETE {remote_svg_path} reported failure.")

        # Attempt to delete the collection (directory) itself.
        # This often requires the collection to be empty on some servers.
        # Some servers might not support DELETE on collections or require specific headers.
        main_logger_wc.info(f"\n--- Testing DELETE for collection {remote_base_dir} (Cleanup) ---")
        if client.delete_file(remote_base_dir):
            main_logger_wc.info(f"DELETE for collection {remote_base_dir} reported success.")
        else:
            main_logger_wc.warning(f"DELETE for collection {remote_base_dir} reported failure (this might be expected if not empty or not supported).")


        if os.path.exists(test_dir_local):
            main_logger_wc.info(f"Cleaning up local test files directory: {test_dir_local}")
            import shutil
            shutil.rmtree(test_dir_local)
            main_logger_wc.info("Local test files directory removed.")

    main_logger_wc.info("WebDAVClient demonstration finished.")
