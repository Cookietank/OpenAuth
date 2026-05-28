import threading
import time
import sys
import tkinter as tk
from plugin_manager import PluginBase

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

if IS_WIN:
    try: import keyboard
    except ImportError: pass
elif IS_MAC:
    try: import pyautogui
    except ImportError: pass

class AutoLoginPlugin(PluginBase):
    def setup(self):
        if "--tray" in sys.argv:
            self.app.root.after(15000, self._delayed_bind)
        else:
            self._delayed_bind()

    def _delayed_bind(self):
        hotkey = self.app.config.get("hotkeys", {}).get("Auto-Login", "ctrl+alt+q")
        self.bind_native_hotkey(hotkey, self.execute_automation)

    def config_updated(self):
        new_hotkey = self.app.config.get("hotkeys", {}).get("Auto-Login", "")
        self.bind_native_hotkey(new_hotkey, self.execute_automation)

    def get_target_code(self):
        if self.app.accounts:
            return self.app.accounts[0].get_current_code()
        return None

    def copy_to_clipboard(self, text):
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(text)
        self.app.root.update()

    def execute_automation(self):
        print("\n[AUTO-LOGIN] Sequence Initiated via Native Keystrokes!")
        self.app.root.after(0, self.app.show_toast, "Triggering Microsoft Auto Login")
        threading.Thread(target=self._run_sequence, daemon=True).start()

    def _run_sequence(self):
        try:
            delay = float(self.app.config.get("hotkeys", {}).get("auto_login_delay", 0.8))
            ways_to_verify = int(self.app.config.get("hotkeys", {}).get("auto_login_ways", 2))
            
            if IS_WIN:
                keyboard.release('ctrl')
                keyboard.release('alt')
                keyboard.release('shift')
            elif IS_MAC:
                time.sleep(0.3)
                pyautogui.keyUp('command')
                pyautogui.keyUp('option')
                pyautogui.keyUp('shift')
                pyautogui.keyUp('ctrl')
            
            time.sleep(0.1)
            
            tabs_needed = ways_to_verify - 1
            print(f"[AUTO-LOGIN] Step 1: {tabs_needed}x Tab -> Enter")
            
            for _ in range(tabs_needed):
                if IS_WIN:
                    keyboard.send('tab')
                elif IS_MAC:
                    pyautogui.press('tab')
                time.sleep(0.1)
                
            if IS_WIN:
                keyboard.send('enter')
            elif IS_MAC:
                pyautogui.press('enter')
            
            code = self.get_target_code()
            if code:
                print(f"[AUTO-LOGIN] Copying code: {code}")
                self.app.root.after(0, self.copy_to_clipboard, code)
            else:
                print("[AUTO-LOGIN] No code available to copy!")
                self.app.root.after(0, self.app.show_toast, "Error: No Primary Code available!")
                return
                
            time.sleep(delay)
            
            print("[AUTO-LOGIN] Step 2: Paste -> Enter")
            if IS_WIN:
                keyboard.send('ctrl+v')
                time.sleep(0.2)
                keyboard.send('enter')
            elif IS_MAC:
                pyautogui.hotkey('command', 'v')
                time.sleep(0.2)
                pyautogui.press('enter')
            
            print("[AUTO-LOGIN] Sequence Complete!")
            
        except Exception as e:
            print(f"[AUTO-LOGIN] Error during sequence: {e}")