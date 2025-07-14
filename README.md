# Enhanced WebDAV Security Assessment Tool (EWT)

The Enhanced WebDAV Security Assessment Tool (EWT) is a Python-based command-line utility designed to help security professionals assess the security posture of WebDAV servers. It focuses on testing how servers handle potentially malicious file uploads and path manipulations, with a special emphasis on payloads embedded within SVG and CSS files.

**SECURITY NOTICE:** This tool is intended for authorized security assessment and educational purposes ONLY. Misuse of this tool on systems for which you do not have explicit, written permission is illegal and unethical. The developers assume no liability and are not responsible for any misuse or damage caused by this program. All actions that involve server interaction can be logged.

## Features

*   **Flexible WebDAV Client**: Interacts with WebDAV servers using PUT, GET, DELETE, and PROPFIND (for directory listing). Supports basic authentication and SSL/TLS.
*   **SVG Payload Generation & Testing**:
    *   Generates various types of SVG payloads designed to test for XSS and other vulnerabilities when SVGs are served and rendered.
    *   Supported SVG types: `basic`, `script_tag` (JS in `<script>`), `event_handler` (JS in `onload` etc.), `animate` (JS in animation events), `foreign_object` (HTML+JS in SVG), `data_exfil` (JS to send data to a callback), `polyglot` (SVG/JS).
*   **CSS Payload Generation & Testing**:
    *   Generates CSS payloads to test for data exfiltration capabilities and other CSS-based attack vectors.
    *   Supported CSS types: `basic`, `background_exfil` (generic exfil via `background-image`), `font_face_exfil` (`@font-face` exfil), `media_query_exfil` (fingerprinting via media queries), `input_value_exfil` (attempt to leak input values), `keylogger_simulation` (simulated keylogging).
*   **Test Orchestration**:
    *   Run single, targeted tests against a WebDAV server.
    *   Execute batches of tests defined in a JSON configuration file.
*   **Parameterizable Payloads**: Customize JavaScript code, callback URLs, and target CSS selectors for generated payloads.
*   **Comprehensive Reporting**: Generates detailed Markdown reports summarizing test activities, successes, failures, and basic security recommendations.
*   **Configurable Output**: Control directories for generated payloads, reports, and logs.
*   **Logging**: Detailed logging of operations for debugging and audit.

### Operational Security Features

*   **C2 Obfuscation & Hardening**:
    *   **HTTP Header Spoofing**: The WebDAV server can spoof its `Server` header to mimic other servers (e.g., IIS), making it harder to fingerprint. The header value is stored in Base64 to avoid simple static analysis.
    *   **TLS/SSL Integration**: The WebDAV server can be started with TLS/SSL encryption (`--tls` flag) to protect C2 communications. It uses a self-signed certificate by default.
*   **Vector Generation Engine**:
    *   A TUI-based wizard allows for the rapid creation of attack packages.
    *   The engine combines a payload (e.g., an executable) with a decoy document (e.g., a PDF) and generates a `.url` file that, when clicked, accesses the decoy document while executing the payload from the WebDAV server.
*   **Real-time Intelligence Panel**:
    *   The WebDAV server includes an "Intel Middleware" that logs requests for specific, high-value assets (e.g., the payload).
    *   This provides real-time alerts when a target interacts with the staged files, including the target's IP address and the requested asset.
*   **Payload Lifecycle Management**:
    *   A `build` command in the CLI allows for the generation of payload source code from C-style templates.
    *   This feature enables quick customization of payloads by replacing placeholders for C2 server IP addresses and ports.

## Requirements

*   Python 3.8+
*   External libraries: `requests` (ensure this is installed, e.g., `pip install requests`)

## Installation

1.  Ensure Python 3.8+ is installed.
2.  Clone the repository or download all the Python files (`ewt_cli.py`, `webdav_security_tester.py`, `payload_generator.py`, `svg_payload_generator.py`, `css_payload_generator.py`) into a single directory.
3.  Install the `requests` library:
    ```bash
    pip install requests
    ```
    (If a `requirements.txt` file is provided with the tool, you can use `pip install -r requirements.txt`.)

## Usage (`ewt_cli.py`)

The primary entry point is `ewt_cli.py`.

```bash
python ewt_cli.py --help
```

### Common Arguments

*   `--url TARGET_URL`: (Required) The full URL of the target WebDAV server (e.g., `http://localhost/webdav/`).
*   `--username USER`: Username for WebDAV authentication.
*   `--password PASS`: Password for WebDAV authentication.
*   `--timeout SECS`: Request timeout in seconds (default: 30).
*   `--no-verify-ssl`: Disable SSL certificate verification (use with caution for test environments).
*   `--output-dir DIR`: Main directory for tool output (logs, generated payloads). Default: `./ewt_output`.
*   `--report-dir DIR`: Specific directory for Markdown reports. Default: `<output-dir>/reports`.
*   `--log-level LEVEL`: Set console logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL). Default: INFO.

### Running Tests

