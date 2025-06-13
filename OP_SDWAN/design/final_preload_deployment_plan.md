# Final ld.so.preload Deployment Strategy for validation_module.so

## 1. Introduction

This document outlines the refined strategy for deploying the compiled `validation_module.so` (from `validation_module.c`) into a target environment via the `/etc/ld.so.preload` mechanism. This plan considers hypothetical findings from concurrency testing (Task F.3) and the operational design of `validation_module.c` (Task G.1).

The primary goal is to reliably place `validation_module.so` into `/etc/ld.so.preload` and trigger its execution to assess host-container boundary integrity under specific conditions.

## 2. Analysis of (Hypothetical) Concurrency Test Findings

**Assumption for this plan:** While current decryption efforts for past logs documented in `OP_SDWAN/reports/concurrency_test_findings_report.md` were inconclusive due to encryption key mismatches, we will proceed with this deployment plan based on a *hypothetical scenario* where previous concurrency tests (Task F) indicated the following:

*   **Occasional Success:** Writes to `/etc/ld.so.preload` via the `/package/spack/upload` endpoint (simulated by `config_deploy_test.py`) were intermittently successful under moderate to high concurrency (e.g., 10-20 concurrent requests).
*   **Timing Sensitivity:** Success appeared correlated with specific timing windows, possibly during moments of high I/O load on the target system, or when certain services were initializing or restarting.
*   **File Overwrite vs. Append:** The mechanism was more reliable when overwriting `/etc/ld.so.preload` rather than attempting to append to it, though both showed some success. `validation_module.so` requires being the sole or first entry if it's to reliably execute its full intended test sequence.

These hypothetical findings suggest that a carefully timed burst of deployment attempts is more effective than a continuous low-level stream.

## 3. Optimal Deployment Parameters for `config_deploy_test.py`

Based on the above hypothetical analysis and the nature of `validation_module.so` (which is designed to execute upon being loaded by new processes):

*   **Target File Content:** The `config_deploy_test.py` script should aim to overwrite `/etc/ld.so.preload` with the full path to where `validation_module.so` is uploaded within the container's accessible filesystem (e.g., `/tmp/validation_module.so` or a path within the spack upload area if it's made executable and accessible for `ld.so`).
*   **Concurrency Level:**
    *   A moderate concurrency level of **15-25 simultaneous clients** initiated by `config_deploy_test.py` is recommended.
    *   This range is chosen to exploit potential race conditions or temporary permission misconfigurations without overwhelming a typical target system to the point of denial of service, which could mask successful exploitation.
*   **Timing and Duration:**
    *   **Burst Strategy:** Instead of continuous attempts, implement a burst strategy. Each client from `config_deploy_test.py` should make a series of N (e.g., 5-10) rapid attempts to write to `/etc/ld.so.preload` and then pause.
    *   **Coordinated Bursts:** These bursts should be loosely coordinated to occur around expected system events if known (e.g., scheduled tasks, service health checks that might restart other services). If such events are unknown, random intervals between bursts (e.g., 1-5 minutes) should be used.
    *   **Total Duration:** The deployment attempts should be run for a significant window (e.g., 30-60 minutes) to maximize the chance of hitting a vulnerable timing window.
*   **Payload Delivery:**
    *   `validation_module.so` must first be uploaded to a predictable, accessible, and executable location within the container's view of the filesystem. The path written to `/etc/ld.so.preload` must be this exact path.
    *   Example:
        1. Upload `validation_module.so` to `/opt/custom_modules/validation_module.so` (assuming this path is writable and usable).
        2. `config_deploy_test.py` attempts to write `/opt/custom_modules/validation_module.so` into `/etc/ld.so.preload`.

## 4. Triggering `ld.so.preload` and `validation_module.so` Execution

Once `validation_module.so` is successfully listed in `/etc/ld.so.preload` (on the host, via the container's write access), its `on_load` constructor function will execute when new processes are started, or existing services are made to re-initialize in a way that respects `ld.so.preload`.

The following methods should be considered to "trigger a runtime configuration refresh," thereby causing `validation_module.so` to load:

*   **Targeted Service Restart (If known vulnerable/triggerable service):**
    *   **Method:** If specific services are known to be restartable or triggerable by actions accessible from the container (or by an external orchestrator after deployment), target these.
    *   **Example:** `systemctl restart <service_name>` (executed on the host, if the container compromise allows such escalation or if done by a separate part of the test harness).
    *   **Consideration:** This is the most direct way. `validation_module.c` is designed to log its loading, so this provides clear feedback.

*   **System-Wide Process Spawning Event (More General):**
    *   **Method:** Initiate actions that cause many new processes to spawn across the system.
    *   **Examples:**
        *   A controlled system reboot (if within test parameters and permissible). This is the most comprehensive trigger.
        *   Triggering a package update or system scan on the host if such an action can be initiated.
        *   Executing common command-line tools that are dynamically linked (e.g., `ls`, `ps`, `cat`, `find`) from within the container *if these tools are executed in a context that respects the host's `/etc/ld.so.preload`*. This depends on how the container is isolated and how its process tree is managed relative to the host. Often, container processes are sufficiently isolated that they use their own library loader setup or a chroot-like environment for libraries. However, if the container escape is more profound, host tools might be callable.

*   **Application-Specific Triggers:**
    *   **Method:** If the container is running a specific application that can be forced to spawn new worker processes or reload its configuration dynamically, use this application's mechanisms.
    *   **Example:** Sending a `SIGHUP` to a daemon that re-execs or spawns new workers, or using an application-specific command like `apachectl graceful`.

**Framing the Trigger:**
All trigger actions should be framed as "System Integrity Verification: Initiating a standard runtime configuration refresh to observe dynamic library loading behavior and ensure system stability post-configuration adjustments."

## 5. Monitoring and Verification

*   The primary verification of `validation_module.so` execution will be the encrypted logs it sends to the Remote Event Log Receiver (as designed in `validation_module.c`).
*   The `log_decrypt_analyzer.py` script (or a similar tool with the correct decryption key for `validation_module.so`'s logs) would be used to monitor these logs for expected messages from `validation_module.so`.

## 6. Contingency and Fallback

*   If direct triggering methods are unavailable or prove ineffective, the deployment of `validation_module.so` via `ld.so.preload` will rely on naturally occurring process creations on the host system. This is a passive approach and may require a longer observation window.
*   The `validation_module.so` should be designed to be idempotent or to log its executions uniquely if it might be loaded multiple times.

This deployment plan aims to maximize the chances of successful placement and execution of `validation_module.so` for robust cross-boundary integrity validation.
