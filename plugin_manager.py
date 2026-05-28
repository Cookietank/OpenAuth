import os
import sys
import threading

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
        def __init__(self, hotkey_str, callback):
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
                print(f"[!] Failed to register native hotkey: {self.hotkey_str} (May be in use by another app)")
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
    from pynput import keyboard as pynput_kb

    class NativeHotkeyThread:
        def __init__(self, hotkey_str, callback):
            self.callback = callback
            self.listener = None
            self.current_modifiers = set()
            
            # Parse the string into required modifiers and the trigger key
            parts = hotkey_str.lower().split('+')
            self.required_modifiers = set()
            self.trigger_key = None
            
            for p in parts:
                p = p.strip()
                if p == 'ctrl': self.required_modifiers.add('ctrl')
                elif p == 'alt': self.required_modifiers.add('alt')
                elif p == 'shift': self.required_modifiers.add('shift')
                elif p in ('win', 'cmd'): self.required_modifiers.add('cmd')
                else: self.trigger_key = p
                
        def on_press(self, key):
            try:
                # Track Modifiers
                if key == pynput_kb.Key.ctrl or key == pynput_kb.Key.ctrl_l or key == pynput_kb.Key.ctrl_r:
                    self.current_modifiers.add('ctrl')
                elif key == pynput_kb.Key.alt or key == pynput_kb.Key.alt_l or key == pynput_kb.Key.alt_r:
                    self.current_modifiers.add('alt')
                elif key == pynput_kb.Key.shift or key == pynput_kb.Key.shift_l or key == pynput_kb.Key.shift_r:
                    self.current_modifiers.add('shift')
                elif key == pynput_kb.Key.cmd or key == pynput_kb.Key.cmd_l or key == pynput_kb.Key.cmd_r:
                    self.current_modifiers.add('cmd')
                
                # Check for trigger key
                elif hasattr(key, 'char') and key.char:
                    if key.char.lower() == self.trigger_key:
                        if self.current_modifiers == self.required_modifiers:
                            self.callback()
            except Exception:
                pass

        def on_release(self, key):
            try:
                if key == pynput_kb.Key.ctrl or key == pynput_kb.Key.ctrl_l or key == pynput_kb.Key.ctrl_r:
                    self.current_modifiers.discard('ctrl')
                elif key == pynput_kb.Key.alt or key == pynput_kb.Key.alt_l or key == pynput_kb.Key.alt_r:
                    self.current_modifiers.discard('alt')
                elif key == pynput_kb.Key.shift or key == pynput_kb.Key.shift_l or key == pynput_kb.Key.shift_r:
                    self.current_modifiers.discard('shift')
                elif key == pynput_kb.Key.cmd or key == pynput_kb.Key.cmd_l or key == pynput_kb.Key.cmd_r:
                    self.current_modifiers.discard('cmd')
            except Exception:
                pass

        def start(self):
            print(f"[*] Bound Native Mac Hotkey (Raw Listener)")
            # Using the raw Listener bypasses the HIToolbox layout query entirely!
            self.listener = pynput_kb.Listener(on_press=self.on_press, on_release=self.on_release)
            self.listener.start()

        def stop(self):
            if self.listener:
                self.listener.stop()


class PluginBase:
    def __init__(self, app):
        self.app = app
        self._hotkey_thread = None

    def setup(self):
        pass

    def config_updated(self):
        pass

    def bind_native_hotkey(self, hotkey_str, callback):
        if self._hotkey_thread:
            self._hotkey_thread.stop()
            self._hotkey_thread = None
        
        if hotkey_str:
            self._hotkey_thread = NativeHotkeyThread(hotkey_str, callback)
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