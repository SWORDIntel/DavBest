#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <time.h>
#include <sys/stat.h> // For mkdir, though not strictly used by sensor core directly

// OpenSSL headers
#include <openssl/evp.h>
#include <openssl/rand.h>
#include <openssl/err.h>

// --- Configuration & Globals ---
// IMPORTANT: This key is a placeholder for development and design.
// In a real-world scenario, this key MUST be managed securely and not hardcoded.
// It should match the key used by the DavBest event receiver.
unsigned char aes_key[32] = "0123456789abcdef0123456789abcdef"; // 32-byte key

// Receiver details (conceptual - actual network transmission is not implemented here)
// The encrypted logs will be printed to stdout in a specific format.
// const char* RECEIVER_IP = "127.0.0.1"; // Placeholder
// const int RECEIVER_PORT = 12345;      // Placeholder

// Host mount points to check
const char* host_mount_points[] = {"/host_root", "/mnt/host", "/"}; // Order of check can be important
const int num_host_mount_points = sizeof(host_mount_points) / sizeof(host_mount_points[0]);

// Critical files for integrity probes (relative to mount points)
const char* critical_files[] = {
    "root/.ssh/authorized_keys",
    "etc/passwd",
    "etc/shadow"
    // Add more critical files if needed
};
const int num_critical_files = sizeof(critical_files) / sizeof(critical_files[0]);

#define MAX_LOG_JSON_SIZE 1024
#define AES_GCM_NONCE_SIZE 12
#define AES_GCM_TAG_SIZE 16

// --- Forward Declarations ---
void format_and_send_log(const char *probe_type, const char *target_file, const char *status, const char *details, int err_code);
int encrypt_and_prepare_packet(const unsigned char *plaintext_json, unsigned char *output_packet, int *output_packet_len);
void perform_probe(const char *base_host_path, const char *file_relative_path);
void module_cleanup();
void handle_openssl_errors(void);

// --- Helper Functions ---

void handle_openssl_errors(void) {
    // Simple OpenSSL error printing. In a real module, might log to a fallback local file.
    fprintf(stderr, "OpenSSL Error: ");
    ERR_print_errors_fp(stderr);
    fprintf(stderr, "\n");
}

// Prepares a log packet: [12-byte Nonce][Ciphertext][16-byte Auth Tag]
// and "sends" it (prints to stdout as hex for this conceptual implementation).
int encrypt_and_prepare_packet(const unsigned char *plaintext_json, unsigned char *output_packet_buffer, int *output_packet_len) {
    EVP_CIPHER_CTX *ctx;
    int len;
    int ciphertext_len;
    unsigned char nonce[AES_GCM_NONCE_SIZE];
    unsigned char tag[AES_GCM_TAG_SIZE];

    // 1. Generate random Nonce
    if (!RAND_bytes(nonce, sizeof(nonce))) {
        fprintf(stderr, "ERROR: RAND_bytes for nonce failed\n");
        handle_openssl_errors();
        return 0; // Failure
    }

    // 2. Create and initialize the context
    if (!(ctx = EVP_CIPHER_CTX_new())) {
        fprintf(stderr, "ERROR: EVP_CIPHER_CTX_new failed\n");
        handle_openssl_errors();
        return 0; // Failure
    }

    // 3. Initialize encryption operation: AES-256-GCM
    if (1 != EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL)) {
        fprintf(stderr, "ERROR: EVP_EncryptInit_ex (cipher) failed\n");
        EVP_CIPHER_CTX_free(ctx);
        handle_openssl_errors();
        return 0; // Failure
    }

    // 4. Set IV (Nonce) length (GCM default is 12 bytes)
    if (1 != EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, sizeof(nonce), NULL)) {
        fprintf(stderr, "ERROR: EVP_CIPHER_CTX_ctrl (IV len) failed\n");
        EVP_CIPHER_CTX_free(ctx);
        handle_openssl_errors();
        return 0; // Failure
    }

    // 5. Initialize key and IV (Nonce)
    if (1 != EVP_EncryptInit_ex(ctx, NULL, NULL, aes_key, nonce)) {
        fprintf(stderr, "ERROR: EVP_EncryptInit_ex (key/IV) failed\n");
        EVP_CIPHER_CTX_free(ctx);
        handle_openssl_errors();
        return 0; // Failure
    }

    // 6. Provide message to be encrypted, and obtain encrypted output.
    // EVP_EncryptUpdate can be called multiple times if necessary
    if (1 != EVP_EncryptUpdate(ctx, output_packet_buffer + AES_GCM_NONCE_SIZE, &len, plaintext_json, strlen((const char*)plaintext_json))) {
        fprintf(stderr, "ERROR: EVP_EncryptUpdate failed\n");
        EVP_CIPHER_CTX_free(ctx);
        handle_openssl_errors();
        return 0; // Failure
    }
    ciphertext_len = len;

    // 7. Finalize encryption: Any remaining ciphertext specific to GCM mode.
    // Note: GCM mode does not typically produce output here with OpenSSL's default padding (which is none for GCM).
    if (1 != EVP_EncryptFinal_ex(ctx, output_packet_buffer + AES_GCM_NONCE_SIZE + ciphertext_len, &len)) {
        fprintf(stderr, "ERROR: EVP_EncryptFinal_ex failed\n");
        EVP_CIPHER_CTX_free(ctx);
        handle_openssl_errors();
        return 0; // Failure
    }
    ciphertext_len += len;

    // 8. Get the Authentication Tag
    if (1 != EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, AES_GCM_TAG_SIZE, tag)) {
        fprintf(stderr, "ERROR: EVP_CIPHER_CTX_ctrl (get tag) failed\n");
        EVP_CIPHER_CTX_free(ctx);
        handle_openssl_errors();
        return 0; // Failure
    }

    // 9. Clean up context
    EVP_CIPHER_CTX_free(ctx);

    // 10. Construct the packet: [Nonce][Ciphertext][Tag]
    memcpy(output_packet_buffer, nonce, AES_GCM_NONCE_SIZE);
    // Ciphertext is already in place: output_packet_buffer + AES_GCM_NONCE_SIZE
    memcpy(output_packet_buffer + AES_GCM_NONCE_SIZE + ciphertext_len, tag, AES_GCM_TAG_SIZE);

    *output_packet_len = AES_GCM_NONCE_SIZE + ciphertext_len + AES_GCM_TAG_SIZE;

    return 1; // Success
}

