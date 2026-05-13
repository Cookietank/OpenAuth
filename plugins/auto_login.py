import threading
import time
import tkinter as tk
from plugin_manager import PluginBase

try:
    import keyboard
except ImportError:
    print("Missing libraries. Run: pip install keyboard")

class AutoLoginPlugin(PluginBase):
    def setup(self):
        self.hotkey_hook = None
        threading.Thread(target=self.start_hotkey_listener, daemon=True).start()

    def start_hotkey_listener(self):
        hotkey = self.app.config.get("hotkeys", {}).get("Auto-Login", "ctrl+alt+q")
        self.bind_hotkey(hotkey)
        keyboard.wait()

    def config_updated(self):
        """Live Apply: Instantly rebind the hotkey if changed in settings."""
        new_hotkey = self.app.config.get("hotkeys", {}).get("Auto-Login", "")
        self.bind_hotkey(new_hotkey)

    def bind_hotkey(self, new_hotkey):
        if self.hotkey_hook:
            try:
                keyboard.remove_hotkey(self.hotkey_hook)
            except Exception:
                pass
            self.hotkey_hook = None
            
        if not new_hotkey:
            return
            
        try:
            self.hotkey_hook = keyboard.add_hotkey(new_hotkey, self.execute_automation)
            print(f"Bound Auto-Login Macro to: {new_hotkey}")
        except Exception as e:
            print(f"Failed to bind hotkey: {e}")

    def get_target_code(self):
        if self.app.accounts:
            return self.app.accounts[0].get_current_code()
        return None

    def copy_to_clipboard(self, text):
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(text)
        self.app.root.update()

    def execute_automation(self):
        print("\n[AUTO-LOGIN] Sequence Initiated via Keystrokes!")
        threading.Thread(target=self._run_sequence, daemon=True).start()

    def _run_sequence(self):
        try:
            # Dynamically fetch the delay setting (defaults to 0.8s)
            delay = float(self.app.config.get("hotkeys", {}).get("auto_login_delay", 0.8))
            
            # Force release modifier keys so 'tab' doesn't become 'ctrl+tab'
            keyboard.release('ctrl')
            keyboard.release('alt')
            keyboard.release('shift')
            
            print("[AUTO-LOGIN] Step 1: Tab -> Enter")
            keyboard.send('tab')
            time.sleep(0.1) 
            keyboard.send('enter')
            
            # Wait for next screen to load based on user settings
            time.sleep(delay)
            
            print("[AUTO-LOGIN] Step 2: Tab -> Enter")
            keyboard.send('tab')
            time.sleep(0.1)
            keyboard.send('enter')
            
            code = self.get_target_code()
            if code:
                print(f"[AUTO-LOGIN] Copying code: {code}")
                self.app.root.after(0, self.copy_to_clipboard, code)
            else:
                print("[AUTO-LOGIN] No code available to copy!")
                return
                
            # Wait for the code input screen to load and RDP clipboard to sync
            time.sleep(delay)
            
            print("[AUTO-LOGIN] Step 3: Paste -> Enter")
            keyboard.send('ctrl+v')
            time.sleep(0.2)
            keyboard.send('enter')
            
            print("[AUTO-LOGIN] Sequence Complete!")
            
        except Exception as e:
            print(f"[AUTO-LOGIN] Error during sequence: {e}")