import os
import sys
import ctypes
from ctypes import wintypes
import threading

# Native Windows API Constants
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
MOD_ALT = 0x0001
MOD_CTRL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

# Standard Virtual Key Code Mapping
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
        
        # Parse the string (e.g., "ctrl+alt+c") into native modifiers and VK codes
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
        
        # Attempt to register with the OS
        if not ctypes.windll.user32.RegisterHotKey(None, self.hotkey_id, modifiers, vk):
            print(f"[!] Failed to register native hotkey: {self.hotkey_str} (May be in use by another app)")
            return

        print(f"[*] Bound Native Windows Hotkey: {self.hotkey_str}")

        # The Windows Message Loop - Puts the thread to sleep until the exact hotkey is pressed!
        msg = wintypes.MSG()
        while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                self.callback()
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

        # Cleanup if the loop exits
        ctypes.windll.user32.UnregisterHotKey(None, self.hotkey_id)

    def stop(self):
        """Cleanly forces the Windows Message loop to exit so a new hotkey can be bound."""
        if self.thread_id:
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, WM_QUIT, 0, 0)


class PluginBase:
    """Base class for all plugins."""
    def __init__(self, app):
        self.app = app
        self._hotkey_thread = None

    def setup(self):
        pass

    def config_updated(self):
        pass

    def bind_native_hotkey(self, hotkey_str, callback):
        """Allows any plugin to securely bind a Windows API hotkey."""
        if self._hotkey_thread:
            self._hotkey_thread.stop()
            self._hotkey_thread = None
        
        if hotkey_str:
            self._hotkey_thread = NativeHotkeyThread(hotkey_str, callback)
            self._hotkey_thread.start()

    def get_resource_path(self, relative_path):
        """Safely gets absolute paths for resources, compatible with PyInstaller EXEs."""
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
        """Fires an event across all loaded plugins."""
        for plugin in self.plugins:
            method = getattr(plugin, event_name, None)
            if callable(method):
                method(*args, **kwargs)