// Formats a log message as JSON and "sends" it (via encrypt_and_prepare_packet).
// For this conceptual module, "sending" means printing the hex representation of the encrypted packet to stdout.
void format_and_send_log(const char *probe_type, const char *target_file, const char *status, const char *details, int err_code) {
    char json_buffer[MAX_LOG_JSON_SIZE];
    char timestamp[64];
    time_t now = time(NULL);
    struct tm *gmt_time = gmtime(&now);

    if (gmt_time == NULL) {
        strcpy(timestamp, "1970-01-01T00:00:00Z"); // Fallback
    } else {
        strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", gmt_time);
    }

    snprintf(json_buffer, sizeof(json_buffer),
             "{ \"timestamp\": \"%s\", \"module\": \"DavBestSensorModule\", \"probe_type\": \"%s\", \"target\": \"%s\", \"status\": \"%s\", \"details\": \"%s\", \"errno\": %d }",
             timestamp, probe_type, target_file ? target_file : "N/A", status, details, err_code);

    unsigned char encrypted_packet_buffer[AES_GCM_NONCE_SIZE + MAX_LOG_JSON_SIZE + EVP_MAX_BLOCK_LENGTH + AES_GCM_TAG_SIZE];
    int encrypted_packet_len = 0;

    if (encrypt_and_prepare_packet((const unsigned char *)json_buffer, encrypted_packet_buffer, &encrypted_packet_len)) {
        // "Send" by printing hex representation of Nonce + Ciphertext + Tag
        printf("DAVBEST_ENCRYPTED_LOG_HEX: ");
        for (int i = 0; i < encrypted_packet_len; i++) {
            printf("%02x", encrypted_packet_buffer[i]);
        }
        printf("\n");
    } else {
        // Fallback for encryption failure: print plaintext to stderr (for diagnostics)
        fprintf(stderr, "CRITICAL_ERROR: Encryption failed. Log data (plaintext): %s\n", json_buffer);
    }
}

// Performs an integrity probe by attempting to append to a file.
void perform_probe(const char *base_host_path, const char *file_relative_path) {
    char full_path[512];
    snprintf(full_path, sizeof(full_path), "%s/%s", base_host_path, file_relative_path);

    // Benign audit string
    char audit_string[256];
    time_t now_ts = time(NULL);
    char time_buffer[64];
    struct tm *current_local_time = localtime(&now_ts);
    if (current_local_time == NULL) {
        strcpy(time_buffer, "timestamp_error");
    } else {
        strftime(time_buffer, sizeof(time_buffer), "%Y-%m-%d %H:%M:%S (UTC %z)");
    }
    snprintf(audit_string, sizeof(audit_string), "\n# DavBest Integrity Probe: Write attempt at %s by DavBestSensorModule\n", time_buffer);

    FILE *fp = fopen(full_path, "a");
    if (fp) {
        fputs(audit_string, fp);
        // It's good practice to check ferror and fflush before closing,
        // but for this conceptual module, we'll keep it simpler.
        fclose(fp);
        // THIS IS AN ANOMALY!
        format_and_send_log("FILE_WRITE_ATTEMPT", full_path, "CRITICAL_SUCCESS", "Host path modification was unexpectedly permitted.", 0);

        // Conceptual: Attempt to remove the benign string.
        // This is complex to do reliably (e.g., need original file size, race conditions).
        // For this version, we are not implementing a reliable removal.
        // A real module might log the success and leave the string, or use more advanced techniques.
    } else {
        // This is the EXPECTED outcome.
        format_and_send_log("FILE_WRITE_ATTEMPT", full_path, "EXPECTED_FAILURE", "Host path modification denied as expected.", errno);
    }
}

