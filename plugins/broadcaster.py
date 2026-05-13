import tkinter as tk
from tkinter import ttk
import socket
from plugin_manager import PluginBase

class LocalBroadcasterPlugin(PluginBase):
    def setup(self):
        # Track whether broadcasting is toggled ON per account URI
        self.broadcast_states = {}
        
        # Subscribe to App Events
        self.app.account_ui_hooks.append(self.inject_ui)
        self.app.tick_hooks.append(self.on_code_reset)

    def inject_ui(self, acc, frame):
        """Adds the toggle button and port text to the bottom of the account frame."""
        # Generate a consistent port based on its position (e.g., 50000, 50001)
        port = 50000 + self.app.accounts.index(acc)
        acc.broadcast_port = port # Save for later

        b_frame = tk.Frame(frame)
        b_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)

        # Restore previous toggle state or default to False
        is_on = tk.BooleanVar(value=self.broadcast_states.get(acc.uri, False))
        
        def on_toggle(a=acc, v=is_on):
            self.broadcast_states[a.uri] = v.get()

        chk = ttk.Checkbutton(b_frame, text="Local Broadcast", variable=is_on, command=on_toggle)
        chk.pack(side=tk.LEFT, padx=5)

        lbl = ttk.Label(b_frame, text=f"UDP Port: {port}", foreground="gray", font=("Helvetica", 8))
        lbl.pack(side=tk.RIGHT, padx=5)

    def on_code_reset(self):
        """Called automatically by app.py ONLY when the 30-second interval rolls over."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        for acc in self.app.accounts:
            # If toggle is checked
            if self.broadcast_states.get(acc.uri, False):
                port = getattr(acc, 'broadcast_port', None)
                if port:
                    code = acc.get_current_code()
                    try:
                        # Send the code as a UDP packet to localhost on the specific port
                        sock.sendto(code.encode('utf-8'), ('127.0.0.1', port))
                    except Exception as e:
                        print(f"Failed to broadcast {acc.name}: {e}")
        
        sock.close()