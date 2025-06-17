# DavBest Sensor Module: Compilation & Deployment Plan

## 1. Overview

This document outlines the strategy for compiling the `davbest_sensor_core.c` code into a shared library (`davbest_sensor.so`) and deploying it within monitored environments (primarily containerized systems) to perform integrity validation checks.

## 2. Compilation Process

The `davbest_sensor_core.c` module needs to be compiled into a shared object (`.so`) file that can be loaded by the dynamic linker.

### 2.1. Dependencies

The primary dependencies for compilation are:
- **C Compiler:** A standard C compiler like GCC (GNU Compiler Collection) or Clang.
- **OpenSSL Development Libraries:** Headers and libraries for OpenSSL (e.g., `libssl-dev` or `openssl-devel` package, depending on the Linux distribution) are required for the AES-256-GCM encryption functionality.

### 2.2. Conceptual Compilation Commands

The following commands are conceptual and may need adjustments based on the specific build environment and target architecture.

**For x86_64 Linux (Typical):**
```bash
# Ensure OpenSSL development libraries are installed
# e.g., on Debian/Ubuntu: sudo apt-get install libssl-dev
# e.g., on CentOS/RHEL: sudo yum install openssl-devel

gcc -shared -o davbest_sensor.so davbest_sensor_core.c -fPIC -lssl -lcrypto -Wl,-z,relro,-z,now
```
- `gcc`: The C compiler.
- `-shared`: Produces a shared object suitable for dynamic linking.
- `-o davbest_sensor.so`: Specifies the output filename.
- `davbest_sensor_core.c`: The input source file.
- `-fPIC`: Generate Position Independent Code, necessary for shared libraries.
- `-lssl -lcrypto`: Links against the OpenSSL libraries (SSL and Crypto components).
- `-Wl,-z,relro,-z,now`: Linker flags to enhance security (Read-Only Relocations, Full RELRO, and Bind Now). These are good practices for shared libraries.

**For ARM Architecture (e.g., aarch64):**
Compilation for ARM would require a cross-compiler if building on an x86_64 machine, or a native ARM build environment.

*Conceptual command using a cross-compiler (e.g., `aarch64-linux-gnu-gcc`):*
```bash
# Ensure OpenSSL development libraries for ARM are available in the cross-compilation sysroot
aarch64-linux-gnu-gcc -shared -o davbest_sensor_arm64.so davbest_sensor_core.c -fPIC -lssl -lcrypto -Wl,-z,relro,-z,now
```
The specific cross-compiler name and setup will vary.

### 2.3. Build Environment Considerations
- It's recommended to build the sensor in an environment that closely matches the target deployment environment to avoid ABI compatibility issues.
- Using a Docker container for building can help create a consistent and reproducible build process.

## 3. Deployment Strategies

The `davbest_sensor.so` library needs to be placed into the target (containerized) environment where it can be loaded by applications to initiate integrity scans.

### 3.1. Volume Mounting (Dynamic Deployment)

- **Description:** The `davbest_sensor.so` file can be placed on the host machine (or a shared volume) and mounted into the container at runtime.
- **Mechanism:**
    - Docker: `docker run -v /path/on/host/davbest_sensor.so:/path/in/container/davbest_sensor.so ...`
    - Kubernetes: Via `volumeMounts` and a corresponding `volume` definition (e.g., `hostPath`, `persistentVolumeClaim`).
- **Pros:**
    - Allows updating the sensor without rebuilding the container image.
    - Flexible for testing different sensor versions.
- **Cons:**
    - Requires orchestrator/runtime configuration.
    - The host path must be accessible and managed.

### 3.2. Integration into Container Image (Static Deployment)

- **Description:** The `davbest_sensor.so` file is copied directly into the container image during its build process.
- **Mechanism (Dockerfile example):**
```dockerfile
FROM base_application_image

# Prerequisites for the sensor (if any, though the .so should be self-contained with OpenSSL linked)
# RUN apt-get update && apt-get install -y libssl1.1 # or libssl3, etc. depending on linked version

# Copy the compiled sensor library into the image
COPY davbest_sensor.so /opt/davbest/davbest_sensor.so
# Ensure the directory is in the library search path or use an absolute path for LD_PRELOAD
ENV LD_LIBRARY_PATH=/opt/davbest:$LD_LIBRARY_PATH
```
- **Pros:**
    - Self-contained image, easier to distribute.
    - Versioning of the sensor is tied to the image version.