// Conceptual: Cleanup actions for the module.
void module_cleanup() {
    // 1. Remove temporary files:
    //    This module, as designed, doesn't create uniquely named temporary files that it
    //    can easily track and remove. The audit strings are appended.
    //    If it created, e.g., /tmp/davbest_sensor.pid, it would remove it here.
    format_and_send_log("MODULE_LIFECYCLE", "N/A", "INFO", "Conceptual: No temporary files to remove in this version.", 0);

    // 2. Attempt to remove ld.so.preload entry:
    //    This is extremely difficult and often impossible for a preloaded library to do to itself.
    //    It typically requires external intervention or very specific (usually elevated) permissions
    //    to modify /etc/ld.so.preload.
    //    We log the intent.
    const char* preload_path_segment = "etc/ld.so.preload"; // Path relative to a mount
    char full_preload_path_attempt[512];
    int found_preload = 0;

    for (int i = 0; i < num_host_mount_points; ++i) {
        // Construct path carefully to avoid double slashes if mount_point is "/"
        if (strcmp(host_mount_points[i], "/") == 0 && preload_path_segment[0] == '/') {
             snprintf(full_preload_path_attempt, sizeof(full_preload_path_attempt), "%s", preload_path_segment);
        } else if (strcmp(host_mount_points[i], "/") == 0 ) {
             snprintf(full_preload_path_attempt, sizeof(full_preload_path_attempt), "/%s", preload_path_segment);
        }
        else {
            snprintf(full_preload_path_attempt, sizeof(full_preload_path_attempt), "%s/%s", host_mount_points[i], preload_path_segment);
        }

        if (access(full_preload_path_attempt, F_OK) == 0) {
            // Found a candidate for ld.so.preload
            // Actual removal: remove(full_preload_path_attempt); // Requires permissions
            format_and_send_log("MODULE_LIFECYCLE", full_preload_path_attempt, "INFO", "Conceptual ld.so.preload removal attempt at path.", 0);
            found_preload = 1;
            // break; // Assuming only one relevant ld.so.preload, or attempt all found
        }
    }
    if (!found_preload) {
        format_and_send_log("MODULE_LIFECYCLE", "/etc/ld.so.preload", "INFO", "Conceptual ld.so.preload removal: path not found under checked mounts.", 0);
    }
}

// --- Main Module Logic ---
// This function will be called when the library is loaded (e.g., via LD_PRELOAD).
__attribute__((constructor))
void run_integrity_scan() {
    // Initialize OpenSSL library functions (load error strings, etc.)
    // Not strictly necessary for all OpenSSL versions/builds but good practice.
    OpenSSL_add_all_algorithms(); // Deprecated in OpenSSL 3.0, but common in older examples
    ERR_load_crypto_strings();

    format_and_send_log("MODULE_LIFECYCLE", "DavBestSensorModule.so", "INFO", "Module loaded, starting integrity scan.", 0);

    for (int i = 0; i < num_host_mount_points; ++i) {
        const char *current_mount = host_mount_points[i];
        // Basic check if the mount point itself is accessible/readable.
        // More sophisticated checks might be needed for certain mount types.
        if (access(current_mount, R_OK) != 0) {
            // Log this, but don't send it as an encrypted packet if basic filesystem utils aren't working
            // Or, if logging is absolutely critical, try to send it anyway.
            // For now, we'll log it as an attempt.
             format_and_send_log("MOUNT_ACCESS_CHECK", current_mount, "SKIPPING", "Mount point not accessible or does not exist.", errno);
            continue; // Skip to next mount point
        }
        format_and_send_log("MOUNT_ACCESS_CHECK", current_mount, "INFO", "Processing mount point for integrity probes.", 0);

        for (int j = 0; j < num_critical_files; ++j) {
            perform_probe(current_mount, critical_files[j]);
        }
    }

    module_cleanup();

    format_and_send_log("MODULE_LIFECYCLE", "DavBestSensorModule.so", "INFO", "Integrity scan complete, cleanup attempted. Module shutting down.", 0);

    // Clean up OpenSSL (if it was initialized)
    // EVP_cleanup(); // Deprecated in OpenSSL 3.0
    // ERR_free_strings(); // Also part of OpenSSL cleanup
}

// Destructor (optional, for cleanup if needed on unload)
// __attribute__((destructor))
// void on_unload() {
//     // Perform any final cleanup if run_integrity_scan doesn't cover it
//     // or if the library is unloaded unexpectedly.
// }

// For testing purposes: main function to allow direct execution
// This would not typically be part of a .so used with LD_PRELOAD
/*
int main() {
    printf("DavBest Sensor Core Module: Direct Execution Test\n");
    run_integrity_scan();
    printf("DavBest Sensor Core Module: Direct Execution Test Complete\n");
    return 0;
}
*/
