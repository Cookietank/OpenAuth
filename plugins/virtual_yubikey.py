import threading
import time
import sys
import tkinter as tk
from plugin_manager import PluginBase

try:
    import keyboard
except ImportError:
    pass

class VirtualYubiKeyPlugin(PluginBase):
    def setup(self):
        self.hotkey_hook = None
        threading.Thread(target=self.start_hotkey_listener, daemon=True).start()

    def start_hotkey_listener(self):
        # Boot Delay Fix: Windows drops hooks if applied before the desktop is ready
        if "--tray" in sys.argv:
            time.sleep(5)
            
        hotkey = self.app.config.get("hotkeys", {}).get("Copy Code to Clipboard", "ctrl+alt+c")
        self.bind_hotkey(hotkey)
        keyboard.wait()

    def config_updated(self):
        """Live Apply: Instantly rebind the hotkey if changed in settings."""
        new_hotkey = self.app.config.get("hotkeys", {}).get("Copy Code to Clipboard", "")
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
            self.hotkey_hook = keyboard.add_hotkey(new_hotkey, self.execute_hotkey_action)
            print(f"Bound Copy Code Macro to: {new_hotkey}")
        except Exception as e:
            print(f"Failed to bind hotkey: {e}")

    def show_toast(self, message, duration=2500):
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

    def copy_to_clipboard(self, text):
        self.app.root.clipboard_clear()
        self.app.root.clipboard_append(text)
        self.app.root.update()

    def execute_hotkey_action(self):
        if not self.app.accounts:
            self.app.root.after(0, self.show_toast, "No accounts provisioned!")
            return
            
        primary_acc = self.app.accounts[0]
        rem_time = primary_acc.get_time_remaining()
        
        if rem_time <= 3:
            self.app.root.after(0, self.show_toast, f"Code expiring in {rem_time}s!\nWaiting for next code...", 3000)
            threading.Thread(target=self._wait_and_copy_next, args=(primary_acc, rem_time), daemon=True).start()
        else:
            code = primary_acc.get_current_code()
            self._process_code(code, rem_time)

    def _process_code(self, code, rem_time):
        self.app.root.after(0, self.copy_to_clipboard, code)
        auto_paste = self.app.config.get("hotkeys", {}).get("auto_paste", False)
        
        if auto_paste:
            try:
                keyboard.write(code, delay=0.02)
                keyboard.send('enter')
                self.app.root.after(0, self.show_toast, f"Code Pasted: {code}\n(Valid for {rem_time}s)")
            except Exception as e:
                self.app.root.after(0, self.show_toast, f"Paste failed: {e}")
        else:
            self.app.root.after(0, self.show_toast, f"Code Copied: {code}\n(Valid for {rem_time}s)")

    def _wait_and_copy_next(self, primary_acc, wait_time):
        time.sleep(wait_time + 0.2)
        new_code = primary_acc.get_current_code()
        self.app.root.after(0, lambda: self._process_code(new_code, 30))