- **Cons:**
    - Updating the sensor requires rebuilding and redeploying the image.

## 4. Triggering Mechanisms for Integrity Scan

Once deployed, the `davbest_sensor.so` needs its `run_integrity_scan()` function (marked with `__attribute__((constructor))`) to be executed.

### 4.1. `LD_PRELOAD` Environment Variable

- **Description:** This is the primary intended method. The `LD_PRELOAD` environment variable can be used to instruct the dynamic linker to load the `davbest_sensor.so` library before any other library, including the main application. Since `run_integrity_scan()` is a constructor, it will execute automatically when the library is loaded.
- **Mechanism:**
    - **Docker:**
      ```bash
      docker run -e LD_PRELOAD=/opt/davbest/davbest_sensor.so ... my_application_image
      ```
      (Assuming `davbest_sensor.so` is at `/opt/davbest/davbest_sensor.so` within the container, either via volume mount or copied into the image).
    - **Kubernetes:**
      Set the `LD_PRELOAD` environment variable in the container spec:
      ```yaml
      apiVersion: v1
      kind: Pod
      metadata:
        name: my-app-with-sensor
      spec:
        containers:
        - name: my-app
          image: my_application_image
          env:
          - name: LD_PRELOAD
            value: "/opt/davbest/davbest_sensor.so" # Or path from volumeMount
          # ... other container settings ...
          # volumeMounts:
          # - name: sensor-volume
          #   mountPath: /opt/davbest/davbest_sensor.so # If using volume mount
      # volumes: # If using volume mount
      # - name: sensor-volume
      #   hostPath:
      #     path: /path/on/host/davbest_sensor.so
      ```
- **Framing:** "Initiating integrity scan during application startup via dynamic library preloading."
- **Considerations:**
    - The path to `davbest_sensor.so` must be correct and accessible within the container.
    - The application within the container must be dynamically linked for `LD_PRELOAD` to work effectively. Most standard applications are.
    - If the application changes its privileges (e.g., drops root), `LD_PRELOAD` might be subject to security restrictions (e.g., `AT_SECURE` flag).

### 4.2. Internal Application Calls (Advanced/Optional)

- **Description:** For more tightly integrated scenarios, the application itself could explicitly load and call a function within `davbest_sensor.so` using `dlopen()` and `dlsym()`. This would require modifying the application code.
- **Mechanism:**
    ```c
    // Example in application code
    // #include <dlfcn.h>
    // void *handle = dlopen("/opt/davbest/davbest_sensor.so", RTLD_LAZY);
    // if (handle) {
    //     void (*scan_func)() = dlsym(handle, "run_integrity_scan"); // Or a specific exported function
    //     if (scan_func) {
    //         scan_func();
    //     }
    //     dlclose(handle);
    // }
    ```
- **Framing:** "Initiating integrity scan via direct invocation from application logic."
- **Pros:** Finer control over when the scan occurs.
- **Cons:** Requires application modification; less transparent. The constructor-based approach with `LD_PRELOAD` is generally simpler for this module's design.

## 5. Security and Operational Notes

- **Permissions:** The sensor module will run with the permissions of the process it is loaded into. This is inherent to its design of testing the boundaries of those permissions.
- **Sensor Updates:** A clear process for updating `davbest_sensor.so` should be established, whether through image rebuilds or controlled updates to volume-mounted versions.
- **Logging Impact:** Ensure that the "stdout" logging from the sensor (the hex-encoded encrypted messages) is captured by the container's logging mechanism (e.g., Docker logs, Kubernetes pod logs) so it can be forwarded to the DavBest event ingestion system.

This plan provides a conceptual framework. Specific implementation details will depend on the chosen container orchestration platform and application architecture.
```
