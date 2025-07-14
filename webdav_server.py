# webdav_server.py
# Module for launching a lightweight WebDAV server for payload staging.

import os
from cheroot import wsgi
from wsgidav.wsgidav_app import WsgiDAVApp

class DAVServer:
    def __init__(self, root_path: str, host: str, port: int, verbose: bool = True):
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
        self.app = WsgiDAVApp(self.config)
        self.server = wsgi.Server((self.host, self.port), self.app)
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
