import os
import sys
import threading
import time

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

if IS_WIN:
    import ctypes
    from ctypes import wintypes
    
    WM_HOTKEY = 0x0312
    WM_QUIT = 0x0012
    MOD_ALT = 0x0001
    MOD_CTRL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008

    VK_CODES = {
        'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45, 'f': 0x46,
        'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A, 'k': 0x4B, 'l': 0x4C,
        'm': 0x4D, 'n': 0x4E, 'o': 0x4F, 'p': 0x50, 'q': 0x51, 'r': 0x52,
        's': 0x53, 't': 0x54, 'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58,
        'y': 0x59, 'z': 0x5A,
        'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73, 'f5': 0x74, 'f6': 0x75,
        'f7': 0x76, 'f8': 0x77, 'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
        'space': 0x20, 'enter': 0x0D, 'esc': 0x1B, 'tab': 0x09
    }

    class NativeHotkeyThread(threading.Thread):
        def __init__(self, hotkey_str, callback, app_ref=None):
            super().__init__(daemon=True)
            self.hotkey_str = hotkey_str
            self.callback = callback
            self.thread_id = None
            self.hotkey_id = 1 

        def run(self):
            self.thread_id = ctypes.windll.kernel32.GetCurrentThreadId()
            
            parts = self.hotkey_str.lower().split('+')
            modifiers = 0
            vk = 0
            for part in parts:
                part = part.strip()
                if part == 'ctrl': modifiers |= MOD_CTRL
                elif part == 'alt': modifiers |= MOD_ALT
                elif part == 'shift': modifiers |= MOD_SHIFT
                elif part == 'win': modifiers |= MOD_WIN
                elif part in VK_CODES: vk = VK_CODES[part]
            
            if not ctypes.windll.user32.RegisterHotKey(None, self.hotkey_id, modifiers, vk):
                print(f"[HOTKEY ERROR] Failed to register native hotkey: {self.hotkey_str}")
                return

            print(f"[*] Bound Native Windows Hotkey: {self.hotkey_str}")

            msg = wintypes.MSG()
            while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    self.callback()
                ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

            ctypes.windll.user32.UnregisterHotKey(None, self.hotkey_id)

        def stop(self):
            if self.thread_id:
                ctypes.windll.user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)

elif IS_MAC:
    import keyboard

    class NativeHotkeyThread(threading.Thread):
        def __init__(self, hotkey_str, callback, app_ref=None):
            super().__init__(daemon=True)
            # Ensure proper Mac key mapping (e.g., 'win' becomes 'cmd')
            self.hotkey_str = hotkey_str.lower().replace('win', 'cmd')
            self.callback = callback
            self._stop_event = threading.Event()

        def run(self):
            try:
                # Clean up any lingering hooks from live-reloads
                try: keyboard.remove_hotkey(self.hotkey_str)
                except: pass
                
                # Bind using the reliable 'keyboard' library
                keyboard.add_hotkey(self.hotkey_str, self.callback)
                print(f"[*] Bound Mac Hotkey: {self.hotkey_str}")
                
                # Block the thread safely to keep the listener alive
                while not self._stop_event.is_set():
                    time.sleep(0.5)
            except Exception as e:
                print(f"[HOTKEY ERROR] Mac hotkey binding failed. Did you grant Accessibility permissions? Error: {e}")

        def stop(self):
            self._stop_event.set()
            try:
                keyboard.remove_hotkey(self.hotkey_str)
            except:
                pass


class PluginBase:
    def __init__(self, app):
        self.app = app
        self._hotkey_thread = None

    def setup(self): pass
    def config_updated(self): pass

    def bind_native_hotkey(self, hotkey_str, callback):
        if self._hotkey_thread:
            self._hotkey_thread.stop()
            self._hotkey_thread = None
        
        if hotkey_str:
            self._hotkey_thread = NativeHotkeyThread(hotkey_str, callback, self.app)
            self._hotkey_thread.start()

    def get_resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

class PluginManager:
    def __init__(self, app):
        self.app = app
        self.plugins = []

    def register_plugin(self, plugin_class):
        plugin_instance = plugin_class(self.app)
        plugin_instance.setup()
        self.plugins.append(plugin_instance)

    def broadcast(self, event_name, *args, **kwargs):
        for plugin in self.plugins:
            method = getattr(plugin, event_name, None)
            if callable(method):
                method(*args, **kwargs)