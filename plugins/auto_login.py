import threading
import time
import os
import json
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox
from plugin_manager import PluginBase

try:
    import keyboard
    import pyautogui
    import cv2
except ImportError:
    print("Missing libraries. Run: pip install keyboard pyautogui opencv-python")

# Force Windows DPI Awareness
try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# Windows API Mouse Event Constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000

SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77

CONFIG_FILE = "autologin_config.json"
PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))

class AutoLoginPlugin(PluginBase):
    def setup(self):
        self.hotkey_hook = None
        threading.Thread(target=self.start_hotkey_listener, daemon=True).start()

    def start_hotkey_listener(self):
        hotkey = self.app.config.get("hotkeys", {}).get("Auto-Login OCR", "")
        if not hotkey:
            return
            
        try:
            self.hotkey_hook = keyboard.add_hotkey(hotkey, self.execute_automation)
            print(f"Bound Auto-Login to: {hotkey}")
        except Exception as e:
            print(f"Failed to bind hotkey: {e}")
            
        keyboard.wait()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config.update(json.load(f))
            except Exception as e:
                print(f"Failed to load config: {e}")

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)

    def start_hotkey_listener(self):
        self.bind_hotkey(self.config["hotkey"])
        keyboard.wait()

    def bind_hotkey(self, new_hotkey):
        if self.hotkey_hook:
            try:
                keyboard.remove_hotkey(self.hotkey_hook)
            except Exception:
                pass
        try:
            self.hotkey_hook = keyboard.add_hotkey(new_hotkey, self.execute_automation)
            print(f"[*] Bound Auto-Login to: {new_hotkey}")
        except Exception as e:
            print(f"[!] Failed to bind hotkey: {e}")

    def open_settings_ui(self):
        top = tk.Toplevel(self.app.root)
        top.title("Auto-Login Settings")
        top.geometry("300x150")
        top.attributes("-topmost", True)

        tk.Label(top, text="Global Keyboard Shortcut:", font=("Helvetica", 9, "bold")).pack(anchor="w", padx=10, pady=(15, 2))
        hotkey_var = tk.StringVar(value=self.config.get("hotkey", "ctrl+alt+m"))
        ttk.Combobox(top, textvariable=hotkey_var, values=["ctrl+alt+m", "alt+shift+v", "ctrl+alt+q", "f10"]).pack(fill=tk.X, padx=10)

        def save_and_close():
            self.config["hotkey"] = hotkey_var.get()
            self.save_config()
            self.bind_hotkey(self.config["hotkey"])
            top.destroy()
            messagebox.showinfo("Saved", "Settings saved successfully!", parent=self.app.root)

        ttk.Button(top, text="Save Settings", command=save_and_close).pack(pady=20)

    def get_target_code(self):
        for acc in self.app.accounts:
            if getattr(acc, 'broadcast_port', None) == 50000:
                return acc.get_current_code()
        if self.app.accounts:
            return self.app.accounts[0].get_current_code()
        return None

    def rdp_safe_move_and_click(self, x, y):
        """Bypasses RDP mouse swallowing by mapping to the absolute 65535 hardware grid."""
        user32 = ctypes.windll.user32
        
        # Get the dimensions of your entire monitor setup
        width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)

        # Map pixel coordinates to the 0-65535 absolute grid Windows expects for hardware injection
        mapped_x = int(((x - left) * 65535) / width)
        mapped_y = int(((y - top) * 65535) / height)

        # 1. Teleport the mouse using the ABSOLUTE flag
        flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
        user32.mouse_event(flags, mapped_x, mapped_y, 0, 0)
        
        time.sleep(0.2) # Allow browser to register the hover state
        
        # 2. Fire a Double-Click! (1st click focuses browser, 2nd click hits the link)
        for _ in range(2):
            user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.05) 
            user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.05)

    def find_and_click_image(self, image_name, timeout=4, confidence=0.8, y_offset=0):
        print(f"\n[SEARCH] Looking for '{image_name}' (Timeout: {timeout}s, Conf: {confidence})")
        image_path = os.path.join(PLUGIN_DIR, image_name)
        
        if not os.path.exists(image_path):
            print(f"[ERROR] Missing file: {image_path}")
            return False

        start_time = time.time()
        attempt = 1

        while time.time() - start_time < timeout:
            try:
                pos = pyautogui.locateCenterOnScreen(image_path, confidence=confidence)
                if pos is not None:
                    click_x = pos.x
                    click_y = pos.y + y_offset
                    
                    print(f"  -> [MATCH] Found '{image_name}' at X:{pos.x}, Y:{pos.y}")
                    print(f"  -> [ACTION] Executing RDP-Safe Double Click at X:{click_x}, Y:{click_y}")
                    
                    self.rdp_safe_move_and_click(click_x, click_y)
                    return True
                    
            except pyautogui.ImageNotFoundException:
                pass 
            except Exception as e:
                print(f"  -> [ERROR] OpenCV failed: {e}")
                
            attempt += 1
            time.sleep(0.5)
            
        print(f"[FAIL] Timed out waiting for '{image_name}' after {timeout} seconds.")
        return False

    def execute_automation(self):
        print("\n" + "="*40)
        print("AUTO-LOGIN SEQUENCE INITIATED")
        print("="*40)
        threading.Thread(target=self._run_automation_sequence, daemon=True).start()

    def _run_automation_sequence(self):
        try:
            if not self.find_and_click_image("step1.png", timeout=5):
                return
            time.sleep(1.0)
            
            if not self.find_and_click_image("step2.png", timeout=5):
                return
            time.sleep(1.0)
            
            if not self.find_and_click_image("step3.png", timeout=5, y_offset=40):
                return
            time.sleep(0.5)
            
            code = self.get_target_code()
            if code:
                print(f"\n[ACTION] Hardware typing code: {code}")
                keyboard.write(code, delay=0.05)
                print(f"[ACTION] Hardware pressing ENTER")
                keyboard.send('enter')
                print("\n[SUCCESS] Sequence complete!")
            else:
                print("\n[FAIL] No OTP code available to type!")
                
        except Exception as e:
            print(f"\n[CRITICAL ERROR] Sequence aborted: {e}")