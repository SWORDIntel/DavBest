import os
import json
import sys
import subprocess
import datetime

# Adjust sys.path to allow importing from the root 'event_receiver' directory
# The script is in OP_SDWAN/tools/. We need to add the repository root to sys.path.
current_script_dir = os.path.dirname(os.path.abspath(__file__)) # OP_SDWAN/tools
op_sdwan_dir = os.path.dirname(current_script_dir) # OP_SDWAN
repo_root_dir = os.path.dirname(op_sdwan_dir) # Repository Root

if repo_root_dir not in sys.path:
    sys.path.insert(0, repo_root_dir)

try:
    from event_receiver.encryption_utils import decrypt_log_entry, ENCRYPTION_KEY
except ImportError as e:
    print(f"CRITICAL ERROR: Could not import from root 'event_receiver.encryption_utils': {e}", file=sys.stderr)
    print("Ensure the script is run from a location where OP_SDWAN/tools/ is valid, and the root 'event_receiver' directory is present.", file=sys.stderr)
    sys.exit(1)

def find_log_files(log_dir_path):
    """Returns a list of full paths to .enc_log files in log_dir_path using shell commands."""
    if not os.path.isdir(log_dir_path):
        print(f"Error: Log directory '{log_dir_path}' not found for shell command.", file=sys.stderr)
        return []
    found_log_files = []
    try:
        ls_process = subprocess.run(['ls', log_dir_path], capture_output=True, text=True, check=False)
        if ls_process.returncode != 0:
            print(f"Error running 'ls' in '{log_dir_path}': {ls_process.stderr}", file=sys.stderr)
            return []
        ls_output = ls_process.stdout
    except Exception as e:
        print(f"Exception running 'ls' for directory '{log_dir_path}': {e}", file=sys.stderr)
        return []
    try:
        grep_pattern = r'\.enc\.log$'
        grep_command = ['grep', '-E', grep_pattern]
        grep_process = subprocess.run(grep_command, input=ls_output, capture_output=True, text=True, check=False)
        if grep_process.returncode > 1:
            print(f"Error running 'grep' (command: '{' '.join(grep_command)}'): {grep_process.stderr}", file=sys.stderr)
            return []
        grep_output = grep_process.stdout
    except Exception as e:
        print(f"Exception running 'grep' (command: '{' '.join(grep_command)}'): {e}", file=sys.stderr)
        return []
    if grep_output:
        raw_filenames = grep_output.strip().split('\n')
        for raw_filename in raw_filenames:
            filename = raw_filename.strip()
            if filename:
                full_path = os.path.join(log_dir_path, filename)
                found_log_files.append(full_path)
    return found_log_files

def decrypt_and_parse_log(file_path, key):
    """
    Reads, decrypts, and parses a log file.
    Returns a tuple: (success_status: bool, result: object).
    If successful, (True, parsed_json_data).
    If decryption fails, (False, "Decryption failed: <error_message>").
    If JSON parsing fails, (False, "JSON parsing failed: <error_message>").
    """
    try:
        with open(file_path, 'rb') as f:
            encrypted_content = f.read()

        decrypted_content = decrypt_log_entry(encrypted_content, key)

        try:
            parsed_data = json.loads(decrypted_content)
            return True, parsed_data
        except json.JSONDecodeError as e:
            error_msg = f"JSON parsing failed: {e}"
            print(f"Error for {file_path}: {error_msg}", file=sys.stderr)
            return False, error_msg

    except ValueError as e: # Includes InvalidTag from decrypt_log_entry
        error_msg = f"Decryption failed: {e}"
        print(f"Error for {file_path}: {error_msg}", file=sys.stderr)
        return False, error_msg
    except FileNotFoundError:
        error_msg = "File not found"
        print(f"Error for {file_path}: {error_msg}", file=sys.stderr)
        return False, error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        print(f"Error for {file_path}: {error_msg}", file=sys.stderr)
        return False, error_msg

def analyze_log_data(log_data, file_path):
    """
    Analyzes parsed log data for specific strings.
    Returns a list of findings (strings).
    """
    findings = []
    if log_data is None: # Should not happen if called after successful parse
        return findings
    try:
        data_to_search = json.dumps(log_data)
    except TypeError:
        data_to_search = str(log_data)

    if "TEST_CONFIG_LOADED" in data_to_search: # Target string
        findings.append(f"Found 'TEST_CONFIG_LOADED' in {os.path.basename(file_path)}") # Report basename for brevity
    return findings

