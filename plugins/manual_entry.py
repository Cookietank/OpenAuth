import tkinter as tk
from tkinter import ttk, messagebox
import urllib.parse
from plugin_manager import PluginBase

class ManualEntryPlugin(PluginBase):
    def setup(self):
        if hasattr(self.app, 'add_auth_action'):
            self.app.add_auth_action("Add Manually (Secret/URI)", self.open_manual_entry)
        else:
            self.app.add_toolbar_action("Add Manually", self.open_manual_entry, side=tk.LEFT)

    def open_manual_entry(self):
        top = tk.Toplevel(self.app.root)
        top.title("Add Account Manually")
        top.geometry("350x300")
        top.attributes("-topmost", True)
        top.configure(bg=self.app.colors['bg'])

        notebook = ttk.Notebook(top)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        secret_frame = ttk.Frame(notebook)
        notebook.add(secret_frame, text="Secret Key")

        tk.Label(secret_frame, text="Issuer (e.g. Microsoft):", bg=self.app.colors['bg'], fg=self.app.colors['fg']).pack(anchor="w", padx=10, pady=(10, 0))
        issuer_var = tk.StringVar()
        self.app.create_styled_entry(secret_frame, issuer_var).pack(fill=tk.X, padx=10, pady=2, ipady=3)

        tk.Label(secret_frame, text="Account Name (e.g. user@domain.com):", bg=self.app.colors['bg'], fg=self.app.colors['fg']).pack(anchor="w", padx=10, pady=(10, 0))
        name_var = tk.StringVar()
        self.app.create_styled_entry(secret_frame, name_var).pack(fill=tk.X, padx=10, pady=2, ipady=3)

        tk.Label(secret_frame, text="Secret Key:", bg=self.app.colors['bg'], fg=self.app.colors['fg']).pack(anchor="w", padx=10, pady=(10, 0))
        secret_var = tk.StringVar()
        self.app.create_styled_entry(secret_frame, secret_var).pack(fill=tk.X, padx=10, pady=2, ipady=3)

        uri_frame = ttk.Frame(notebook)
        notebook.add(uri_frame, text="Paste URI")

        tk.Label(uri_frame, text="Paste otpauth:// URI:", bg=self.app.colors['bg'], fg=self.app.colors['fg']).pack(anchor="w", padx=10, pady=(10, 0))
        uri_var = tk.StringVar()
        self.app.create_styled_entry(uri_frame, uri_var).pack(fill=tk.X, padx=10, pady=2, ipady=3)

        def add_account():
            current_tab = notebook.index(notebook.select())
            uri_to_add = ""
            
            if current_tab == 0: 
                issuer = urllib.parse.quote(issuer_var.get().strip() or "Unknown")
                name = urllib.parse.quote(name_var.get().strip() or "Account")
                secret = secret_var.get().strip().replace(" ", "").upper()
                
                if not secret:
                    messagebox.showerror("Error", "Secret Key cannot be empty.", parent=top)
                    return
                    
                uri_to_add = f"otpauth://totp/{issuer}:{name}?secret={secret}&issuer={issuer}"
            else: 
                uri_to_add = uri_var.get().strip()
                if not uri_to_add.startswith("otpauth://"):
                    messagebox.showerror("Error", "Invalid URI format. Must start with otpauth://", parent=top)
                    return

            success = self.app.add_account(uri_to_add)
            if success:
                top.destroy()
            else:
                top.focus_force()

        btn_frame = tk.Frame(top, bg=self.app.colors['bg'])
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)
        ttk.Button(btn_frame, text="Add Account", command=add_account).pack(fill=tk.X)