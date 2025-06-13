import argparse
import http.server
import socketserver
import socket
import threading
import time
import json
import os
from datetime import datetime
from typing import Type, Optional

# Attempt to import encryption utilities from the current directory
try:
    from encryption_utils import encrypt_log_entry, ENCRYPTION_KEY as DEFAULT_KEY
except ImportError:
    print("Error: encryption_utils.py not found. Please ensure it's in the same directory.")
    # Define dummy functions if import fails, to allow basic script structure testing
    # In a real scenario, this script would not run without actual encryption_utils
    def encrypt_log_entry(log_str: str, key: bytes) -> bytes:
        print("(Warning: Using dummy encryption - encryption_utils.py not found)")
        return log_str.encode('utf-8')
    DEFAULT_KEY = os.urandom(32)


ENCRYPTION_KEY_BYTES: Optional[bytes] = None
LOG_FILE_PATH: Optional[str] = None
log_lock = threading.Lock()

def write_encrypted_log(log_data: dict) -> None:
    """Appends an encrypted log entry to the global log file."""
    global ENCRYPTION_KEY_BYTES, LOG_FILE_PATH
    if not LOG_FILE_PATH or not ENCRYPTION_KEY_BYTES:
        print("Error: Log file path or encryption key not configured for logging.")
        return

    log_data['timestamp'] = datetime.now().isoformat()
    log_entry_str = json.dumps(log_data)

    try:
        encrypted_log = encrypt_log_entry(log_entry_str, ENCRYPTION_KEY_BYTES)
        with log_lock:
            with open(LOG_FILE_PATH, 'ab') as f: # Append binary
                f.write(encrypted_log + b'\n') # Add newline for easier parsing
    except Exception as e:
        print(f"Error writing encrypted log: {e}")


class LoggingTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    """TCPServer that allows assigning a logger function."""
    def __init__(self, server_address, RequestHandlerClass, logger_func):
        super().__init__(server_address, RequestHandlerClass)
        self.logger_func = logger_func
        self.daemon_threads = True # Ensure threads don't block exit


class HTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP request handler that logs requests."""
    def __init__(self, *args, **kwargs):
        self.server_logger_func = self.server.logger_func #type: ignore
        super().__init__(*args, **kwargs)

    def log_message(self, format_str: str, *args) -> None:
        """Override to log HTTP requests to our encrypted log."""
        log_content = {
            "type": "http_request",
            "source_ip": self.client_address[0],
            "source_port": self.client_address[1],
            "method": self.command,
            "path": self.path,
            "http_version": self.request_version
        }
        self.server_logger_func(log_content)
        # Optional: print to stdout as well for real-time monitoring
        # print(f"HTTP Request: {self.client_address} - {self.command} {self.path}")

class MockSMBTCPHandler(socketserver.BaseRequestHandler):
    """TCP handler to log connection attempts for mock SMB."""
    def handle(self) -> None:
        client_ip, client_port = self.client_address
        log_content = {
            "type": "smb_mock_connection",
            "source_ip": client_ip,
            "source_port": client_port,
            "message": "Connection attempt logged."
        }
        self.server.logger_func(log_content) # type: ignore
        # print(f"Mock SMB (TCP) connection from: {client_ip}:{client_port}")
        self.request.sendall(b"MockSMB: Connection logged.\n")


def start_http_server(host: str, port: int, directory: str, logger_func) -> LoggingTCPServer:
    """Starts the HTTP server in a separate thread."""
    handler = HTTPRequestHandler
    # Must change directory for SimpleHTTPRequestHandler to serve from the correct place
    original_dir = os.getcwd()
    os.chdir(directory)
    httpd = LoggingTCPServer((host, port), handler, logger_func)
    os.chdir(original_dir) # Restore original directory

    print(f"HTTP server serving from '{directory}' on {host}:{port}...")
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd

def start_tcp_mock_server(host: str, port: int, logger_func) -> LoggingTCPServer:
    """Starts the TCP mock (SMB) server in a separate thread."""
    tcpd = LoggingTCPServer((host, port), MockSMBTCPHandler, logger_func)
    print(f"Mock SMB (TCP) server listening on {host}:{port}...")
    thread = threading.Thread(target=tcpd.serve_forever, daemon=True)
    thread.start()
    return tcpd

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock Remote Content Server (HTTP & TCP).")
    parser.add_argument("--http-port", type=int, default=8000, help="HTTP server port.")
    parser.add_argument("--tcp-port", type=int, default=4445, help="TCP mock server port (for SMB simulation).")
    parser.add_argument("--serve-dir", type=str, default=".", help="Directory to serve HTTP content from.")
    parser.add_argument("--log-file", type=str, required=True, help="Path to the encrypted log file.")
    parser.add_argument("--key", type=str, required=True, help="Hex-encoded 256-bit encryption key for logs.")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address for servers.")

    args = parser.parse_args()

    try:
        ENCRYPTION_KEY_BYTES = bytes.fromhex(args.key)
        if len(ENCRYPTION_KEY_BYTES) != 32:
            raise ValueError("Encryption key must be 32 bytes (64 hex characters).")
    except ValueError as e:
        print(f"Error with encryption key: {e}")
        exit(1)

    LOG_FILE_PATH = args.log_file

    # Ensure serve_dir exists
    if not os.path.isdir(args.serve_dir):
        print(f"Error: HTTP serve directory '{args.serve_dir}' does not exist or is not a directory.")
        exit(1)

    # Ensure log directory exists
    log_dir = os.path.dirname(LOG_FILE_PATH)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
        print(f"Created log directory: {log_dir}")

    http_server = start_http_server(args.host, args.http_port, args.serve_dir, write_encrypted_log)
    tcp_server = start_tcp_mock_server(args.host, args.tcp_port, write_encrypted_log)

    print("Servers started. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down servers...")
        http_server.shutdown()
        http_server.server_close()
        tcp_server.shutdown()
        tcp_server.server_close()
        print("Servers stopped.")
