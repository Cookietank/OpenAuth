import tkinter as tk
from tkinter import ttk
import threading
import sys
import os
from plugin_manager import PluginBase

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

if IS_WIN:
    import pystray
elif IS_MAC:
    import AppKit

    class MacTrayDelegate(AppKit.NSObject):
        plugin = None

        def showApp_(self, sender):
            self.plugin.app.root.after(0, self.plugin.restore_from_tray)

        def copyCode_(self, sender):
            self.plugin.app.root.after(0, self.plugin.copy_from_tray)

        def quitApp_(self, sender):
            self.plugin.app.root.after(0, self.plugin.quit_from_tray)


class TrayIconPlugin(PluginBase):
    def setup(self):
        self.to_tray_btn = None
        self.status_item = None
        self.mac_delegate = None

        btn_text = "To Menu Bar" if IS_MAC else "To Tray"
        
        if not self.app.config.get("understood_tray", False):
            self.to_tray_btn = self.app.add_toolbar_action(btn_text, self.tray_tutorial_click, side=tk.RIGHT)
        
        self.app.root.bind("<Unmap>", self.on_unmap)
        
        if "--tray" in sys.argv:
            self.app.root.after(100, self.minimize_to_tray)

    def tray_tutorial_click(self):
        tut = tk.Toplevel(self.app.root)
        os_tray_name = "macOS Menu Bar" if IS_MAC else "System Tray"
        btn_text = "To Menu Bar" if IS_MAC else "To Tray"
        
        tut.title(os_tray_name)
        tut.geometry("380x250")
        tut.attributes("-topmost", True)
        tut.configure(bg=self.app.colors['bg'])
        
        tk.Label(tut, text=f"ℹ️ Hiding in the {os_tray_name}", font=("Helvetica", 12, "bold"), bg=self.app.colors['bg'], fg=self.app.colors['fg']).pack(pady=15)
        
        msg = f"OpenAuth is designed to run silently in the background.\n\nIt minimizes to your {os_tray_name}.\n\nPro Tip: Clicking the Close (X) button does the exact same thing!"
        tk.Message(tut, text=msg, bg=self.app.colors['bg'], fg=self.app.colors['fg'], width=340, justify=tk.LEFT).pack(padx=20, pady=5)
        
        understand_var = tk.BooleanVar(value=True)
        chk = ttk.Checkbutton(tut, text=f"I understand, remove this '{btn_text}' button", variable=understand_var)
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
        # On Mac, the yellow minimize button naturally minimizes to the Dock.
        # We ONLY intercept the 'iconic' state on Windows to force it to the Tray.
        if IS_WIN:
            if event.widget == self.app.root and self.app.root.state() == 'iconic':
                self.minimize_to_tray()

    def minimize_to_tray(self, event=None):
        """Hides the app UI, and triggers the OS-specific hidden background state."""
        for widget in self.app.root.winfo_children():
            if isinstance(widget, tk.Toplevel):
                widget.destroy()
                
        self.app.root.withdraw() 
        
        if IS_WIN:
            threading.Thread(target=self.show_tray_win, daemon=True).start()
        elif IS_MAC:
            self.show_tray_mac()

    def show_tray_win(self):
        image = self.app.get_icon_image()
        menu = pystray.Menu(
            pystray.MenuItem('Show OpenAuth', self.restore_from_tray, default=True),
            pystray.MenuItem('Copy Primary Code', self.copy_from_tray),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem('Quit', self.quit_from_tray)
        )
        self.icon = pystray.Icon("OpenAuth", image, "OpenAuth", menu)
        self.icon.run()

    def show_tray_mac(self):
        # Native AppKit API to create a Menu Bar item (Must run on Tkinter Main Thread)
        if not self.status_item:
            self.status_item = AppKit.NSStatusBar.systemStatusBar().statusItemWithLength_(AppKit.NSVariableStatusItemLength)
            self.status_item.button().setTitle_("🛡️")
            
            self.mac_delegate = MacTrayDelegate.alloc().init()
            self.mac_delegate.plugin = self
            
            menu = AppKit.NSMenu.alloc().init()
            
            item_show = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Show OpenAuth", "showApp:", "")
            item_show.setTarget_(self.mac_delegate)
            menu.addItem_(item_show)
            
            item_copy = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Copy Primary Code", "copyCode:", "")
            item_copy.setTarget_(self.mac_delegate)
            menu.addItem_(item_copy)
            
            menu.addItem_(AppKit.NSMenuItem.separatorItem())
            
            item_quit = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("Quit", "quitApp:", "")
            item_quit.setTarget_(self.mac_delegate)
            menu.addItem_(item_quit)
            
            self.status_item.setMenu_(menu)
            
        # Hide the App from the macOS Dock completely
        AppKit.NSApp.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)

    def copy_from_tray(self, icon=None, item=None):
        if self.app.accounts:
            code = self.app.accounts[0].get_current_code()
            def safe_copy():
                self.app.root.clipboard_clear()
                self.app.root.clipboard_append(code)
                self.app.root.update()
            self.app.root.after(0, safe_copy)
            self.app.root.after(0, lambda: self.app.show_toast(f"Code copied: {code}"))

    def restore_from_tray(self, icon=None, item=None):
        if IS_WIN:
            self.icon.stop() 
        elif IS_MAC:
            # Remove the Menu Bar icon
            if self.status_item:
                AppKit.NSStatusBar.systemStatusBar().removeStatusItem_(self.status_item)
                self.status_item = None
            # Restore the App to the macOS Dock and bring to front
            AppKit.NSApp.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
            AppKit.NSApp.activateIgnoringOtherApps_(True)
            
        self.app.root.after(0, self.app.resize_main_window)
        self.app.root.after(0, self.app.root.deiconify) 

    def quit_from_tray(self, icon=None, item=None):
        if IS_WIN:
            self.icon.stop()
        self.app.root.after(0, self.app.force_quit_app)