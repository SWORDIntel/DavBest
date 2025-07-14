import argparse
import json
import logging
import os
import sys
import textwrap # For formatting help text

# Assuming other modules are in the same directory or PYTHONPATH
from webdav_security_tester import WebDAVSecurityTester
from webdav_server import DAVServer
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
          %(prog)s test --url https://webdav.example.com --username user --password pass --test svg/script_tag --js-code "alert('Custom XSS');"
          %(prog)s test --url http://localhost/dav --list-tests
          %(prog)s batch --config /path/to/my_test_batch.json --report-dir ./my_reports
          %(prog)s serve --dir ./payloads --port 80
        ''')
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.required = True

    # --- NEW: Subparser for the 'serve' command ---
    serve_parser = subparsers.add_parser("serve", help="Start a lightweight WebDAV server for payload staging.")
    serve_parser.add_argument("--dir", default="./webdav_root", help="Root directory to serve files from. Default: ./webdav_root")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host IP to bind the server to. Default: 0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to run the server on. Default: 8080")

    # --- Subparser for the 'test' command ---
    test_parser = subparsers.add_parser("test", help="Run single or list available tests.")
    # Server Connection Arguments
    server_group = test_parser.add_argument_group('Server Connection')
    server_group.add_argument('--url', required=True, help='Target WebDAV server URL (e.g., https://webdav.example.com/path).')
    server_group.add_argument('--username', help='Username for WebDAV authentication.')
    server_group.add_argument('--password', help='Password for WebDAV authentication.')
    server_group.add_argument('--timeout', type=int, default=30, help='Timeout for WebDAV requests in seconds (default: 30).')
    server_group.add_argument('--no-verify-ssl', action='store_false', dest='verify_ssl', default=True, help='Disable SSL certificate verification (use with caution).')

    # Test Execution Arguments (mutually exclusive)
    execution_group = test_parser.add_mutually_exclusive_group(required=True)
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

    # Payload Parameter Arguments
    payload_params_group = test_parser.add_argument_group('Payload Parameters (for --test mode)')
    payload_params_group.add_argument('--js-code', help="JavaScript code to embed in relevant SVG payloads (e.g., script_tag, event_handler).")
    payload_params_group.add_argument('--callback-url', help="Callback URL for exfiltration payloads (e.g., SVG data_exfil, CSS background_exfil).")
    payload_params_group.add_argument('--target-element', help="CSS selector for targeting elements in CSS exfiltration payloads.")

    # Output and Reporting Arguments
    output_group = test_parser.add_argument_group('Output and Reporting')
    output_group.add_argument('--output-dir', default='./ewt_output', help="Main directory for tool output (logs, generated payloads). Default: ./ewt_output.")
    output_group.add_argument('--report-dir', help="Specific directory for Markdown reports (if not specified, defaults to 'reports' under --output-dir).")
    output_group.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Set the logging level for console output (default: INFO).')

    # --- Subparser for the 'batch' command ---
    batch_parser = subparsers.add_parser("batch", help="Run a batch of tests from a JSON file.")
    batch_parser.add_argument('--config', required=True, metavar='JSON_FILE', help='Path to the JSON batch configuration file.')
    # Re-add server and output args for batch, as they are not shared across subparsers
    batch_server_group = batch_parser.add_argument_group('Server Connection')
    batch_server_group.add_argument('--url', required=True, help='Target WebDAV server URL.')
    batch_server_group.add_argument('--username', help='Username for WebDAV authentication.')
    batch_server_group.add_argument('--password', help='Password for WebDAV authentication.')
    batch_server_group.add_argument('--timeout', type=int, default=30, help='Timeout for WebDAV requests.')
    batch_server_group.add_argument('--no-verify-ssl', action='store_false', dest='verify_ssl', default=True, help='Disable SSL certificate verification.')
    batch_output_group = batch_parser.add_argument_group('Output and Reporting')
    batch_output_group.add_argument('--output-dir', default='./ewt_output', help="Main directory for tool output.")
    batch_output_group.add_argument('--report-dir', help="Specific directory for Markdown reports.")
    batch_output_group.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Set the logging level.')


    args = parser.parse_args()

    # Adjust logging level based on CLI argument for the root logger
    if hasattr(args, 'log_level'):
        logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    if args.command == "serve":
        server = DAVServer(root_path=args.dir, host=args.host, port=args.port)
        server.start()
        sys.exit(0)

    # Common logic for 'test' and 'batch' commands
    # Prepare configuration for WebDAVSecurityTester
    config = {
        'webdav_url': args.url,
        'username': args.username,
        'password': args.password,
        'output_dir': args.output_dir,
        'report_dir': args.report_dir if args.report_dir else os.path.join(args.output_dir, 'reports'),
        'timeout': args.timeout,
        'verify_ssl': args.verify_ssl,
        'log_level': getattr(logging, args.log_level.upper()) if hasattr(args, 'log_level') else logging.INFO
    }

    try:
        tester = WebDAVSecurityTester(config)
    except Exception as e:
        logger.critical(f"Failed to initialize WebDAVSecurityTester: {e}", exc_info=True)
        sys.exit(1)

    if args.command == "test":
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
        if args.target_element:
            payload_params['target_element'] = args.target_element
            payload_params['target_input_selector'] = args.target_element

        if args.test:
            try:
                file_type, payload_name = args.test.split('/', 1)
                logger.info(f"Running single test: FileType='{file_type}', PayloadName='{payload_name}', Params={payload_params}")
                single_test_remote_dir = f"ewt_single_test_{file_type}_{payload_name}_{int(time.time())}"
                tester.run_test(file_type, payload_name, params=payload_params, remote_target_dir=single_test_remote_dir)
            except ValueError:
                logger.error(f"Invalid format for --test argument: '{args.test}'. Must be 'filetype/payloadname'.")
                sys.exit(1)
            except Exception as e:
                logger.critical(f"An error occurred while running the test '{args.test}': {e}", exc_info=True)
                sys.exit(1)

    elif args.command == "batch":
        logger.info(f"Running batch tests from file: {args.config}")
        if not os.path.exists(args.config):
            logger.critical(f"Batch configuration file not found: {args.config}")
            sys.exit(1)
        try:
            with open(args.config, 'r', encoding='utf-8') as f:
                batch_configs = json.load(f)
            if not isinstance(batch_configs, list) and isinstance(batch_configs, dict) and 'tests' in batch_configs:
                batch_configs = batch_configs['tests']
            elif not isinstance(batch_configs, list):
                 raise TypeError("Batch file must contain a JSON list of test configurations.")

            tester.run_batch_tests(batch_configs)
        except (json.JSONDecodeError, TypeError) as ex:
            logger.critical(f"Invalid format in batch file {args.config}: {ex}")
            sys.exit(1)
        except Exception as e:
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
