import tkinter as tk
import threading
import sys
import pystray
from plugin_manager import PluginBase

class TrayIconPlugin(PluginBase):
    def setup(self):
        self.app.add_toolbar_action("To Tray", self.minimize_to_tray, side=tk.RIGHT)
        
        self.app.root.bind("<Unmap>", self.on_unmap)
        
        if "--tray" in sys.argv:
            self.app.root.after(100, self.minimize_to_tray)

    def on_unmap(self, event):
        if event.widget == self.app.root and self.app.root.state() == 'iconic':
            self.minimize_to_tray()

    def minimize_to_tray(self, event=None):
        for widget in self.app.root.winfo_children():
            if isinstance(widget, tk.Toplevel):
                widget.destroy()
                
        self.app.root.withdraw() 
        threading.Thread(target=self.show_tray, daemon=True).start()

    def show_tray(self):
        image = self.app.get_icon_image()
        
        menu = pystray.Menu(
            # default=True executes when you Double-Click the tray icon
            pystray.MenuItem('Show OpenAuth', self.restore_from_tray, default=True),
            # New Copy action right in the tray menu!
            pystray.MenuItem('Copy Primary Code', self.copy_from_tray),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', self.quit_from_tray)
        )
        self.icon = pystray.Icon("OpenAuth", image, "OpenAuth", menu)
        self.icon.run()

    def copy_from_tray(self, icon, item):
        """Copies the code safely in the Tkinter thread and shows a Windows Native Toast."""
        if self.app.accounts:
            code = self.app.accounts[0].get_current_code()
            
            # Tkinter clipboard must be accessed from the main GUI thread
            def safe_copy():
                self.app.root.clipboard_clear()
                self.app.root.clipboard_append(code)
                self.app.root.update()
                
            self.app.root.after(0, safe_copy)
            
            # Use pystray's built-in Windows Notification API
            try:
                self.icon.notify(f"Code copied: {code}", "OpenAuth")
            except Exception as e:
                print(f"Tray notification failed: {e}")

    def restore_from_tray(self, icon, item):
        self.icon.stop() 
        self.app.root.after(0, self.app.root.deiconify) 

    def quit_from_tray(self, icon, item):
        self.icon.stop()
        self.app.root.after(0, self.app.quit_app)