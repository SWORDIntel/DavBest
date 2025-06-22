# DAVBest: WebDAV Management and Testing Tool

DAVBest is a Python-based command-line tool designed for comprehensive WebDAV server path handling analysis and content management. It integrates functionalities for testing path traversal vulnerabilities (inspired by CVE-2025-33053 concepts) and utilities for encoding/decoding content using UUIDs, which can be useful for certain payload delivery techniques.

**SECURITY NOTICE:** This tool is intended for authorized security assessment and educational purposes only. Use it responsibly and only against systems you have explicit permission to test. All analytical actions that involve server interaction are logged by the tool.

## Features

*   **WebDAV Path Analysis (`analyze`):**
    *   Tests various path manipulation techniques against a target WebDAV server.
    *   Detects server platform (IIS, Apache, Nginx, Unknown) for tailored payload generation.
    *   Supports different payload types for testing file placement and execution:
        *   `info`: A simple script displaying system information.
        *   `echo`: A script that echoes back a parameter.
        *   `uuid`: An information script encoded using UUIDs and wrapped in a platform-specific decoder (ASP for IIS, PHP for Apache/Nginx, raw UUIDs for Unknown).
    *   Generates a JSON report of test results.
    *   Supports HTTP/HTTPS, authentication, and proxy configuration.
*   **UUID Content Encoding (`encode-uuid`):**
    *   Encodes arbitrary file content (or stdin) into a list of UUIDs.
    *   Can output raw UUIDs or wrap them in an ASP or PHP decoder script.
    *   Customizable chunk size for encoding (1-16 bytes of original content per UUID).
*   **UUID Content Decoding (`decode-uuid`):**
    *   Decodes a list of UUIDs (from file or stdin) back into the original content.

## Requirements

*   Python 3.8+
*   External libraries: `requests`, `rich`

## Installation

1.  Clone the repository or download the `dav_best.py` script and other files into a directory (e.g., `DAVBest`).
2.  Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```
    (Ensure `requirements.txt` is in the `DAVBest` directory or specify the correct path)

## Usage

The tool is operated via subcommands.

```bash
python dav_best.py -h
```

### Analyze WebDAV Paths

```bash
python dav_best.py analyze -t <target_url> [options]
```

**Common Options for `analyze`:**
*   `-t, --target TARGET`: (Required) Target WebDAV server URL (e.g., `http://localhost/webdav`).
*   `-d, --directory DIRECTORY`: Base WebDAV directory for tests (default: `davbest_tests`).
*   `--payload {info,echo,uuid,all}`: Payload type to use (default: `info`).
*   `-u, --username USERNAME`: WebDAV username.
*   `-p, --password PASSWORD`: WebDAV password.
*   `--proxy PROXY`: HTTP/HTTPS proxy URL.
*   `--no-verify-ssl`: Disable SSL certificate verification.
*   `--user-agent USER_AGENT`: Custom User-Agent string.

**Example `analyze`:**
```bash
python dav_best.py analyze -t http://example.com/webdav --payload uuid -u testuser -p testpass
```

### Encode Content to UUIDs

```bash
python dav_best.py encode-uuid [options]
```
**Options for `encode-uuid`:**
*   `-i, --input INPUT_FILE`: Input file path (reads from stdin if not specified).
*   `-o, --output OUTPUT_FILE`: Output file path (writes to stdout if not specified).
*   `--type {asp,php,raw}`: Output type (default: `raw`).
*   `--chunk-size SIZE`: Chunk size for encoding (1-16, default: 16).

**Example `encode-uuid`:**
```bash
# Encode a file to raw UUIDs
python dav_best.py encode-uuid -i payload.sh -o payload.uuids

# Encode stdin to a PHP UUID decoder script
echo "<?php phpinfo(); ?>" | python dav_best.py encode-uuid --type php -o shell.php_uuid.php
```

### Decode UUIDs to Content

```bash
python dav_best.py decode-uuid [options]
```
**Options for `decode-uuid`:**
*   `-i, --input INPUT_FILE`: Input file path with UUIDs (reads from stdin if not specified).
*   `-o, --output OUTPUT_FILE`: Output file path for decoded content (writes to stdout if not specified).

**Example `decode-uuid`:**
```bash
python dav_best.py decode-uuid -i payload.uuids -o payload_decoded.sh
```

## Logging

The tool logs its activities to `dav_best.log` in the directory where it's run, and also prints to the console.
Analysis reports are saved as JSON files (e.g., `dav_best_analysis_YYYYMMDD_HHMMSS_clientid.json`).

## Disclaimer

This tool is provided as-is. The developers assume no liability and are not responsible for any misuse or damage caused by this program. Ensure you have proper authorization before using it on any target.
