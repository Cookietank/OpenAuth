import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from plugin_manager import PluginBase

SHARED_PLUGIN_REF = None 

class TailscaleAPIHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        expected_token = SHARED_PLUGIN_REF.app.config.get("tailscale", {}).get("api_token", "")
        auth_header = self.headers.get('Authorization')
        
        if not auth_header or auth_header != f"Bearer {expected_token}":
            self.send_response(401)
            self.end_headers()
            self.wfile.write(b"Unauthorized")
            return

        if not SHARED_PLUGIN_REF.app.accounts:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"No accounts provisioned")
            return
            
        primary_code = SHARED_PLUGIN_REF.app.accounts[0].get_current_code()
        
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(primary_code.encode('utf-8'))

    def log_message(self, format, *args):
        pass

class TailscaleSyncPlugin(PluginBase):
    def setup(self):
        global SHARED_PLUGIN_REF
        SHARED_PLUGIN_REF = self
        
        self.server = None
        threading.Thread(target=self.start_server, daemon=True).start()

    def start_server(self):
        port = self.app.config.get("tailscale", {}).get("port", 50051)
        try:
            self.server = ThreadingHTTPServer(('0.0.0.0', port), TailscaleAPIHandler)
            print(f"Tailscale Sync Server listening on port {port}")
            self.server.serve_forever()
        except Exception as e:
            print(f"Failed to start Tailscale server: {e}")

    def config_updated(self):
        """Live Apply: Checks if the port changed, and restarts the server if so."""
        new_port = self.app.config.get("tailscale", {}).get("port", 50051)
        if self.server and self.server.server_port != new_port:
            def restart_srv():
                self.server.shutdown()
                self.server.server_close()
                self.start_server()
            threading.Thread(target=restart_srv, daemon=True).start()