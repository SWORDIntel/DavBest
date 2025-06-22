import os
import datetime
import logging
import traceback # For detailed error logging in run_test
import json # For loading batch test configs if needed later by CLI

# Assuming these files are in the same directory or accessible via PYTHONPATH
from payload_generator import PayloadGenerator # Though not directly used, good for type hinting if needed
from svg_payload_generator import SVGPayloadGenerator
from css_payload_generator import CSSPayloadGenerator
from webdav_client import WebDAVClient

# Configure a logger for this module
logger = logging.getLogger(__name__)
if not logger.handlers: # Ensure logger is configured if not already by application
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] %(name)s: %(message)s')

class WebDAVSecurityTester:
    """Main application class for orchestrating WebDAV security tests."""

    def __init__(self, config):
        """
        Initialize the WebDAVSecurityTester.

        Args:
            config (dict): Configuration dictionary containing:
                - 'webdav_url' (str): URL of the WebDAV server.
                - 'username' (str, optional): WebDAV username.
                - 'password' (str, optional): WebDAV password.
                - 'output_dir' (str, optional): Directory for generated payloads. Defaults to './output/payloads_generated'.
                - 'report_dir' (str, optional): Directory for saving reports. Defaults to './output/reports'.
                - 'timeout' (int, optional): Timeout for WebDAV requests. Defaults to 30.
                - 'verify_ssl' (bool, optional): Verify SSL certs. Defaults to True.
        """
        self.config = config
        self.base_output_dir = os.path.abspath(config.get('output_dir', './output'))
        self.payload_output_dir = os.path.join(self.base_output_dir, 'payloads_generated')
        self.report_dir = os.path.abspath(config.get('report_dir', os.path.join(self.base_output_dir, 'reports')))

        # Create output directories
        os.makedirs(self.payload_output_dir, exist_ok=True)
        os.makedirs(self.report_dir, exist_ok=True)

        self._setup_main_logger() # Application specific logger setup

        self.webdav_client = WebDAVClient(
            config['webdav_url'],
            username=config.get('username'),
            password=config.get('password'),
            timeout=config.get('timeout', 30),
            verify_ssl=config.get('verify_ssl', True)
        )

        # Pass the specific payload output directory to generators
        generator_config = {'output_dir': self.payload_output_dir}
        self.svg_generator = SVGPayloadGenerator(config=generator_config)
        self.css_generator = CSSPayloadGenerator(config=generator_config)

        self.results = []
        logger.info(f"WebDAVSecurityTester initialized for target: {config['webdav_url']}")
        logger.info(f"Payloads will be generated in: {self.payload_output_dir}")
        logger.info(f"Reports will be saved in: {self.report_dir}")

    def _setup_main_logger(self):
        """Configure main application logger if not already sufficiently configured."""
        # This method can be expanded if more specific app-level logging (e.g. to a dedicated app file) is needed
        # beyond what the module-level loggers provide. For now, module-level basicConfig is assumed.
        # If using a central logging config, this might just ensure the level.
        app_logger = logging.getLogger('WebDAVSecurityTesterApp') # A more specific name for this instance's logs
        if not app_logger.handlers:
            # Example: Add a file handler for application-level logs
            log_file_path = os.path.join(self.base_output_dir, 'enhanced_webdav_tester_app.log')
            fh = logging.FileHandler(log_file_path)
            formatter = logging.Formatter('%(asctime)s - %(name)s - [%(levelname)s] - %(message)s')
            fh.setFormatter(formatter)
            app_logger.addHandler(fh)
            app_logger.setLevel(self.config.get('log_level', logging.INFO)) # Configurable log level
            app_logger.propagate = False # Avoid double-logging if root logger also has console handler
        self.app_logger = app_logger # Use this for app-specific high level logs

    def run_test(self, file_type, payload_name, params=None, remote_target_dir="webdav_security_tests"):
        """
        Run a single security test: generate payload, upload, optionally verify.

        Args:
            file_type (str): 'svg' or 'css'.
            payload_name (str): The name of the payload type (e.g., 'basic', 'script_tag').
            params (dict, optional): Parameters for payload generation.
            remote_target_dir (str, optional): Base directory on WebDAV server for uploads.

        Returns:
            dict: A dictionary containing the test result.
        """
        self.app_logger.info(f"Starting test: FileType='{file_type}', PayloadName='{payload_name}', Params={params}")
        params = params or {}
        local_payload_path = None
        upload_success = False
        verify_success = False
        retrieved_content_matches = None # True, False, or None if not verified/retrieved
        error_message = None

        # Sanitize inputs for directory/file naming
        safe_file_type = "".join(c if c.isalnum() else "_" for c in file_type)
        safe_payload_name = "".join(c if c.isalnum() else "_" for c in payload_name)

        try:
            # 1. Generate payload
            if file_type == 'svg':
                generator = self.svg_generator
            elif file_type == 'css':
                generator = self.css_generator
            else:
                raise ValueError(f"Unsupported file type for testing: {file_type}")

            local_payload_path = generator.generate(payload_name, params)
            self.app_logger.info(f"Generated payload: {local_payload_path}")

            # 2. Define remote path
            # Use a structured path on the server, e.g., /<remote_target_dir>/<file_type>/<payload_name>/<filename>
            # This helps organize files on the server if many tests are run.
            filename_only = os.path.basename(local_payload_path)
            # Path needs to be URL-friendly; avoid characters that might be problematic.
            # The WebDAVClient's _construct_url should handle basic URL encoding of path segments.
            remote_path = f"{remote_target_dir}/{safe_file_type}/{safe_payload_name}/{filename_only}"
            self.app_logger.info(f"Target remote path: {remote_path}")

            # 3. Upload payload
            upload_success = self.webdav_client.put_file(local_payload_path, remote_path)
            if not upload_success:
                error_message = f"Upload failed for {remote_path}"
                self.app_logger.error(error_message)
            else:
                self.app_logger.info(f"Upload successful: {remote_path}")

                # 4. Verify by downloading (optional, but good practice)
                # This confirms the file is retrievable and content integrity.
                retrieved_content_bytes = self.webdav_client.get_file(remote_path)
                if retrieved_content_bytes is not None:
                    verify_success = True
                    with open(local_payload_path, 'rb') as f_orig:
                        original_content_bytes = f_orig.read()
                    retrieved_content_matches = (retrieved_content_bytes == original_content_bytes)
                    if not retrieved_content_matches:
                        self.app_logger.warning(f"Content mismatch for {remote_path} after download.")
                        error_message = error_message or "" + "Downloaded content does not match original. "
                    else:
                        self.app_logger.info(f"Verification GET and content match successful for {remote_path}")
                else:
                    verify_success = False # GET failed
                    error_message = error_message or "" + f"Verification GET failed for {remote_path}. "
                    self.app_logger.error(f"Verification GET failed for {remote_path}")

        except ValueError as ve: # Catch specific errors like unknown payload type
            error_message = str(ve)
            self.app_logger.error(f"Configuration error for test {file_type}/{payload_name}: {ve}")
        except NotImplementedError as nie: # From PayloadGenerator base if methods not implemented
            error_message = str(nie)
            self.app_logger.error(f"Payload generation not implemented for {file_type}/{payload_name}: {nie}")
        except Exception as e:
            error_message = f"Unexpected error during test {file_type}/{payload_name}: {str(e)}"
            self.app_logger.error(error_message, exc_info=True)
            # traceback.print_exc() # For more detailed console output during debugging

        result = {
            'timestamp': datetime.datetime.now().isoformat(),
            'file_type': file_type,
            'payload_name': payload_name,
            'params': params,
            'local_payload_path': local_payload_path,
            'remote_path': remote_path if 'remote_path' in locals() else None, # Ensure remote_path is defined
            'upload_success': upload_success,
            'verify_get_success': verify_success, # Clarify this is about the GET part of verification
            'content_match': retrieved_content_matches,
            'status': 'SUCCESS' if upload_success and verify_success and retrieved_content_matches else 'FAILURE',
            'error_message': error_message
        }
        self.results.append(result)
        self.app_logger.info(f"Test completed for {file_type}/{payload_name}. Status: {result['status']}")
        return result

    def run_batch_tests(self, test_configs):
        """
        Run multiple tests based on a list of test configurations.

        Args:
            test_configs (list[dict]): A list where each dict defines a test:
                {'file_type': 'svg', 'payload_name': 'basic', 'params': {}, 'remote_target_dir': 'optional_dir'}

        Returns:
            list[dict]: A list of result dictionaries from run_test.
        """
        self.app_logger.info(f"Starting batch of {len(test_configs)} tests.")
        batch_results = []
        for i, test_config in enumerate(test_configs):
            self.app_logger.info(f"Running batch test {i+1}/{len(test_configs)}: {test_config.get('file_type')}/{test_config.get('payload_name')}")
            try:
                result = self.run_test(
                    file_type=test_config['file_type'],
                    payload_name=test_config['payload_name'],
                    params=test_config.get('params'),
                    remote_target_dir=test_config.get('remote_target_dir', "webdav_security_tests_batch")
                )
                batch_results.append(result)
            except KeyError as ke:
                error_msg = f"Missing required key in test_config: {ke}"
                self.app_logger.error(error_msg)
                batch_results.append({
                    'timestamp': datetime.datetime.now().isoformat(),
                    'test_config': test_config,
                    'status': 'ERROR_CONFIG',
                    'error_message': error_msg
                })
            except Exception as e: # Catch any other unexpected error from run_test itself
                error_msg = f"Unexpected error running batch item {test_config}: {e}"
                self.app_logger.error(error_msg, exc_info=True)
                batch_results.append({
                    'timestamp': datetime.datetime.now().isoformat(),
                    'test_config': test_config,
                    'status': 'ERROR_UNEXPECTED',
                    'error_message': error_msg
                })
        self.app_logger.info("Batch testing finished.")
        return batch_results

    def generate_report(self, report_filename_base="webdav_security_assessment_report"):
        """Generate a comprehensive Markdown test report."""
        if not self.results:
            self.app_logger.warning("No test results available to generate a report.")
            return None

        timestamp_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"{report_filename_base}_{timestamp_str}.md"
        report_filepath = os.path.join(self.report_dir, report_filename)

        self.app_logger.info(f"Generating report: {report_filepath}")
        report_content = self._format_markdown_report()

        try:
            with open(report_filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)
            self.app_logger.info(f"Report successfully saved to {report_filepath}")
            return report_filepath
        except IOError as e:
            self.app_logger.error(f"Failed to save report to {report_filepath}: {e}")
            return None

    def _format_markdown_report(self):
        """Helper to format test results into a Markdown string."""
        report_lines = [
            f"# WebDAV Security Assessment Report",
            f"- **Date Generated**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"- **Target Server**: {self.config.get('webdav_url', 'N/A')}",
            f"- **Report File**: This document.",
            "\n## Summary of Test Results",
            f"- Total Tests Executed: {len(self.results)}"
        ]

        successful_uploads = sum(1 for r in self.results if r.get('upload_success'))
        verified_gets = sum(1 for r in self.results if r.get('verify_get_success'))
        content_matches = sum(1 for r in self.results if r.get('content_match') is True) # Explicitly True
        overall_successes = sum(1 for r in self.results if r.get('status') == 'SUCCESS')

        report_lines.append(f"- Tests with Successful Upload: {successful_uploads}")
        report_lines.append(f"- Tests with Successful Verification GET: {verified_gets}")
        report_lines.append(f"- Tests with Verified Content Match: {content_matches}")
        report_lines.append(f"- Overall Successful Tests (Upload & Verify & Match): {overall_successes}")
        report_lines.append(f"- Tests with Failures/Errors: {len(self.results) - overall_successes}")

        report_lines.append("\n## Detailed Test Results")
        if not self.results:
            report_lines.append("\nNo tests were run or no results available.")
        else:
            for i, result in enumerate(self.results, 1):
                report_lines.append(f"\n### Test {i}: {result.get('file_type', 'N/A')} / {result.get('payload_name', 'N/A')}")
                report_lines.append(f"- **Timestamp**: {result.get('timestamp', 'N/A')}")
                report_lines.append(f"- **Parameters**: `{json.dumps(result.get('params')) if result.get('params') else 'None'}`")
                report_lines.append(f"- **Local Payload**: `{result.get('local_payload_path', 'N/A')}`")
                report_lines.append(f"- **Remote Target**: `{result.get('remote_path', 'N/A')}`")
                report_lines.append(f"- **Upload Status**: {'SUCCESS' if result.get('upload_success') else 'FAILURE'}")
                report_lines.append(f"- **Verification GET**: {'SUCCESS' if result.get('verify_get_success') else 'FAILURE' if result.get('upload_success') else 'N/A'}")

                cm = result.get('content_match')
                content_match_str = 'MATCH' if cm is True else ('MISMATCH' if cm is False else 'N/A (Verification GET failed or not performed)')
                report_lines.append(f"- **Content Match**: {content_match_str}")

                report_lines.append(f"- **Overall Status**: **{result.get('status', 'UNKNOWN')}**")
                if result.get('error_message'):
                    report_lines.append(f"- **Error/Details**: `{result.get('error_message')}`")

        report_lines.append("\n## Security Recommendations")
        recommendations = self._generate_recommendations()
        if recommendations:
            for rec in recommendations:
                report_lines.append(f"- {rec}")
        else:
            report_lines.append("No specific recommendations generated based on these tests. General WebDAV hardening is always advised.")

        return "\n".join(report_lines)

    def _generate_recommendations(self):
        """Generate dynamic security recommendations based on test results."""
        # This is a basic example; a real version would be more sophisticated.
        recommendations = [
            "Regularly audit WebDAV server configurations and permissions.",
            "Employ strong authentication and authorization mechanisms for WebDAV access.",
            "Use HTTPS for all WebDAV communications.",
            "Implement Content Security Policy (CSP) headers on any web applications that might serve or reference content from this WebDAV server, especially if SVGs or HTML can be rendered."
        ]

        # Example: If any SVG upload was successful
        if any(r.get('upload_success') and r.get('file_type') == 'svg' for r in self.results):
            recommendations.append("Sanitize or restrict SVG uploads: SVGs can contain executable JavaScript. If SVGs are served and rendered, ensure they are from trusted sources or properly sanitized (e.g., using a library like DOMPurify if rendered client-side, or server-side sanitization). Consider disallowing SVG uploads if not strictly necessary or if they cannot be effectively secured.")

        if any(r.get('upload_success') and r.get('file_type') == 'css' for r in self.results):
            recommendations.append("Review CSS serving: While CSS itself rarely leads to direct RCE, it can be used for UI redressing, data exfiltration attempts (as tested), or as part of more complex XSS chains if HTML injection is also possible. Ensure CSS files are served with `Content-Type: text/css` and the `X-Content-Type-Options: nosniff` header.")

        if any(r.get('status') == 'FAILURE' for r in self.results):
             recommendations.append("Investigate failed tests: Understand why certain uploads, verifications, or content matches failed. This could indicate server-side protections, network issues, or misconfigurations that inadvertently provide some security.")

        return recommendations

    def get_all_available_tests(self):
        """Returns a list of all available test identifiers (file_type/payload_name)."""
        tests = []
        for pt in self.svg_generator.get_available_payloads():
            tests.append(f"svg/{pt}")
        for pt in self.css_generator.get_available_payloads():
            tests.append(f"css/{pt}")
        return tests


