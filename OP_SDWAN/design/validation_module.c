#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h> // For access() and syscalls if needed
#include <errno.h>  // For errno
#include <time.h>   // For timestamps
#include <sys/stat.h> // For mkdir

// Assume OpenSSL is available for AES-GCM.
// These includes would be needed for actual compilation.
#include <openssl/evp.h>
#include <openssl/rand.h>

// --- Configuration & Globals ---
// Key should ideally be fetched securely, not hardcoded directly in final version.
// For this design, we'll use a placeholder. This MUST match the key used by the receiver.
// This is a 32-byte key.
unsigned char aes_key[32] = "0123456789abcdef0123456789abcdef"; // Placeholder - REPLACE

// Receiver details (conceptual - how logs are sent)
#define RECEIVER_IP "127.0.0.1" // Example IP for event_receiver_core.py
#define RECEIVER_PORT 12345     // Example Port

const char* host_mount_points[] = {"/host_root", "/mnt/host", "/"}; // Include / for direct access if container shares host FS
const int num_host_mount_points = sizeof(host_mount_points) / sizeof(host_mount_points[0]);

const char* critical_files[] = {
    "root/.ssh/authorized_keys",
    "etc/passwd",
    "etc/shadow"
};
const int num_critical_files = sizeof(critical_files) / sizeof(critical_files[0]);

// --- Helper Functions ---

// (Conceptual) Sends an encrypted log message.
// In a real implementation, this would handle AES-GCM encryption and network transmission.
void send_encrypted_log(const char *log_message_json) {
    // 1. Get AES Key (ensure it's the correct one)
    // 2. Generate 12-byte nonce.
    // 3. Encrypt `log_message_json` using AES-256-GCM (e.g., with OpenSSL's EVP_AEAD API).
    //    - Nonce: 12 bytes
    //    - Tag: 16 bytes (appended by AES-GCM)
    //    - Ciphertext
    // 4. Form a packet: nonce (12 bytes) + ciphertext_with_tag.
    // 5. Send packet to RECEIVER_IP:RECEIVER_PORT via UDP/TCP.
    //    (Using printf as a placeholder for actual network send and encryption)
    printf("LOG_TO_RECEIVER (encrypted): %s\n", log_message_json);
    // Actual implementation would involve socket programming and OpenSSL.
}

// Generates a JSON formatted log message
void format_and_send_log(const char *action, const char *target_file, const char *status, const char *details, int err_code) {
    char json_buffer[1024];
    char timestamp[64];
    time_t now = time(NULL);
    struct tm *gmt_time = gmtime(&now); // Use gmtime for UTC

    // Ensure gmtime result is not NULL before using it
    if (gmt_time == NULL) {
        // Handle error, perhaps by logging a simple message or using a fixed timestamp
        strcpy(timestamp, "1970-01-01T00:00:00Z"); // Fallback timestamp
    } else {
        strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", gmt_time);
    }


    snprintf(json_buffer, sizeof(json_buffer),
             "{ \"timestamp\": \"%s\", \"module\": \"validation_module\", \"action\": \"%s\", \"target\": \"%s\", \"status\": \"%s\", \"details\": \"%s\", \"errno\": %d }",
             timestamp, action, target_file, status, details, err_code);
    send_encrypted_log(json_buffer);
}

// Attempts to append a string to a file.
void attempt_append_to_file(const char *base_path, const char *file_rel_path) {
    char full_path[512];
    snprintf(full_path, sizeof(full_path), "%s/%s", base_path, file_rel_path);

    // Benign audit string
    char audit_string[256];
    time_t now_ts = time(NULL);
    char time_buffer[64];

    // Format time without newline from ctime
    struct tm *current_local_time = localtime(&now_ts);
    if (current_local_time == NULL) {
        strcpy(time_buffer, "timestamp_error");
    } else {
        strftime(time_buffer, sizeof(time_buffer), "%Y-%m-%d %H:%M:%S", current_local_time);
    }

    snprintf(audit_string, sizeof(audit_string), "\n# Audit: validation_module write attempt at %s\n", time_buffer);
    // audit_string[strcspn(audit_string, "\n")] = 0; // ctime adds newline, strftime does not if format string is correct.

    FILE *fp = fopen(full_path, "a");
    if (fp) {
        fputs(audit_string, fp);
        fclose(fp);
        format_and_send_log("APPEND_ATTEMPT", full_path, "SUCCESS", "Appended audit string.", 0);

        // Conceptual: Attempt to remove the benign string (very difficult to do reliably)
        // For this design, we'll skip reliable removal. A real module might need a more complex strategy.
    } else {
        format_and_send_log("APPEND_ATTEMPT", full_path, "FAILURE", "Failed to open/append.", errno);
    }
}

// Conceptual: Function to attempt removing ld.so.preload entry (highly privileged)
void attempt_remove_preload_entry() {
    // This is extremely difficult to do from within a preloaded library itself
    // and typically requires external process intervention or specific system states.
    // For this design, it's a conceptual placeholder.
    // A real implementation might try to rename /etc/ld.so.preload temporarily if it has perms,
    // or rely on an external script.
    const char* preload_path_segment = "etc/ld.so.preload";

    for (int i = 0; i < num_host_mount_points; ++i) {
        char full_preload_path[512];
        // Ensure no double slashes if mount_point is "/"
        if (strcmp(host_mount_points[i], "/") == 0) {
            snprintf(full_preload_path, sizeof(full_preload_path), "/%s", preload_path_segment);
        } else {
            snprintf(full_preload_path, sizeof(full_preload_path), "%s/%s", host_mount_points[i], preload_path_segment);
        }

        if (access(full_preload_path, F_OK) == 0) {
             format_and_send_log("CLEANUP_PRELOAD", full_preload_path, "INFO", "ld.so.preload found. Conceptual removal attempt.", 0);
             // Actual removal logic would be complex and permission-dependent.
             // e.g., if (remove(full_preload_path) == 0) { ... } else { ... }
             break;
        }
    }
}


// --- Main Module Logic ---
// Using a constructor function to run when the library is loaded.
__attribute__((constructor))
void on_load() {
    // Create reports directory if it doesn't exist (conceptual for host)
    // This part is more for logging from the module itself if it were writing local files,
    // rather than for the analyzer script. The analyzer ensures its own report dir.
    // For a shared library, mkdir might not be its primary concern unless explicitly designed.

    format_and_send_log("MODULE_LOAD", "validation_module.so", "SUCCESS", "Module loaded via ld.so.preload.", 0);

    for (int i = 0; i < num_host_mount_points; ++i) {
        const char *current_mount = host_mount_points[i];
        // Check if mount point itself is accessible (rudimentary check)
        if (access(current_mount, R_OK) != 0) {
            format_and_send_log("MOUNT_ACCESS_CHECK", current_mount, "SKIPPING", "Mount point not accessible or does not exist.", errno);
            continue;
        }
        format_and_send_log("MOUNT_ACCESS_CHECK", current_mount, "INFO", "Processing mount point.", 0);

        for (int j = 0; j < num_critical_files; ++j) {
            attempt_append_to_file(current_mount, critical_files[j]);
        }
    }

    // Conceptual: Attempt cleanup
    attempt_remove_preload_entry(); // Log attempt

    format_and_send_log("MODULE_UNLOAD_PENDING", "validation_module.so", "INFO", "Module finished execution, cleanup attempted.", 0);
    // Actual unload cleanup (like removing itself from ld.so.preload) is complex.
}

// Note: A destructor __attribute__((destructor)) could also be used,
// but cleanup of ld.so.preload is tricky from within the loaded lib.
