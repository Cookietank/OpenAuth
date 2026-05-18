import tkinter as tk
from tkinter import ttk, messagebox
import urllib.parse
from plugin_manager import PluginBase

class BackupExportPlugin(PluginBase):
    def setup(self):
        # The button is now generated natively in the Advanced Settings tab!
        pass

    def open_export_ui(self):
        if not self.app.accounts:
            messagebox.showinfo("Export", "No accounts to export!", parent=self.app.root)
            return

        warning_msg = (
            "⚠️ SECURITY WARNING ⚠️\n\n"
            "Anyone who has access to these secret keys can generate your 2FA codes "
            "and access your accounts.\n\n"
            "Ensure no one else is looking at your screen, and only store these "
            "in a secure password manager or physical safe.\n\n"
            "Do you want to proceed?"
        )
        if not messagebox.askyesno("Security Warning", warning_msg, parent=self.app.root):
            return

        top = tk.Toplevel(self.app.root)
        top.title("Export Accounts")
        top.geometry("500x450")
        top.attributes("-topmost", True)
        top.configure(bg=self.app.colors['bg'])

        tk.Label(top, text="Account Backup & Export", font=("Helvetica", 14, "bold"), bg=self.app.colors['bg'], fg=self.app.colors['fg']).pack(pady=(15, 5))
        tk.Label(top, text="Store these securely. Never share them with anyone.", bg=self.app.colors['bg'], fg=self.app.colors['fg']).pack(pady=(0, 10))

        text_frame = tk.Frame(top, bg=self.app.colors['bg'])
        text_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        text_area = tk.Text(text_frame, yscrollcommand=scrollbar.set, bg=self.app.colors['entry_bg'], fg=self.app.colors['fg'], font=("Consolas", 10), wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
        text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_area.yview)

        export_data = ""
        for acc in self.app.accounts:
            parsed_uri = urllib.parse.urlparse(acc.uri)
            qs = urllib.parse.parse_qs(parsed_uri.query)
            secret = qs.get('secret', [''])[0]

            export_data += f"Issuer:  {acc.issuer}\n"
            export_data += f"Account: {acc.name}\n"
            export_data += f"Secret:  {secret}\n"
            export_data += f"URI:     {acc.uri}\n"
            export_data += "-" * 45 + "\n\n"

        text_area.insert(tk.END, export_data)
        text_area.config(state=tk.DISABLED) 

        def copy_all():
            self.app.root.clipboard_clear()
            self.app.root.clipboard_append(export_data)
            self.app.root.update()
            messagebox.showinfo("Copied", "All account secrets have been copied to your clipboard!", parent=top)

        btn_frame = tk.Frame(top, bg=self.app.colors['bg'])
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=15, padx=15)
        
        ttk.Button(btn_frame, text="Copy All to Clipboard", command=copy_all).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        ttk.Button(btn_frame, text="Close", command=top.destroy).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(5, 0))