if __name__ == '__main__':
    # This basicConfig is for the __main__ execution of this file.
    # Module-level loggers (WebDAVClient, SVGPayloadGenerator, CSSPayloadGenerator)
    # will also use this if they haven't been configured by an application.
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - [%(levelname)s] %(name)s: %(message)s')
    main_logger_tester = logging.getLogger(__name__) # For messages from this __main__ block

    main_logger_tester.info("WebDAVSecurityTester demonstration started.")

    # Configuration for the tester
    # IMPORTANT: For live tests, set the TEST_WEBDAV_URL environment variable.
    # Optionally, set TEST_WEBDAV_USER and TEST_WEBDAV_PASS for authenticated servers.
    # And TEST_WEBDAV_NO_SSL_VERIFY="true" to disable SSL cert checks (use with caution).
    test_url = os.environ.get("TEST_WEBDAV_URL")
    if not test_url:
        main_logger_tester.warning("TEST_WEBDAV_URL environment variable not set. Cannot run live demonstration.")
        main_logger_tester.info("To run a live test, set TEST_WEBDAV_URL, e.g.:")
        main_logger_tester.info("export TEST_WEBDAV_URL='http://localhost:8080/webdav'")
        main_logger_tester.info("export TEST_WEBDAV_USER='youruser'") # if auth needed
        main_logger_tester.info("export TEST_WEBDAV_PASS='yourpass'") # if auth needed
        exit()

    config = {
        'webdav_url': test_url,
        'username': os.environ.get("TEST_WEBDAV_USER"),
        'password': os.environ.get("TEST_WEBDAV_PASS"),
        'output_dir': './ewt_output', # Main output for logs, payloads, reports
        'report_dir': './ewt_output/reports', # Specific subdir for reports
        'timeout': 45,
        'verify_ssl': not (os.environ.get("TEST_WEBDAV_NO_SSL_VERIFY", "false").lower() == "true"),
        'log_level': logging.DEBUG # For the app_logger instance within WebDAVSecurityTester
    }

    tester = WebDAVSecurityTester(config)
    tester.app_logger.info("WebDAVSecurityTester instance created for demonstration.")

    main_logger_tester.info(f"Available tests: {tester.get_all_available_tests()}")

    # Example: Run a few specific tests
    tests_to_run = [
        {'file_type': 'svg', 'payload_name': 'basic', 'params': {}},
        {'file_type': 'svg', 'payload_name': 'script_tag', 'params': {'js_code': "console.log('SVG script_tag test executed: ' + document.domain);"}},
        {'file_type': 'css', 'payload_name': 'basic', 'params': {}},
        {'file_type': 'css', 'payload_name': 'font_face_exfil',
         'params': {'callback_url': 'http://localhost:12345/css_font_exfil_test_callback', 'font_family_name': 'DemoTestFont'}}
    ]

    # Example: Remote directory for this test run
    # Using a timestamp to try and keep test runs somewhat isolated on the server.
    # Ensure your WebDAV server allows creation of subdirectories or that this base path exists and is writable.
    test_run_remote_dir = f"ewt_demorun_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
    main_logger_tester.info(f"Test files will be uploaded under remote directory: {test_run_remote_dir}")

    for test_conf in tests_to_run:
        test_conf['remote_target_dir'] = test_run_remote_dir # Add/override remote_target_dir for each test

    results = tester.run_batch_tests(tests_to_run)

    main_logger_tester.info("\n--- Batch Test Run Summary ---")
    for res in results:
        main_logger_tester.info(
            f"Test: {res.get('file_type')}/{res.get('payload_name')} - "
            f"Status: {res.get('status')} - "
            f"Upload: {res.get('upload_success')} - "
            f"VerifyGet: {res.get('verify_get_success')} - "
            f"ContentMatch: {res.get('content_match')}"
        )
        if res.get('error_message'):
            main_logger_tester.warning(f"  Error: {res.get('error_message')}")


    report_file = tester.generate_report(report_filename_base="DemoRun_WebDAV_Security_Report")
    if report_file:
        main_logger_tester.info(f"Markdown report generated at: {report_file}")
    else:
        main_logger_tester.error("Failed to generate report.")

    main_logger_tester.info(f"Demonstration finished. Check logs in {config['output_dir']}.")
    main_logger_tester.info(f"IMPORTANT: Manually verify and clean up files on the WebDAV server under '{test_run_remote_dir}' if tests ran.")
