import argparse
import json
import logging
import os
import sys
import textwrap # For formatting help text

# Assuming other modules are in the same directory or PYTHONPATH
from webdav_security_tester import WebDAVSecurityTester
# SVG and CSS generators are used by WebDAVSecurityTester, but listing tests might need them directly or via tester.

# Setup basic logging for the CLI tool itself.
# More detailed logging is handled within the classes.
# The level set here will be the minimum for console output from this script.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] %(name)s (CLI): %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the Enhanced WebDAV Security Testing tool CLI."""
    parser = argparse.ArgumentParser(
        description='Enhanced WebDAV Security Assessment Tool - Test for vulnerabilities using SVG/CSS payloads.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
        Examples:
          %(prog)s --url https://webdav.example.com --username user --password pass --test svg/script_tag --js-code "alert('Custom XSS');"
          %(prog)s --url http://localhost/dav --list-tests
          %(prog)s --url https://secure.dav.server/ --batch /path/to/my_test_batch.json --report-dir ./my_reports
          %(prog)s --url https://webdav.example.com --test css/background_exfil --callback https://my.listener.com/css_hit
        ''')
    )

    # Server Connection Arguments
    server_group = parser.add_argument_group('Server Connection')
    server_group.add_argument('--url', required=True, help='Target WebDAV server URL (e.g., https://webdav.example.com/path).')
    server_group.add_argument('--username', help='Username for WebDAV authentication.')
    server_group.add_argument('--password', help='Password for WebDAV authentication.')
    server_group.add_argument('--timeout', type=int, default=30, help='Timeout for WebDAV requests in seconds (default: 30).')
    server_group.add_argument('--no-verify-ssl', action='store_false', dest='verify_ssl', default=True, help='Disable SSL certificate verification (use with caution).')

    # Test Execution Arguments (mutually exclusive)
    execution_group = parser.add_mutually_exclusive_group(required=True)
    execution_group.add_argument(
        '--test',
        metavar='FILETYPE/PAYLOADNAME',
        help='Run a single test. Format: filetype/payloadname (e.g., svg/script_tag, css/basic).'
    )
    execution_group.add_argument(
        '--list-tests',
        action='store_true',
        help='List all available test types (filetype/payloadname combinations).'
    )
    execution_group.add_argument(
        '--batch',
        metavar='JSON_FILE',
        help='Run a batch of tests defined in a JSON configuration file.'
    )

    # Payload Parameter Arguments
    payload_params_group = parser.add_argument_group('Payload Parameters (for --test mode)')
    payload_params_group.add_argument('--js-code', help="JavaScript code to embed in relevant SVG payloads (e.g., script_tag, event_handler).")
    payload_params_group.add_argument('--callback-url', help="Callback URL for exfiltration payloads (e.g., SVG data_exfil, CSS background_exfil).")
    payload_params_group.add_argument('--target-element', help="CSS selector for targeting elements in CSS exfiltration payloads.")
    # Add more specific params as payload types grow, or use a generic --param 'key=value'

    # Output and Reporting Arguments
    output_group = parser.add_argument_group('Output and Reporting')
    output_group.add_argument('--output-dir', default='./ewt_output', help="Main directory for tool output (logs, generated payloads). Default: ./ewt_output.")
    # report_dir will be a subdir of output_dir by default in WebDAVSecurityTester, but allow override
    output_group.add_argument('--report-dir', help="Specific directory for Markdown reports (if not specified, defaults to 'reports' under --output-dir).")
    output_group.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Set the logging level for console output (default: INFO).')


    args = parser.parse_args()

    # Adjust logging level based on CLI argument for the root logger (affects console)
    # Class loggers might have their own levels or inherit.
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))


    # Prepare configuration for WebDAVSecurityTester
    config = {
        'webdav_url': args.url,
        'username': args.username,
        'password': args.password,
        'output_dir': args.output_dir,
        'report_dir': args.report_dir if args.report_dir else os.path.join(args.output_dir, 'reports'), # Default logic
        'timeout': args.timeout,
        'verify_ssl': args.verify_ssl,
        'log_level': getattr(logging, args.log_level.upper()) # Pass to tester for its own logger
    }

    try:
        tester = WebDAVSecurityTester(config)
    except Exception as e:
        logger.critical(f"Failed to initialize WebDAVSecurityTester: {e}", exc_info=True)
        sys.exit(1)

    if args.list_tests:
        logger.info("Listing available tests...")
        available_tests = tester.get_all_available_tests()
        if available_tests:
            print("\nAvailable tests (format: filetype/payloadname):")
            for test_name in available_tests:
                print(f"  - {test_name}")
        else:
            print("No tests available or found.")
        sys.exit(0)

    # Collect payload parameters for single test mode
    payload_params = {}
    if args.js_code:
        payload_params['js_code'] = args.js_code
    if args.callback_url:
        payload_params['callback_url'] = args.callback_url
    if args.target_element: # For CSS payloads
        payload_params['target_element'] = args.target_element
        payload_params['target_input_selector'] = args.target_element # Alias for input_value_exfil

    if args.test:
        try:
            file_type, payload_name = args.test.split('/', 1)
            logger.info(f"Running single test: FileType='{file_type}', PayloadName='{payload_name}', Params={payload_params}")
            # Define a default remote directory for single tests if needed, or let tester handle it
            # For consistency with batch, let's pass a default.
            # Users might want to customize this later.
            single_test_remote_dir = f"ewt_single_test_{file_type}_{payload_name}_{int(time.time())}"
            tester.run_test(file_type, payload_name, params=payload_params, remote_target_dir=single_test_remote_dir)
        except ValueError:
            logger.error(f"Invalid format for --test argument: '{args.test}'. Must be 'filetype/payloadname'.")
            print("\nExample: --test svg/script_tag")
            print("Use --list-tests to see available options.")
            sys.exit(1)
        except Exception as e: # Catch errors from run_test
            logger.critical(f"An error occurred while running the test '{args.test}': {e}", exc_info=True)
            sys.exit(1)

    elif args.batch:
        logger.info(f"Running batch tests from file: {args.batch}")
        if not os.path.exists(args.batch):
            logger.critical(f"Batch configuration file not found: {args.batch}")
            sys.exit(1)
        try:
            with open(args.batch, 'r', encoding='utf-8') as f:
                batch_configs = json.load(f)

            if not isinstance(batch_configs, list):
                # Allow for a root "tests": [] structure as in user's example
                if isinstance(batch_configs, dict) and 'tests' in batch_configs and isinstance(batch_configs['tests'], list):
                    batch_configs = batch_configs['tests']
                else:
                    logger.critical("Batch file must contain a JSON list of test configurations, or a JSON object with a 'tests' key holding such a list.")
                    sys.exit(1)

            tester.run_batch_tests(batch_configs)
        except json.JSONDecodeError as jde:
            logger.critical(f"Invalid JSON in batch file {args.batch}: {jde}")
            sys.exit(1)
        except Exception as e: # Catch errors from run_batch_tests
            logger.critical(f"An error occurred during batch test execution: {e}", exc_info=True)
            sys.exit(1)

    # Generate report after tests are run
    logger.info("Attempting to generate final report...")
    report_file_path = tester.generate_report()
    if report_file_path:
        logger.info(f"Execution finished. Report generated at: {report_file_path}")
    else:
        logger.warning("Execution finished, but report generation failed or no results to report.")

    logger.info("Enhanced WebDAV Security Tester finished.")

if __name__ == "__main__":
    # Add a simple check for dependent files in the same directory for easier execution if not installed.
    # This is a developer convenience, not a substitute for proper packaging.
    required_files = ['webdav_security_tester.py', 'payload_generator.py', 'svg_payload_generator.py', 'css_payload_generator.py']
    missing_files = [f for f in required_files if not os.path.exists(os.path.join(os.path.dirname(__file__), f))]
    if missing_files:
        sys.stderr.write("Error: Missing one or more required module files in the current directory:\n")
        for mf in missing_files:
             sys.stderr.write(f" - {mf}\n")
        sys.stderr.write("Please ensure all script components are present or the tool is properly installed.\n")
        sys.exit(1)

    # Import time for single test remote dir naming, if not already imported
    import time

    main()