**1. List Available Tests:**
To see all built-in payload types:
```bash
python ewt_cli.py --url http://ignore.me --list-tests
```
*(Note: `--url` is technically required by argparse even for `--list-tests` for the current CLI design, but its value isn't used in this mode beyond initializing the WebDAVClient which isn't strictly needed for just listing).*

**2. Run a Single Test:**
Use the format `FILETYPE/PAYLOADNAME`.
```bash
# Basic SVG test
python ewt_cli.py --url <TARGET_URL> --test svg/basic

# SVG with custom JavaScript in a <script> tag
python ewt_cli.py --url <TARGET_URL> --test svg/script_tag --js-code "alert('My Custom SVG XSS: ' + document.domain);"

# CSS data exfiltration test using @font-face, with a custom callback
python ewt_cli.py --url <TARGET_URL> --test css/font_face_exfil --callback-url "https://my.listener.com/css_font_hit"
```

**Available Payload Parameters for `--test` mode:**
*   `--js-code "JAVASCRIPT_CODE"`: For SVG payloads like `script_tag`, `event_handler`, `animate`, `foreign_object`, `polyglot`. Also for SVG `data_exfil` if `data_to_exfil_script` parameter is used within it.
*   `--callback-url "URL"`: For exfiltration payloads like `svg/data_exfil`, `css/background_exfil`, `css/font_face_exfil`, etc.
*   `--target-element "CSS_SELECTOR"`: For some CSS payloads like `css/input_value_exfil` or `css/keylogger_simulation` (where it's used as `target_input_selector`).

**3. Run Batch Tests from a JSON File:**
Create a JSON file defining multiple tests. Example (`my_tests.json`):
```json
{
  "tests": [
    {
      "file_type": "svg",
      "payload_name": "event_handler",
      "params": {"js_code": "console.warn('SVG event handler from batch');"},
      "remote_target_dir": "my_company_tests/svg_events"
    },
    {
      "file_type": "css",
      "payload_name": "media_query_exfil",
      "params": {"callback_url": "https://my.listener.com/batch_media_query"},
      "remote_target_dir": "my_company_tests/css_fingerprinting"
    }
    // Add more test configurations here
  ]
}
```
Then run:
```bash
python ewt_cli.py --url <TARGET_URL> --batch my_tests.json
```
The `remote_target_dir` in the JSON is optional for each test item; the tool will use a default if not provided.

### Output

*   **Generated Payloads**: Saved in `<output-dir>/payloads_generated/`.
*   **Application Log**: A detailed application log is saved to `<output-dir>/enhanced_webdav_tester_app.log`.
*   **Markdown Reports**: Saved in the specified report directory (default: `<output-dir>/reports/`).

## Payload Types Reference

### SVG Payloads (`svg/...`)
*   `basic`: Benign SVG for basic upload/retrieval test.
*   `script_tag`: Embeds JS using `<script><![CDATA[...]]></script>`.
*   `event_handler`: Embeds JS in an SVG event handler (e.g., `onload`).
*   `animate`: Embeds JS in an animation event (e.g., `onbegin`).
*   `foreign_object`: Embeds HTML (which can include `<script>`) within the SVG.
*   `data_exfil`: SVG with JS designed to send data (e.g., `document.cookie`) to a specified callback URL.
*   `polyglot`: A file structured to be valid as both SVG and executable JavaScript.

### CSS Payloads (`css/...`)
*   `basic`: Benign CSS for basic upload/retrieval test.
*   `background_exfil`: Attempts to trigger a request to a callback URL via `background-image: url(...)`.
*   `font_face_exfil`: Uses `@font-face { src: url(...); }` to trigger a request.
*   `media_query_exfil`: Uses various media queries to conditionally request URLs, potentially for device fingerprinting.
*   `input_value_exfil`: Attempts to leak characters from input field values using attribute selectors and `background-image`. Highly browser-dependent.
*   `keylogger_simulation`: Attempts to detect last typed characters in inputs using attribute selectors. Highly browser-dependent.

## Development Notes & Structure

*   `ewt_cli.py`: Main command-line interface.
*   `webdav_security_tester.py`: Orchestrates tests (`WebDAVSecurityTester` class).
*   `webdav_client.py`: Handles WebDAV communications (`WebDAVClient` class).
*   `payload_generator.py`: Base class for payload generation (`PayloadGenerator`).
*   `svg_payload_generator.py`: Generates SVG payloads (`SVGPayloadGenerator` class).
*   `css_payload_generator.py`: Generates CSS payloads (`CSSPayloadGenerator` class).

## Disclaimer

This tool is for educational and authorized testing purposes only. The user is responsible for any and all actions performed using this tool. Ensure you comply with all applicable laws and obtain necessary permissions before testing any system.
---
A `requirements.txt` file should also be created for this new tool:
```
requests
```
(Currently, only `requests` is a direct external dependency for the core functionality. `rich` was for DAVBest, this new tool doesn't explicitly use it yet unless added for fancier CLI output later).
