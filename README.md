# DavBest 2.XXX EXPLICIT
*Modern WebDAV upload‑and‑execution tester & Host Integrity Validation Suite*

_davtest.pl 1.x (2015) rewrite in Python 3, now with Host Integrity Sensing capabilities_

© 2015 – 2025 Websec SC & Contributors · GPL‑3.0‑or‑later

---

## Table of Contents
1. [About](#about)
2. [License](#license)
3. [Features](#features)
    * [DavTester (WebDAV Security Testing)](#davtester-webdav-security-testing)
    * [DavBest Integrity Sensor (Host Integrity Validation)](#davbest-integrity-sensor-host-integrity-validation)
4. [DavBest Integrity Sensor Module](#davbest-integrity-sensor-module)
    * [4.1. Overview & Purpose](#41-overview--purpose)
    * [4.2. Core Components](#42-core-components)
    * [4.3. Workflow](#43-workflow)
    * [4.4. Compilation (`davbest_sensor.so`)](#44-compilation-davbest_sensorso)
    * [4.5. Deployment & Execution](#45-deployment--execution)
    * [4.6. Alerting](#46-alerting)
    * [4.7. Test Environment & Verification](#47-test-environment--verification)
5. [DavTester WebDAV Security Tool](#davtester-webdav-security-tool)
    * [5.1. Requirements](#51-requirements-davtester)
    * [5.2. Installation](#52-installation-davtester)
    * [5.3. Usage](#53-usage-davtester)
        * [Command-line mode](#command-line-mode)
        * [TUI menu mode](#tui-menu-mode)
    * [5.4. Tests & Backdoors (DavTester)](#54-tests--backdoors-davtester)
    * [5.5. Examples (DavTester)](#55-examples-davtester)
6. [Roadmap / TODO](#roadmap--todo)
7. [Changelog](#changelog)
8. [Credits](#credits)

---

## 1. About
`DavBest` is a suite of security tools. Its initial component, `DAVTester`, targets WebDAV-enabled servers to determine which script types can be **uploaded** and **executed**.

Workflow for DAVTester:
1. **MKCOL** — create temporary directory (optional)
2. **PUT**    — upload language-specific test payloads
3. **MOVE** / **COPY** — bypass extension filters (optional)
4. **GET**    — execute & validate via regex
5. **Backdoor upload** if execution succeeded
6. **Cleanup** artefacts (optional)

The Python 3 rewrite of DAVTester adds: robust retry, rich progress bars, ncurses TUI, YAML test packs, JSON reporting.

**New in DavBest:** The **DavBest Integrity Sensor Module** enhances DavBests capabilities by providing in-situ integrity validation of host systems, particularly within containerized environments. It probes for unexpected system modifications and reports findings, rigorously testing host-container resource isolation policies.

---

## 2. License
```
GNU General Public License v3.0 or later
See LICENSE for full text.
```

---

## 3. Features

### DavTester (WebDAV Security Testing)

| Capability                              | v1.x (Perl) | v2.x (Python) |
|-----------------------------------------|:-----------:|:-------------:|
| Upload test payloads                    | ✅ | ✅ |
| MOVE / COPY extension bypass            | ✅ | ✅ |
| Backdoor auto-upload                    | ✅ | ✅ |
| Retry & back-off                        | ❌ | ✅ |
| Rich progress bars                      | ❌ | ✅ |
| ncurses TUI (npyscreen)                 | ❌ | ✅ |
| JSON reporting                          | ❌ | ✅ |
| Cross-platform                          | ⚠️ | ✅ |

### DavBest Integrity Sensor (Host Integrity Validation)
- **Host Path Probing:** Attempts to modify critical host system files (e.g., `/etc/passwd`, `/root/.ssh/authorized_keys`) to detect unexpected write permissions.
- **Container Isolation Testing:** Designed to operate from within containerized environments, providing insights into the effectiveness of host-container isolation.
- **Secure Logging:** Probe results are formatted as JSON, encrypted using AES-256-GCM (by the C sensor module), and output as hex-encoded strings to stdout.
- **Anomaly Detection:** The Python-based analysis framework processes these logs to identify and flag "CRITICAL_SUCCESS" events (i.e., unexpected successful writes) as integrity violations.
- **Framework for Posture Testing:** Provides a method to actively test host security posture from an "insider" (compromised/test container) perspective.
- **Automated Testing:** Includes scripts for setting up a Dockerized test environment and running end-to-end verification of the sensor-to-alert pipeline.

---

## 4. DavBest Integrity Sensor Module

### 4.1. Overview & Purpose
The DavBest Integrity Sensor Module is designed for in-situ integrity validation of host systems. It is particularly useful for testing resource isolation policies in containerized environments. The module works by attempting actions that *should* be denied (like writing to critical host paths). An unexpected success of such an attempt indicates a potential security vulnerability or misconfiguration.

### 4.2. Core Components
- **`OP_SDWAN/davbest_integration/davbest_sensor_core.c`:** A C module that performs the integrity probes. It attempts to append benign audit strings to predefined critical host files.
- **`OP_SDWAN/davbest_integration/davbest_sensor.so`:** The compiled shared library of the C sensor module, intended to be loaded via `LD_PRELOAD`.
- **`OP_SDWAN/davbest_integration/davbest_sensor_analysis_rules.py`:** A Python script that processes the logs generated by the sensor. It (conceptually) decrypts, parses, and analyzes these logs to identify anomalies.
- **`OP_SDWAN/davbest_integration/davbest_alert_manager.py`:** A Python script responsible for formatting and generating structured JSON alerts for critical findings identified by the analysis script.
- **Design & Test Documents:**
    - `OP_SDWAN/davbest_integration/davbest_sensor_module_design.md`
    - `OP_SDWAN/davbest_integration/davbest_sensor_deployment_plan.md`
    - `OP_SDWAN/davbest_integration/test_results/sensor_verification_report.md`
    - `OP_SDWAN/davbest_integration/test_results/final_end_to_end_verification_report.md`

### 4.3. Workflow
1. **Load & Execute:** `davbest_sensor.so` is loaded into a process (typically in a container) using the `LD_PRELOAD` mechanism. Its constructor function `run_integrity_scan()` executes automatically.
2. **Probe:** The sensor attempts to append to critical host files (e.g., `/host_root/etc/passwd`, `/host_root/etc/shadow`, `/host_root/root/.ssh/authorized_keys`) via various potential host mount points.
3. **Log & Encrypt:** The outcome of each probe (success or failure, expected or unexpected) is formatted as a JSON string. This JSON string is then encrypted using AES-256-GCM, and the resulting packet (Nonce + Ciphertext + Tag) is hex-encoded and printed to standard output.
4. **Capture:** Standard output from the container (containing these hex-encoded logs) is captured (e.g., using `docker logs`).
5. **Analyze:** `davbest_sensor_analysis_rules.py` reads the captured log file.
    - It (conceptually, for now) decrypts each log entry using a shared key.
    - It parses the decrypted JSON payload.
    - It identifies entries where `status` is "CRITICAL_SUCCESS" (an unexpected successful write).
6. **Alert:** For each "CRITICAL_SUCCESS", the analysis script calls `davbest_alert_manager.py` to generate a structured JSON alert, which is printed to standard output.

### 4.4. Compilation (`davbest_sensor.so`)
The C sensor module is compiled into a shared library using GCC and OpenSSL:
```bash
gcc -shared -o OP_SDWAN/davbest_integration/davbest_sensor.so OP_SDWAN/davbest_integration/davbest_sensor_core.c -fPIC -lssl -lcrypto -Wl,-z,relro,-z,now
```
**Dependencies:** `gcc`, OpenSSL development libraries (e.g., `libssl-dev` on Debian/Ubuntu).

### 4.5. Deployment & Execution
- **Primary Method:** Load `davbest_sensor.so` using the `LD_PRELOAD` environment variable within a Docker container.
- **Example Docker Setup:** The `OP_SDWAN/davbest_integration/test_env/` directory contains a `Dockerfile` and `docker-compose.yml` demonstrating how to build an image with the sensor and run it.
    - The `Dockerfile` copies `davbest_sensor.so` into the image and sets `LD_PRELOAD`.
    - `docker-compose.yml` (or `docker run` commands) mounts a mock host filesystem to `/host_root` inside the container for the sensor to probe.
- **Log Output:** The sensor logs to `stdout`. These logs are intended to be captured via the containers logging mechanism (e.g., `docker logs <container_id>`).

### 4.6. Alerting
- Alerts are generated by `davbest_alert_manager.py` when `davbest_sensor_analysis_rules.py` detects a "CRITICAL_SUCCESS" event.
- Alerts are currently output as JSON strings to `stdout`, prefixed with `DAVBEST_ALERT_JSON:`.
- The JSON alert structure includes: `alert_type`, `timestamp`, `source_system`, `severity`, `probe_target`, `probe_outcome`, `description`, and `remediation_guidance`.

### 4.7. Test Environment & Verification
- A comprehensive test setup is available in `OP_SDWAN/davbest_integration/test_env/`.
- An automated end-to-end test script, `OP_SDWAN/davbest_integration/run_end_to_end_test.sh`, orchestrates:
    1. Building the sensor Docker image.
    2. Running the container with a mock host filesystem (including a deliberately world-writable `/etc/passwd` for testing).
    3. Capturing sensor logs.
    4. Running the analysis script to process these logs and generate alerts.
- Successful execution of this script, detailed in `final_end_to_end_verification_report.md`, confirms the sensor-to-alert pipeline.

---

## 5. DavTester WebDAV Security Tool

This section details the original WebDAV testing component of DavBest.

### 5.1. Requirements (DavTester)
* Python ≥ 3.8
* `webdavclient3`, `requests`, `rich`, `pyyaml`, `npyscreen`
```bash
pip install webdavclient3 requests rich pyyaml npyscreen
```

### 5.2. Installation (DavTester)
```bash
git clone https://github.com/yourorg/davbest.git # Replace with actual repo URL
cd davbest
pip install -r requirements.txt # Assuming requirements.txt is updated or DavTester has its own
```

### 5.3. Usage (DavTester)

#### Command-line mode
```bash
python davtester.py -u https://host/webdav/dir -A user:pass --create-dir testDir --move --backdoors auto --cleanup
```

#### TUI menu mode
Simply run without arguments:
```bash
python davtester.py
```
An ncurses form collects options.

### 5.4. Tests & Backdoors (DavTester)
* **tests/** — YAML files named `php.yaml`, `aspx.yaml`, …
  * Fields: `content`, `execmatch` (regex)
* **backdoors/** — actual shells; must match a successful test extension.

`$$FILENAME$$` inside `content` is auto-replaced with the random session filename.

### 5.5. Examples (DavTester)
| Description | Command |
|-------------|---------|
| Basic upload test | `python davtester.py -u http://victim/dav/` |
| Test & drop shells automatically | `python davtester.py -u http://victim/dav/ --backdoors auto` | <!-- Corrected flag -->
| Authenticated upload of custom file | `python davtester.py -u https://victim/dav/ -A admin:pw --uploadfile backdoor.aspx --uploadloc shell.aspx` | <!-- Corrected flags -->

---

## 6. Roadmap / TODO

### DavTester
* NTLM / Negotiate authentication
* More language backdoors and tests
* COPY/MOVE auth headers
* Unit-test harness for new YAML packs

### DavBest Integrity Sensor
* **Implement Actual Decryption:** Replace simulated decryption in `davbest_sensor_analysis_rules.py` with actual AES-256-GCM decryption using a library like `cryptography`.
* **Key Management:** Develop a secure way to manage and distribute the AES key for the sensor and analysis script (avoid hardcoded/placeholder keys in production).
* **Expand Probe Types:** Introduce new probes beyond file appends (e.g., attempting to read sensitive files, execute commands, check network access, inspect system properties).
* **Configurable Targets:** Allow critical file paths and mount points to be configured dynamically.
* **Advanced Alerting:** Integrate `davbest_alert_manager.py` with actual alerting systems (SIEM, email, messaging platforms) instead of just printing to console.
* **Source Identification:** Improve `source_ip` / `source_system` identification in alerts (e.g., by querying container metadata if possible).

---

## 7. Changelog
**2.XXX (Recent Date) - DavBest Integrity Sensor Module Integration (Phases 1-3)**
* Added `davbest_sensor_core.c` for host integrity probing via file system write attempts.
* Developed `davbest_sensor_analysis_rules.py` for processing sensor logs (currently with simulated decryption).
* Created `davbest_alert_manager.py` for generating structured JSON alerts for critical findings.
* Implemented sensor compilation (`davbest_sensor.so`), a Docker-based test environment (`OP_SDWAN/davbest_integration/test_env/`), and an automated end-to-end test script (`run_end_to_end_test.sh`).
* Successfully demonstrated sensor execution, log capture (stdout from sensor, captured by Docker), and alert generation based on a mock writable host file.
* Key design documents and verification reports for the sensor module added to `OP_SDWAN/davbest_integration/`.

**2.1.0** (2025-04-19) — Python rewrite of DavTester, rich UI, npyscreen TUI
**1.2.x** — legacy Perl branch fixes

---

## 8. Credits
* **Chris Sullo** (author DavTester 1.0)
* **Paulino Calderón** (author DavTester 1.1)
* **RewardOne** – modern Python rewrite of DavTester
* Community contributors – see `AUTHORS.md` (if exists)
* SWORD - John - Version 2.0 (DavTester)
* **Jules (AI Agent)** - DavBest Integrity Sensor Module development (Phases 1-3)

---
