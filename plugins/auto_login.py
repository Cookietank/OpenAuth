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
        print("Missing libraries. Run: pip install keyboard")
elif IS_MAC:
    try:
        import pyautogui
    except ImportError:
        print("Missing libraries. Run: pip3 install pyautogui")

class AutoLoginPlugin(PluginBase):
    def setup(self):
        hotkey = self.app.config.get("hotkeys", {}).get("Auto-Login", "ctrl+alt+q")
        self.bind_native_hotkey(hotkey, self.execute_automation)

    def config_updated(self):
        """Live Apply: Instantly rebind the hotkey if changed in settings."""
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

    def show_toast(self, message, duration=2500):
        """Creates a custom, non-blocking floating notification window."""
        toast = tk.Toplevel(self.app.root)
        toast.overrideredirect(True)
        toast.attributes('-topmost', True)
        toast.configure(bg="#2d2d2d", bd=1, relief=tk.SOLID)
        
        lbl = tk.Label(toast, text=message, fg="white", bg="#2d2d2d", font=("Helvetica", 10), padx=15, pady=10)
        lbl.pack()
        
        self.app.root.update_idletasks()
        
        x = toast.winfo_screenwidth() - toast.winfo_width() - 20
        y = toast.winfo_screenheight() - toast.winfo_height() - 60
        toast.geometry(f"+{x}+{y}")
        
        self.app.root.after(duration, toast.destroy)

    def execute_automation(self):
        print("\n[AUTO-LOGIN] Sequence Initiated via Native Keystrokes!")
        self.app.root.after(0, self.show_toast, "Triggering Microsoft Auto Login")
        threading.Thread(target=self._run_sequence, daemon=True).start()

    def _run_sequence(self):
        try:
            delay = float(self.app.config.get("hotkeys", {}).get("auto_login_delay", 0.8))
            ways_to_verify = int(self.app.config.get("hotkeys", {}).get("auto_login_ways", 2))
            
            # Failsafe: release keys in case user is still holding Ctrl/Alt/Cmd
            if IS_WIN:
                keyboard.release('ctrl')
                keyboard.release('alt')
                keyboard.release('shift')
            elif IS_MAC:
                pyautogui.keyUp('command')
                pyautogui.keyUp('option')
                pyautogui.keyUp('shift')
                pyautogui.keyUp('ctrl')
            
            time.sleep(0.1)
            
            # Step 1: Dynamic Tabs to select the Authenticator Code option
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
                self.app.root.after(0, self.show_toast, "Error: No Primary Code available!")
                return
                
            time.sleep(delay)
            
            # Step 2: Paste -> Enter
            print("[AUTO-LOGIN] Step 2: Paste -> Enter")
            if IS_WIN:
                keyboard.send('ctrl+v')
                time.sleep(0.2)
                keyboard.send('enter')
            elif IS_MAC:
                # macOS uses Command+V to paste!
                pyautogui.hotkey('command', 'v')
                time.sleep(0.2)
                pyautogui.press('enter')
            
            print("[AUTO-LOGIN] Sequence Complete!")
            
        except Exception as e:
            print(f"[AUTO-LOGIN] Error during sequence: {e}")