def generate_markdown_report(findings, report_path, processed_files, successful_decrypts, failed_decrypts_info):
    """Generates a Markdown report from the analysis results."""
    report_content = []
    report_content.append("# Concurrency Test Findings Report")
    report_content.append(f"\n_Report generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')}_\n")

    report_content.append("## Summary")
    report_content.append(f"- Total files processed: {processed_files}")
    report_content.append(f"- Files successfully decrypted and parsed: {successful_decrypts}")
    report_content.append(f"- Files failed to decrypt/parse: {len(failed_decrypts_info)}")
    report_content.append(f"- Occurrences of 'TEST_CONFIG_LOADED': {len(findings)}")

    report_content.append("\n## Detailed Findings ('TEST_CONFIG_LOADED' occurrences)")
    if findings:
        for finding_detail in findings: # finding_detail is already a string like "Found 'X' in Y"
            report_content.append(f"- {finding_detail}")
    else:
        report_content.append("- No instances of 'TEST_CONFIG_LOADED' (unexpected success for /etc/ld.so.preload) were found in the processed logs.")

    report_content.append("\n## Decryption/Parsing Failures")
    if failed_decrypts_info:
        for file_path, error_msg in failed_decrypts_info:
            report_content.append(f"- **{os.path.basename(file_path)}**: {error_msg}")
    else:
        report_content.append("- No files failed decryption or parsing.")

    try:
        # Ensure the report directory exists
        report_dir = os.path.dirname(report_path)
        if not os.path.exists(report_dir):
            os.makedirs(report_dir)
            print(f"Created report directory: {report_dir}")

        with open(report_path, 'w') as f:
            f.write("\n".join(report_content))
        print(f"Report generated successfully at: {report_path}")
    except IOError as e:
        print(f"Error writing report to {report_path}: {e}", file=sys.stderr)


def main():
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    log_directory = os.path.join(current_script_dir, "..", "..", "test_logs")

    if isinstance(ENCRYPTION_KEY, bytes):
        key_hex = ENCRYPTION_KEY.hex()
        print(f"Using encryption key (hex): {key_hex}")
    else:
        print(f"CRITICAL ERROR: ENCRYPTION_KEY from module was not bytes. Type: {type(ENCRYPTION_KEY)}", file=sys.stderr)
        sys.exit(1)

    log_files_to_process = find_log_files(log_directory)

    processed_files_count = 0
    successful_decryptions_count = 0
    failed_decryptions_list = [] # List of (file_path, error_message)
    all_findings = [] # List of strings for "TEST_CONFIG_LOADED" hits

    if not log_files_to_process:
        print(f"No .enc_log files found in {log_directory} using shell commands.")
    else:
        print(f"\nProcessing {len(log_files_to_process)} log file(s) from {log_directory}...")
        for log_file_path in log_files_to_process:
            processed_files_count += 1
            print(f"Attempting to process: {log_file_path}")
            success, result_data_or_error = decrypt_and_parse_log(log_file_path, ENCRYPTION_KEY)

            if success:
                successful_decryptions_count += 1
                findings_from_file = analyze_log_data(result_data_or_error, log_file_path)
                if findings_from_file:
                    all_findings.extend(findings_from_file)
                else:
                    print(f"No specific findings in {os.path.basename(log_file_path)} after successful parse.")
            else:
                failed_decryptions_list.append((os.path.basename(log_file_path), result_data_or_error))
                # Error message already printed by decrypt_and_parse_log
                print(f"Skipping analysis for {os.path.basename(log_file_path)} due to previous errors.")

    # Define report path relative to the script's location (OP_SDWAN/tools/)
    # Report goes to OP_SDWAN/reports/
    report_file_name = "concurrency_test_findings_report.md"
    # Path for report dir: OP_SDWAN/tools/../../OP_SDWAN/reports -> <repo_root>/OP_SDWAN/reports/
    report_dir_relative_to_script = os.path.join("..", "..", "OP_SDWAN", "reports")
    report_dir_abs = os.path.abspath(os.path.join(current_script_dir, report_dir_relative_to_script))
    report_file_path = os.path.join(report_dir_abs, report_file_name)

    generate_markdown_report(
        all_findings,
        report_file_path,
        processed_files_count,
        successful_decryptions_count,
        failed_decryptions_list
    )

    if not log_files_to_process: # If no files, main summary might be slightly different
         print("\n--- Analysis Complete (No files found to process). ---")
    elif not all_findings and not failed_decryptions_list and successful_decryptions_count == processed_files_count:
        print("\n--- Analysis Complete. All files processed successfully, no specific findings or errors. ---")
    elif not all_findings:
        print("\n--- Analysis Complete. No specific findings to report from processed files. ---")
    else: # There were findings
        print("\n--- Analysis Complete. Findings listed in the report. ---")


if __name__ == '__main__':
    main()
