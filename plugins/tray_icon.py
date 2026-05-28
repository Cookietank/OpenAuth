import tkinter as tk
import threading
import sys
import os
from plugin_manager import PluginBase

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

if IS_WIN:
    import pystray

class TrayIconPlugin(PluginBase):
    def setup(self):
        self.to_tray_btn = None
        
        # macOS handles apps via the Dock, so we skip the custom Tray Icon logic there
        if IS_WIN:
            if not self.app.config.get("understood_tray", False):
                self.to_tray_btn = self.app.add_toolbar_action("To Tray", self.tray_tutorial_click, side=tk.RIGHT)
            self.app.root.bind("<Unmap>", self.on_unmap)
        
        if "--tray" in sys.argv:
            if IS_WIN:
                self.app.root.after(100, self.minimize_to_tray)
            elif IS_MAC:
                self.app.root.after(100, self.app.root.iconify)

    def tray_tutorial_click(self):
        if IS_MAC: return
        tut = tk.Toplevel(self.app.root)
        tut.title("System Tray")
        tut.geometry("380x250")
        tut.attributes("-topmost", True)
        tut.configure(bg=self.app.colors['bg'])
        
        tk.Label(tut, text="ℹ️ Hiding in the Tray", font=("Helvetica", 12, "bold"), bg=self.app.colors['bg'], fg=self.app.colors['fg']).pack(pady=15)
        
        msg = "OpenAuth is designed to run silently in the background.\n\nIt minimizes to your Windows System Tray (the small icons near your clock in the bottom right of your screen).\n\nPro Tip: The standard Windows Minimize (-) button does the exact same thing!"
        tk.Message(tut, text=msg, bg=self.app.colors['bg'], fg=self.app.colors['fg'], width=340, justify=tk.LEFT).pack(padx=20, pady=5)
        
        from tkinter import ttk
        understand_var = tk.BooleanVar(value=True)
        chk = ttk.Checkbutton(tut, text="I understand, remove this 'To Tray' button", variable=understand_var)
        chk.pack(pady=10)
        
        def proceed():
            if understand_var.get():
                self.app.config["understood_tray"] = True
                self.app.save_config()
                if self.to_tray_btn:
                    self.to_tray_btn.pack_forget()
                    self.to_tray_btn.destroy()
            tut.destroy()
            self.minimize_to_tray()

        ttk.Button(tut, text="Got it!", command=proceed).pack(pady=10)

    def on_unmap(self, event):
        if IS_MAC: return
        if event.widget == self.app.root and self.app.root.state() == 'iconic':
            self.minimize_to_tray()

    def minimize_to_tray(self, event=None):
        if IS_MAC:
            self.app.root.iconify()
            return
            
        for widget in self.app.root.winfo_children():
            if isinstance(widget, tk.Toplevel):
                widget.destroy()
                
        self.app.root.withdraw() 
        threading.Thread(target=self.show_tray, daemon=True).start()

    def show_tray(self):
        if IS_MAC: return
        image = self.app.get_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem('Show OpenAuth', self.restore_from_tray, default=True),
            pystray.MenuItem('Copy Primary Code', self.copy_from_tray),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', self.quit_from_tray)
        )
        self.icon = pystray.Icon("OpenAuth", image, "OpenAuth", menu)
        self.icon.run()

    def copy_from_tray(self, icon, item):
        if self.app.accounts:
            code = self.app.accounts[0].get_current_code()
            def safe_copy():
                self.app.root.clipboard_clear()
                self.app.root.clipboard_append(code)
                self.app.root.update()
            self.app.root.after(0, safe_copy)
            try:
                self.icon.notify(f"Code copied: {code}", "OpenAuth")
            except Exception as e:
                print(f"Tray notification failed: {e}")

    def restore_from_tray(self, icon, item):
        if IS_MAC: return
        self.icon.stop() 
        self.app.root.after(0, self.app.resize_main_window)
        self.app.root.after(0, self.app.root.deiconify) 

    def quit_from_tray(self, icon, item):
        if IS_MAC: return
        self.icon.stop()
        self.app.root.after(0, self.app.force_quit_app)