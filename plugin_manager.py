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
    import AppKit
    import ApplicationServices

    MAC_VK_CODES = {
        'a': 0x00, 's': 0x01, 'd': 0x02, 'f': 0x03, 'h': 0x04, 'g': 0x05, 'z': 0x06, 'x': 0x07,
        'c': 0x08, 'v': 0x09, 'b': 0x0B, 'q': 0x0C, 'w': 0x0D, 'e': 0x0E, 'r': 0x0F, 'y': 0x10,
        't': 0x11, '1': 0x12, '2': 0x13, '3': 0x14, '4': 0x15, '6': 0x16, '5': 0x17, '=': 0x18,
        '9': 0x19, '7': 0x1A, '-': 0x1B, '8': 0x1C, '0': 0x1D, ']': 0x1E, 'o': 0x1F, 'u': 0x20,
        '[': 0x21, 'i': 0x22, 'p': 0x23, 'l': 0x25, 'j': 0x26, '\'': 0x27, 'k': 0x28, ';': 0x29,
        '\\': 0x2A, ',': 0x2B, '/': 0x2C, 'n': 0x2D, 'm': 0x2E, '.': 0x2F, '`': 0x32, 'space': 0x31,
        'enter': 0x24, 'tab': 0x30, 'esc': 0x35
    }

    class NativeHotkeyThread:
        def __init__(self, hotkey_str, callback, app_ref):
            self.hotkey_str = hotkey_str
            self.callback = callback
            self.app_ref = app_ref
            self.global_monitor = None
            self.local_monitor = None
            
            parts = hotkey_str.lower().split('+')
            self.req_ctrl = False
            self.req_alt = False
            self.req_shift = False
            self.req_cmd = False
            self.req_vk = None
            
            for part in parts:
                part = part.strip()
                if part == 'ctrl': self.req_ctrl = True
                elif part == 'alt': self.req_alt = True
                elif part == 'shift': self.req_shift = True
                elif part in ('win', 'cmd'): self.req_cmd = True
                elif part in MAC_VK_CODES: self.req_vk = MAC_VK_CODES[part]

        def _check_event(self, event):
            flags = event.modifierFlags()
            has_ctrl = bool(flags & AppKit.NSEventModifierFlagControl)
            has_alt = bool(flags & AppKit.NSEventModifierFlagOption)
            has_shift = bool(flags & AppKit.NSEventModifierFlagShift)
            has_cmd = bool(flags & AppKit.NSEventModifierFlagCommand)
            
            if (has_ctrl == self.req_ctrl and has_alt == self.req_alt and 
                has_shift == self.req_shift and has_cmd == self.req_cmd):
                if event.keyCode() == self.req_vk:
                    # Fire callback in a separate thread so we don't stall the macOS Event Stream!
                    threading.Thread(target=self.callback, daemon=True).start()
                    return True
            return False

        def _global_handler(self, event):
            self._check_event(event)

        def _local_handler(self, event):
            if self._check_event(event):
                return None 
            return event

        def start(self):
            if self.req_vk is None:
                return

            if not ApplicationServices.AXIsProcessTrusted():
                print("[!] macOS Accessibility Permissions missing!")
                if self.app_ref:
                    self.app_ref.root.after(1000, lambda: self.app_ref.show_toast(
                        "⚠️ macOS Accessibility Permissions required for Hotkeys!\nGo to System Settings -> Privacy & Security -> Accessibility", 5000))

            print(f"[*] Bound Native macOS Cocoa Hotkey: {self.hotkey_str}")
            mask = 1 << 10 # NSEventMaskKeyDown
            
            # Since these are created on the Main Tkinter Thread, they use the native macOS RunLoop seamlessly!
            self.global_monitor = AppKit.NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(mask, self._global_handler)
            self.local_monitor = AppKit.NSEvent.addLocalMonitorForEventsMatchingMask_handler_(mask, self._local_handler)

        def stop(self):
            if self.global_monitor:
                AppKit.NSEvent.removeMonitor_(self.global_monitor)
                self.global_monitor = None
            if self.local_monitor:
                AppKit.NSEvent.removeMonitor_(self.local_monitor)
                self.local_monitor = None


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
            if IS_MAC:
                # IMPORTANT: On Mac, we don't start a thread. We just register the monitors on the Main UI thread!
                self._hotkey_thread = NativeHotkeyThread(hotkey_str, callback, self.app)
                self._hotkey_thread.start()
            else:
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