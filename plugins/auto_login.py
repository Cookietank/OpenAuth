import threading
import time
import sys
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
        # 15-second delay ensures Windows CPU settles before hooking
        if "--tray" in sys.argv:
            time.sleep(15)
            
        hotkey = self.app.config.get("hotkeys", {}).get("Auto-Login", "ctrl+alt+q")
        self.bind_hotkey(hotkey)
        
        # Infinite loop ensures the listener survives if Windows drops the hook
        while True:
            try:
                keyboard.wait()
            except Exception:
                time.sleep(2)

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
        print("\n[AUTO-LOGIN] Sequence Initiated via Keystrokes!")
        self.app.root.after(0, self.show_toast, "Triggering Microsoft Auto Login")
        threading.Thread(target=self._run_sequence, daemon=True).start()

    def _run_sequence(self):
        try:
            delay = float(self.app.config.get("hotkeys", {}).get("auto_login_delay", 0.8))
            ways_to_verify = int(self.app.config.get("hotkeys", {}).get("auto_login_ways", 2))
            
            keyboard.release('ctrl')
            keyboard.release('alt')
            keyboard.release('shift')
            
            print("[AUTO-LOGIN] Step 1: Tab -> Enter")
            keyboard.send('tab')
            time.sleep(0.1) 
            keyboard.send('enter')
            
            time.sleep(delay)
            
            tabs_needed = ways_to_verify - 1
            print(f"[AUTO-LOGIN] Step 2: {tabs_needed}x Tab -> Enter")
            
            for _ in range(tabs_needed):
                keyboard.send('tab')
                time.sleep(0.1)
                
            keyboard.send('enter')
            
            code = self.get_target_code()
            if code:
                print(f"[AUTO-LOGIN] Copying code: {code}")
                self.app.root.after(0, self.copy_to_clipboard, code)
            else:
                print("[AUTO-LOGIN] No code available to copy!")
                self.app.root.after(0, self.show_toast, "Error: No Primary Code available!")
                return
                
            time.sleep(delay)
            
            print("[AUTO-LOGIN] Step 3: Paste -> Enter")
            keyboard.send('ctrl+v')
            time.sleep(0.2)
            keyboard.send('enter')
            
            print("[AUTO-LOGIN] Sequence Complete!")
            
        except Exception as e:
            print(f"[AUTO-LOGIN] Error during sequence: {e}")