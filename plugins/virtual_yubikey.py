import threading
import time
import sys
import tkinter as tk
from plugin_manager import PluginBase

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

if IS_WIN:
    try:
        import keyboard
    except ImportError:
        pass
elif IS_MAC:
    try:
        import pyautogui
    except ImportError:
        pass

class VirtualYubiKeyPlugin(PluginBase):
    def setup(self):
        hotkey = self.app.config.get("hotkeys", {}).get("Copy Code to Clipboard", "ctrl+alt+c")
        self.bind_native_hotkey(hotkey, self.execute_hotkey_action)

    def config_updated(self):
        """Live Apply: Instantly rebind the hotkey if changed in settings."""
        new_hotkey = self.app.config.get("hotkeys", {}).get("Copy Code to Clipboard", "")
        self.bind_native_hotkey(new_hotkey, self.execute_hotkey_action)

    def copy_to_clipboard(self, text):
        """Safely interacts with Tkinter's clipboard from the main GUI thread."""
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(text)
        self.app.root.update()

    def execute_hotkey_action(self):
        if not self.app.accounts:
            self.app.root.after(0, self.app.show_toast, "No accounts provisioned!")
            return
            
        primary_acc = self.app.accounts[0]
        rem_time = primary_acc.get_time_remaining()
        
        if rem_time <= 3:
            self.app.root.after(0, self.app.show_toast, f"Code expiring in {rem_time}s!\nWaiting for next code...", 3000)
            threading.Thread(target=self._wait_and_copy_next, args=(primary_acc, rem_time), daemon=True).start()
        else:
            code = primary_acc.get_current_code()
            self._process_code(code, rem_time)

    def _process_code(self, code, rem_time):
        # 1. Always ensure it goes to the clipboard natively as a fallback
        self.app.root.after(0, self.copy_to_clipboard, code)
        
        # 2. Check the user's toggle setting
        auto_paste = self.app.config.get("hotkeys", {}).get("auto_paste", False)
        
        if auto_paste:
            try:
                if IS_WIN:
                    keyboard.write(code, delay=0.02)
                    keyboard.send('enter')
                elif IS_MAC:
                    pyautogui.write(code, interval=0.02)
                    pyautogui.press('enter')
                    
                self.app.root.after(0, self.app.show_toast, f"Code Pasted: {code}\n(Valid for {rem_time}s)")
            except Exception as e:
                self.app.root.after(0, self.app.show_toast, f"Paste failed: {e}")
        else:
            self.app.root.after(0, self.app.show_toast, f"Code Copied: {code}\n(Valid for {rem_time}s)")

    def _wait_and_copy_next(self, primary_acc, wait_time):
        time.sleep(wait_time + 0.2)
        new_code = primary_acc.get_current_code()
        
        # Safely push the delayed processing back to the main thread
        self.app.root.after(0, lambda: self._process_code(new_code, 30))