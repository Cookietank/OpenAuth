import tkinter as tk
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
    import objc

    class MacTrayDelegate(AppKit.NSObject):
        plugin = None

        @objc.IBAction
        def showApp_(self, sender):
            print("[TRAY DIAGNOSTIC] 'Show OpenAuth' clicked in Mac App Bar.")
            if self.plugin:
                try:
                    self.plugin.restore_from_tray()
                except Exception as e:
                    print(f"[TRAY ERROR] Failed to restore app: {e}")

        @objc.IBAction
        def copyCode_(self, sender):
            print("[TRAY DIAGNOSTIC] 'Copy Code' clicked in Mac App Bar.")
            if self.plugin:
                try:
                    self.plugin.copy_from_tray()
                except Exception as e:
                    print(f"[TRAY ERROR] Failed to copy code: {e}")

        @objc.IBAction
        def quitApp_(self, sender):
            print("[TRAY DIAGNOSTIC] 'Quit' clicked in Mac App Bar.")
            if self.plugin:
                self.plugin.quit_from_tray()


class TrayIconPlugin(PluginBase):
    def setup(self):
        self.status_item = None
        self.mac_delegate = None

        btn_text = "To App Bar" if IS_MAC else "To Tray"
        self.app.add_toolbar_action(btn_text, self.minimize_to_tray, side=tk.RIGHT)
        
        if IS_WIN:
            self.app.root.bind("<Unmap>", self.on_unmap)
        
        if "--tray" in sys.argv:
            print("[TRAY DIAGNOSTIC] App launched with --tray flag. Hiding UI.")
            if IS_WIN:
                self.app.root.after(100, self.minimize_to_tray)
            elif IS_MAC:
                self.app.root.after(100, self.minimize_to_tray)

    def on_unmap(self, event):
        if IS_WIN:
            if event.widget == self.app.root and self.app.root.state() == 'iconic':
                self.minimize_to_tray()

    def minimize_to_tray(self, event=None):
        print("[TRAY DIAGNOSTIC] Minimizing app to background...")
        for widget in self.app.root.winfo_children():
            if isinstance(widget, tk.Toplevel):
                widget.destroy()
                
        self.app.root.withdraw() 
        
        if IS_WIN:
            threading.Thread(target=self.show_tray_win, daemon=True).start()
        elif IS_MAC:
            self.app.root.after(0, self.show_tray_mac)

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
        print("[TRAY DIAGNOSTIC] Creating macOS App Bar icon...")
        try:
            if not self.status_item:
                self.status_item = AppKit.NSStatusBar.systemStatusBar().statusItemWithLength_(AppKit.NSVariableStatusItemLength)
                
                icon_path = self.app.get_resource_path(os.path.join('plugins', 'icon.icns'))
                if os.path.exists(icon_path):
                    image = AppKit.NSImage.alloc().initWithContentsOfFile_(icon_path)
                    image.setSize_(AppKit.NSMakeSize(18.0, 18.0))
                    image.setTemplate_(True) 
                    self.status_item.button().setImage_(image)
                else:
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
                
            AppKit.NSApp.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
            print("[TRAY DIAGNOSTIC] Successfully moved to App Bar.")
        except Exception as e:
            print(f"[TRAY ERROR] Failed to create macOS App Bar menu: {e}")

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
        print("[TRAY DIAGNOSTIC] Restoring application...")
        if IS_WIN:
            self.icon.stop() 
        elif IS_MAC:
            try:
                if self.status_item:
                    AppKit.NSStatusBar.systemStatusBar().removeStatusItem_(self.status_item)
                    self.status_item = None
                
                AppKit.NSApp.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
                AppKit.NSApp.activateIgnoringOtherApps_(True)
                
                # THE SLEDGEHAMMER IS BACK: Force macOS to bring the window to the absolute front
                os.system(f"osascript -e 'tell application \"System Events\" to set frontmost of the first process whose unix id is {os.getpid()} to true'")
            except Exception as e:
                print(f"[TRAY ERROR] Failed to restore from Mac App Bar: {e}")
            
        self.app.root.deiconify()
        self.app.root.update()
        self.app.resize_main_window()
        self.app.root.lift()
        self.app.root.focus_force() # Force Tkinter to grab UI focus natively
        print("[TRAY DIAGNOSTIC] Application restored successfully.")

    def quit_from_tray(self, icon=None, item=None):
        if IS_WIN:
            self.icon.stop()
        self.app.root.after(0, self.app.force_quit_app)