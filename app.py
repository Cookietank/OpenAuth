import sys
import os
import datetime

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

if IS_WIN:
    APPDATA_DIR = os.path.join(os.getenv('APPDATA', ''), 'OpenAuth')
elif IS_MAC:
    APPDATA_DIR = os.path.expanduser('~/Library/Application Support/OpenAuth')
else:
    APPDATA_DIR = os.path.abspath('OpenAuth_Data')

if not os.path.exists(APPDATA_DIR):
    os.makedirs(APPDATA_DIR)

LOG_FILE = os.path.join(APPDATA_DIR, "openauth.log")

class SafeLogger:
    def __init__(self, filename, is_stdout=True):
        self.terminal = sys.stdout if is_stdout else sys.stderr
        self.log = open(filename, "a", encoding="utf-8")

    def write(self, message):
        if self.terminal:
            try: self.terminal.write(message)
            except: pass
        if self.log:
            try: 
                self.log.write(message)
                self.log.flush()
            except: pass

    def flush(self):
        if self.terminal:
            try: self.terminal.flush()
            except: pass
        if self.log:
            try: self.log.flush()
            except: pass

    def close(self):
        if self.log:
            try: self.log.close()
            except: pass

APP_VERSION = "v0.1.6.0"

with open(LOG_FILE, 'a', encoding='utf-8') as f:
    f.write(f"\n\n[{datetime.datetime.now()}] === NEW OPENAUTH SESSION ({APP_VERSION}) ===\n")

sys.stdout = SafeLogger(LOG_FILE, is_stdout=True)
sys.stderr = SafeLogger(LOG_FILE, is_stdout=False)

# --- PROTECTED OS IMPORTS ---
if IS_WIN:
    import ctypes
    import winreg

# --- STANDARD IMPORTS ---
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as messagebox
import time
import json
import secrets
import subprocess
import webbrowser
import threading
import urllib.request
import urllib.error
import re
import shutil 
import socket
import struct
import random
from PIL import Image, ImageDraw, ImageTk

from core import StandardAuthAccount
from plugin_manager import PluginManager

# --- Core Plugins ---
from plugins.qr_scanner import ScreenQRScannerPlugin
from plugins.manual_entry import ManualEntryPlugin
from plugins.tray_icon import TrayIconPlugin
from plugins.tutorial import TutorialPlugin

# --- Toggleable Plugins ---
from plugins.backup_export import BackupExportPlugin  
from plugins.secure_storage import SecureStoragePlugin
from plugins.broadcaster import LocalBroadcasterPlugin
from plugins.auto_login import AutoLoginPlugin
from plugins.virtual_yubikey import VirtualYubiKeyPlugin
from plugins.tailscale_sync import TailscaleSyncPlugin

GITHUB_REPO = "cookietank/OpenAuth"
CONFIG_FILE = os.path.join(APPDATA_DIR, "app_config.json")

# =========================================================================
# SILENT COMMAND-LINE UNINSTALLER
# =========================================================================
if "--uninstall" in sys.argv:
    if IS_WIN:
        try:
            import keyring
            keyring.delete_password("ModularDesktopAuthenticator", "TOTP_Secrets")
        except Exception: pass
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
            winreg.DeleteValue(key, "OpenAuth")
            winreg.CloseKey(key)
        except Exception: pass
        vbs_path = os.path.join(os.getenv('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs\Startup\OpenAuth.vbs')
        if os.path.exists(vbs_path):
            try: os.remove(vbs_path)
            except: pass

    if os.path.exists(APPDATA_DIR):
        shutil.rmtree(APPDATA_DIR, ignore_errors=True)

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Uninstall Complete", "OpenAuth has been completely removed from your system.\n\nYou can now safely delete the executable.")
    sys.exit(0)

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

CORE_PLUGINS = {
    "Tray Icon": TrayIconPlugin,
    "Screen QR Scanner": ScreenQRScannerPlugin,
    "Manual Entry": ManualEntryPlugin,
    "Tutorial": TutorialPlugin
}

TOGGLEABLE_PLUGINS = {
    "Backup & Export": BackupExportPlugin,
    "Copy Code to Clipboard": VirtualYubiKeyPlugin,
    "Auto-Login": AutoLoginPlugin,
    "Local Broadcaster": LocalBroadcasterPlugin,
    "Tailscale Phone Sync": TailscaleSyncPlugin
}

PLUGIN_DESCRIPTIONS = {
    "Backup & Export": "Allows you to securely view and export your raw 2FA secrets to backup in a password manager.",
    "Copy Code to Clipboard": "Provides a global keyboard shortcut to instantly copy (or paste) your primary code.",
    "Auto-Login": "Uses an automated keystroke macro to automatically navigate the Microsoft login screen, pasting the current code and handling login for you.",
    "Local Broadcaster": "Broadcasts codes over local UDP for external app integration.",
    "Tailscale Phone Sync": "Hosts a secure API to send codes instantly to your phone via Tailscale VPN."
}

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tw = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + 25
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x}+{y}")
        self.tw.attributes("-topmost", True)
        
        label = tk.Label(self.tw, text=self.text, justify='left',
                         background="#2d2d2d", foreground="white", relief='solid', borderwidth=1,
                         font=("tahoma", "9", "normal"), padx=8, pady=4)
        label.pack(ipadx=1)

    def leave(self, event=None):
        if self.tw:
            self.tw.destroy()
            self.tw = None

class DesktopAuthenticator:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenAuth")
        self.root.minsize(400, 150)
        self.root.attributes("-topmost", True)
        self.settings_window = None 
        
        if "--tray" in sys.argv:
            self.root.withdraw()
        
        self.accounts =[]
        self.update_job = None
        self.account_ui_hooks = []
        self.tick_hooks =[]
        
        self.config = {
            "version": "v0.0.0",
            "show_tutorial": True,
            "auto_update": True,
            "start_on_boot": False,
            "understood_tray": False,
            "privacy_mode": False, 
            "theme": "Automatic",  
            "plugins": {
                "Backup & Export": True,
                "Copy Code to Clipboard": True,
                "Auto-Login": True,
                "Local Broadcaster": False,
                "Tailscale Phone Sync": False
            },
            "hotkeys": {
                "Copy Code to Clipboard": "ctrl+alt+c",
                "Auto-Login": "ctrl+alt+q",
                "auto_paste": False,
                "auto_login_delay": 0.8,
                "auto_login_ways": 2
            },
            "tailscale": {
                "port": 50051,
                "api_token": ""
            }
        }
        self.load_config()
        self.apply_theme_colors()

        try:
            self.tk_icon = ImageTk.PhotoImage(self.get_icon_image())
            self.root.iconphoto(True, self.tk_icon)
        except Exception:
            pass

        self.root.protocol("WM_DELETE_WINDOW", self.send_to_tray)
        
        self.toolbar = tk.Frame(root, bd=1, relief=tk.RAISED, bg=self.colors['bg'])
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        
        self.auth_menu_btn = ttk.Menubutton(self.toolbar, text="➕ Add Auth Key")
        self.auth_menu = tk.Menu(self.auth_menu_btn, tearoff=0, bg=self.colors['frame_bg'], fg=self.colors['fg'])
        self.auth_menu_btn.configure(menu=self.auth_menu)
        self.auth_menu_btn.pack(side=tk.LEFT, padx=5, pady=2)

        self.add_toolbar_action("Quit", self.quit_app_prompt, side=tk.RIGHT)
        self.add_toolbar_action("Settings", self.open_settings, side=tk.RIGHT)
        
        self.main_frame = tk.Frame(root, bg=self.colors['bg'])
        self.main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        if IS_MAC:
            try: urllib.request.getproxies()
            except: pass

        self.plugin_manager = PluginManager(self)
        self.load_plugins()

        self.update_codes()
        self.resize_main_window()

        if self.config.get("version") != APP_VERSION:
            self.config["version"] = APP_VERSION
            self.save_config()
            
            if self.config.get("start_on_boot", False):
                self.manage_startup(True)
                
            if self.config.get("show_tutorial", True):
                self.root.after(500, lambda: self.plugin_manager.broadcast('open_tutorial'))

        if getattr(sys, 'frozen', False) and self.config.get("auto_update", True):
            threading.Thread(target=self.check_for_updates, daemon=True).start()

        threading.Thread(target=self.check_time_drift, daemon=True).start()

    def get_os_theme(self):
        if IS_WIN:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                val, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                return "Light" if val == 1 else "Dark"
            except Exception:
                return "Light" 
        elif IS_MAC:
            try:
                out = subprocess.check_output(['defaults', 'read', '-g', 'AppleInterfaceStyle'], stderr=subprocess.DEVNULL)
                if out.strip() == b'Dark':
                    return "Dark"
            except Exception:
                pass
        return "Light"

    def send_to_tray(self):
        for p in self.plugin_manager.plugins:
            if type(p).__name__ == "TrayIconPlugin":
                p.minimize_to_tray()
                return
        self.force_quit_app()

    def quit_app_prompt(self):
        if messagebox.askyesno("Quit OpenAuth", "Are you sure you want to quit OpenAuth?\n\nYou will not be able to use Hotkeys or Auto-Login while the application is closed.", parent=self.root):
            self.force_quit_app()

    def force_quit_app(self):
        if self.update_job is not None:
            self.root.after_cancel(self.update_job)
        self.root.destroy()
        os._exit(0)

    def get_resource_path(self, relative_path):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

    def show_toast(self, message, duration=2500):
        if IS_MAC:
            safe_msg = message.replace('"', "'")
            os.system(f"""osascript -e 'display notification "{safe_msg}" with title "OpenAuth"'""")
            return

        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.attributes('-topmost', True)
        toast.configure(bg="#2d2d2d", bd=1, relief=tk.SOLID)
        
        lbl = tk.Label(toast, text=message, fg="white", bg="#2d2d2d", font=("Helvetica", 10), padx=15, pady=10)
        lbl.pack()
        
        self.root.update_idletasks()
        x = toast.winfo_screenwidth() - toast.winfo_width() - 20
        y = toast.winfo_screenheight() - toast.winfo_height() - 60
        toast.geometry(f"+{x}+{y}")
        
        self.root.after(duration, toast.destroy)

    def check_time_drift(self):
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            client.settimeout(3)
            client.sendto(b'\x1b' + 47 * b'\0', ('pool.ntp.org', 123))
            msg, _ = client.recvfrom(1024)
            ntp_time = struct.unpack("!12I", msg)[10] - 2208988800
            local_time = time.time()
            
            drift = abs(ntp_time - local_time)
            print(f"[*] System Clock NTP Drift: {drift:.2f} seconds")
            
            if drift > 15: 
                warning_msg = (
                    "⚠️ CRITICAL WARNING: TIME DRIFT DETECTED ⚠️\n\n"
                    f"Your OS clock is out of sync by {drift:.0f} seconds.\n\n"
                    "2FA codes rely on mathematically perfect timing. If your clock is out of sync, "
                    "Microsoft and other services will completely REJECT your codes!\n\n"
                    "Please adjust your system date/time and click 'Sync Now' immediately."
                )
                self.root.after(0, lambda: messagebox.showwarning("Clock Out of Sync", warning_msg))
        except Exception as e:
            print(f"NTP Time check failed or offline: {e}")

    def resize_main_window(self):
        self.root.update_idletasks() 
        num_accounts = len(self.accounts)
        base_height = 50 
        acc_height = 110 
        
        if num_accounts == 0:
            calc_height = 150
        else:
            calc_height = base_height + (min(num_accounts, 3) * acc_height) + 20
            
        self.root.geometry(f"500x{calc_height}")

    def add_auth_action(self, text, command):
        self.auth_menu.add_command(label=text, command=command)

    def trigger_backup_export(self):
        for p in self.plugin_manager.plugins:
            if type(p).__name__ == "BackupExportPlugin":
                p.open_export_ui()
                return
        messagebox.showerror("Error", "Backup & Export plugin is not enabled in the 'Plugins' tab!")

    def check_for_updates(self):
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'OpenAuth-Updater'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get('tag_name', '')
                
                if latest_version:
                    def get_v_tuple(v_str):
                        return tuple(map(int, re.findall(r'\d+', v_str)))
                    
                    latest_tuple = get_v_tuple(latest_version)
                    current_tuple = get_v_tuple(APP_VERSION)
                    
                    if latest_tuple > current_tuple:
                        download_url = None
                        asset_name = f"OpenAuth_{latest_version}.exe" if IS_WIN else f"OpenAuth_{latest_version}"
                        
                        for asset in data.get('assets', []):
                            if IS_WIN and asset['name'].endswith('.exe'):
                                download_url = asset['browser_download_url']
                                asset_name = asset['name'] 
                                break
                            elif IS_MAC and not asset['name'].endswith('.exe'):
                                pass
                                
                        if download_url and IS_WIN:
                            self.root.after(0, lambda: self.prompt_update(latest_version, download_url, asset_name))
        except Exception as e:
            print(f"Update check failed: {e}")

    def prompt_update(self, latest_version, download_url, asset_name):
        if messagebox.askyesno("Update Available", f"A new version of OpenAuth ({latest_version}) is available!\n\nWould you like to automatically download and install it now?"):
            threading.Thread(target=self.perform_update, args=(download_url, asset_name), daemon=True).start()

    def perform_update(self, download_url, asset_name):
        self.show_toast("Downloading update... Please wait.", 5000)
                
        try:
            current_exe = sys.executable
            exe_dir = os.path.dirname(current_exe)
            final_exe = os.path.join(exe_dir, asset_name)
            
            if current_exe != final_exe:
                download_target = final_exe
            else:
                download_target = current_exe + ".update"
            
            req = urllib.request.Request(download_url, headers={'User-Agent': 'OpenAuth-Updater'})
            with urllib.request.urlopen(req) as response, open(download_target, 'wb') as out_file:
                out_file.write(response.read())
                
            self.apply_update_and_restart(download_target, final_exe, current_exe)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Update Failed", f"Failed to download update:\n{e}"))

    def apply_update_and_restart(self, download_target, final_exe, current_exe):
        if self.config.get("start_on_boot", False):
            self.manage_startup(True, exe_override=final_exe)
            
        if IS_WIN:
            bat_path = os.path.join(os.path.dirname(current_exe), "apply_openauth_update.bat")
            if current_exe != final_exe:
                bat_content = f'''@echo off\n:wait\ntimeout /t 1 /nobreak > NUL\ndel "{current_exe}"\nif exist "{current_exe}" goto wait\nstart "" "{final_exe}"\ndel "%~f0"\n'''
            else:
                bat_content = f'''@echo off\n:wait\ntimeout /t 1 /nobreak > NUL\ndel "{current_exe}"\nif exist "{current_exe}" goto wait\nmove /Y "{download_target}" "{final_exe}"\nstart "" "{final_exe}"\ndel "%~f0"\n'''

            with open(bat_path, "w") as f:
                f.write(bat_content)
                
            env = os.environ.copy()
            env.pop('_MEIPASS', None)
            env.pop('_MEIPASS2', None)
            env.pop('TCL_LIBRARY', None)
            env.pop('TK_LIBRARY', None)
                
            subprocess.Popen(bat_path, shell=True, env=env, creationflags=0x00000008)
        
        os._exit(0)

    def get_icon_image(self):
        icon_path = self.get_resource_path(os.path.join('plugins', 'icon.ico'))
        if os.path.exists(icon_path):
            return Image.open(icon_path)
            
        image = Image.new('RGBA', (64, 64), color=(255, 255, 255, 0))
        draw = ImageDraw.Draw(image)
        draw.polygon([(32, 4), (8, 16), (8, 40), (32, 60), (56, 40), (56, 16)], fill="#005A9E")
        draw.ellipse([(26, 22), (38, 34)], fill="white")
        draw.polygon([(30, 32), (34, 32), (34, 48), (30, 48)], fill="white")
        return image

    def apply_theme_colors(self):
        theme_setting = self.config.get("theme", "Automatic")
        if theme_setting == "Automatic":
            theme_choice = self.get_os_theme()
        else:
            theme_choice = theme_setting
            
        is_dark = theme_choice == "Dark"
        
        self.colors = {
            "bg": "#1e1e1e" if is_dark else "SystemButtonFace",
            "fg": "#ffffff" if is_dark else "black",
            "frame_bg": "#2d2d2d" if is_dark else "white",
            "entry_bg": "#333333" if is_dark else "white",
            "highlight": "#004060" if is_dark else "#e6f2ff",
            "primary_text": "#4da6ff" if is_dark else "green",
            "code": "#66b3ff" if is_dark else "#005A9E",
            "handle": "#aaaaaa" if is_dark else "gray"
        }
        
        self.root.configure(bg=self.colors['bg'])
        if hasattr(self, 'toolbar'):
            self.toolbar.configure(bg=self.colors['bg'])
        if hasattr(self, 'main_frame'):
            self.main_frame.configure(bg=self.colors['bg'])
            if hasattr(self, 'auth_menu'):
                self.auth_menu.configure(bg=self.colors['frame_bg'], fg=self.colors['fg'])

        style = ttk.Style()
        try:
            if is_dark:
                style.theme_use('clam')
                style.configure('.', background=self.colors['bg'], foreground=self.colors['fg'])
                style.configure('TButton', background="#333333", foreground="white")
                style.map('TButton', background=[('active', '#555555')])
                style.configure('TNotebook', background=self.colors['bg'])
                style.configure('TNotebook.Tab', background="#333333", foreground="white")
                style.map('TNotebook.Tab', background=[('selected', self.colors['frame_bg'])])
                style.configure('TCheckbutton', background=self.colors['bg'], foreground=self.colors['fg'])
                style.map('TCheckbutton', background=[('active', self.colors['bg'])])
                
                style.map('TCombobox', 
                          fieldbackground=[('readonly', self.colors['entry_bg'])],
                          selectbackground=[('readonly', self.colors['highlight'])],
                          foreground=[('readonly', self.colors['fg'])])
                self.root.option_add('*TCombobox*Listbox.background', self.colors['entry_bg'])
                self.root.option_add('*TCombobox*Listbox.foreground', self.colors['fg'])
                self.root.option_add('*TCombobox*Listbox.selectBackground', self.colors['highlight'])
            else:
                if 'vista' in style.theme_names():
                    style.theme_use('vista')
                else:
                    style.theme_use('clam')
        except Exception:
            pass

    def create_styled_entry(self, parent, text_var, state="normal"):
        return tk.Entry(parent, textvariable=text_var, state=state, 
                        bg=self.colors['entry_bg'], fg=self.colors['fg'], 
                        readonlybackground=self.colors['entry_bg'],
                        insertbackground=self.colors['fg'], 
                        relief=tk.SOLID, borderwidth=1)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    saved_config = json.load(f)
                    self.config["version"] = saved_config.get("version", "v0.0.0")
                    self.config["show_tutorial"] = saved_config.get("show_tutorial", True)
                    self.config["auto_update"] = saved_config.get("auto_update", True)
                    self.config["start_on_boot"] = saved_config.get("start_on_boot", False)
                    self.config["understood_tray"] = saved_config.get("understood_tray", False)
                    self.config["privacy_mode"] = saved_config.get("privacy_mode", False)
                    self.config["theme"] = saved_config.get("theme", "Automatic")
                    
                    self.config["plugins"].update(saved_config.get("plugins", {}))
                    self.config["hotkeys"].update(saved_config.get("hotkeys", {}))
                    self.config["tailscale"].update(saved_config.get("tailscale", {}))
            except Exception:
                pass
                
        if not self.config.get("tailscale", {}).get("api_token"):
            self.config.setdefault("tailscale", {})["api_token"] = secrets.token_hex(16)
            self.save_config()

    def save_config(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f, indent=4)

    def manage_startup(self, enable, exe_override=None):
        if IS_WIN:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "OpenAuth"
            
            vbs_path = os.path.join(os.getenv('APPDATA', ''), r'Microsoft\Windows\Start Menu\Programs\Startup\OpenAuth.vbs')
            if os.path.exists(vbs_path):
                try: os.remove(vbs_path)
                except: pass

            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
                if enable:
                    if getattr(sys, 'frozen', False):
                        target_exe = exe_override if exe_override else sys.executable
                        app_path = f'"{target_exe}" --tray'
                    else:
                        pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")
                        script_path = os.path.abspath(sys.argv[0])
                        app_path = f'"{pythonw_path}" "{script_path}" --tray'
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
                else:
                    try: winreg.DeleteValue(key, app_name)
                    except FileNotFoundError: pass
                winreg.CloseKey(key)
            except Exception as e:
                print(f"Failed to manage startup registry: {e}")
        elif IS_MAC:
            import plistlib
            plist_path = os.path.expanduser('~/Library/LaunchAgents/com.cookietank.openauth.plist')
            if enable:
                plist_dict = {
                    "Label": "com.cookietank.openauth",
                    "ProgramArguments": [sys.executable, "--tray"] if getattr(sys, 'frozen', False) else [sys.executable, os.path.abspath(sys.argv[0]), "--tray"],
                    "RunAtLoad": True,
                    "KeepAlive": False
                }
                try:
                    with open(plist_path, 'wb') as f:
                        plistlib.dump(plist_dict, f)
                except Exception as e:
                    print(f"Failed to set Mac startup: {e}")
            else:
                if os.path.exists(plist_path):
                    try: os.remove(plist_path)
                    except: pass

    def report_issue(self):
        issue_win = tk.Toplevel(self.root)
        issue_win.title("Report an Issue")
        issue_win.geometry("400x380")
        issue_win.attributes("-topmost", True)
        issue_win.configure(bg=self.colors['bg'])

        tk.Label(issue_win, text="🐞 Report a Bug / Issue", font=("Helvetica", 14, "bold"), bg=self.colors['bg'], fg=self.colors['fg']).pack(pady=15)

        steps = (
            "1. A bug report template has been copied to your clipboard.\n\n"
            "2. Click 'Open Log Folder' below to find 'openauth.log'. You can drag this file directly into your GitHub issue to help us debug!\n\n"
            "3. Click 'Copy Template & Open GitHub' to open the official Issues page.\n\n"
            "4. Paste (Ctrl+V) the template and explain what went wrong."
        )

        msg = tk.Message(issue_win, text=steps, bg=self.colors['bg'], fg=self.colors['fg'], width=350, justify=tk.LEFT)
        msg.pack(padx=20, pady=10)

        def open_log_folder():
            if IS_WIN: os.startfile(APPDATA_DIR)
            elif IS_MAC: subprocess.call(["open", APPDATA_DIR])

        def open_and_close():
            template = f"**OpenAuth Version:** {APP_VERSION}\n**OS:** {sys.platform}\n\n**Bug Description:**\n[Describe what went wrong here]\n\n**Steps to Reproduce:**\n1. \n2. "
            self.root.clipboard_clear()
            self.root.clipboard_append(template)
            self.root.update()
            webbrowser.open(f"https://github.com/{GITHUB_REPO}/issues")
            issue_win.destroy()

        ttk.Button(issue_win, text="1. Open Log Folder", command=open_log_folder).pack(pady=(10, 5))
        ttk.Button(issue_win, text="2. Copy Template & Open GitHub", command=open_and_close).pack(pady=5)

    def factory_reset(self):
        warning = ("⚠️ UNINSTALL & FACTORY RESET ⚠️\n\n"
                   "This will PERMANENTLY DELETE:\n"
                   "- All your saved 2FA Secret Keys\n"
                   "- All application settings & logs\n"
                   "- Your Tailscale API Token\n"
                   f"- OpenAuth from {'macOS Startup' if IS_MAC else 'Windows Startup'}\n\n"
                   "Are you absolutely sure you want to wipe OpenAuth from this computer?")
        if messagebox.askyesno("Factory Reset", warning, icon="warning", parent=self.settings_window):
            try:
                self.manage_startup(False)
                if IS_WIN:
                    import keyring
                    try: keyring.delete_password("ModularDesktopAuthenticator", "TOTP_Secrets")
                    except: pass
                
                sys.stdout.close()
                sys.stderr.close()
                
                shutil.rmtree(APPDATA_DIR, ignore_errors=True)
                
                messagebox.showinfo("Uninstall Complete", "OpenAuth has been completely wiped from your system.\n\nThe application will now close. You can safely delete the executable.")
                os._exit(0)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to completely wipe data:\n{e}")

    def open_settings(self):
        if hasattr(self, 'settings_window') and self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return
            
        self.settings_window = tk.Toplevel(self.root)
        top = self.settings_window
        top.title("OpenAuth Settings")
        top.geometry("450x640")
        top.attributes("-topmost", True)
        top.configure(bg=self.colors['bg'])

        notebook = ttk.Notebook(top)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        plugin_vars = {}

        # TAB 1: General
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")
        
        boot_var = tk.BooleanVar(value=self.config.get("start_on_boot", False))
        os_name = "macOS" if IS_MAC else "Windows"
        ttk.Checkbutton(general_frame, text=f"Start OpenAuth silently on login ({os_name})", variable=boot_var).pack(anchor="w", padx=10, pady=(15, 5))
        
        update_var = tk.BooleanVar(value=self.config.get("auto_update", True))
        ttk.Checkbutton(general_frame, text="Check for updates automatically on launch", variable=update_var).pack(anchor="w", padx=10, pady=5)
        
        tut_var = tk.BooleanVar(value=self.config.get("show_tutorial", True))
        ttk.Checkbutton(general_frame, text="Show Tutorial on App Updates", variable=tut_var).pack(anchor="w", padx=10, pady=5)

        privacy_var = tk.BooleanVar(value=self.config.get("privacy_mode", False))
        ttk.Checkbutton(general_frame, text="Privacy Mode (Hide codes until hovered)", variable=privacy_var).pack(anchor="w", padx=10, pady=5)
        
        tk.Label(general_frame, text="App Theme:", bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor="w", padx=10, pady=(10, 0))
        theme_var = tk.StringVar(value=self.config.get("theme", "Automatic"))
        ttk.Combobox(general_frame, textvariable=theme_var, values=["Automatic", "Light", "Dark"], state="readonly").pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(general_frame, text=f"OpenAuth Version: {APP_VERSION}", bg=self.colors['bg'], fg=self.colors['handle']).pack(anchor="w", padx=10, pady=(30, 0))
        
        ttk.Button(general_frame, text="Report an Issue / Bug", command=self.report_issue).pack(anchor="w", padx=10, pady=(5, 0))

        # TAB 2: Plugins & Hotkeys
        plugin_frame = ttk.Frame(notebook)
        notebook.add(plugin_frame, text="Plugins & Hotkeys")
        
        tk.Label(plugin_frame, text="Optional Modules", font=("Helvetica", 9, "bold"), bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor="w", padx=10, pady=(10, 2))

        automation_plugins = ["Copy Code to Clipboard", "Auto-Login"]
        for name in automation_plugins:
            var = tk.BooleanVar(value=self.config["plugins"].get(name, TOGGLEABLE_PLUGINS.get(name) is not None))
            plugin_vars[name] = var
            chk = ttk.Checkbutton(plugin_frame, text=f"Enable {name}", variable=var)
            chk.pack(anchor="w", padx=10, pady=2)
            ToolTip(chk, PLUGIN_DESCRIPTIONS.get(name, ""))

        ttk.Separator(plugin_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)

        hk_vars = {}
        for name in ["Copy Code to Clipboard", "Auto-Login"]:
            tk.Label(plugin_frame, text=f"{name} Shortcut:", bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor="w", padx=10, pady=(5, 0))
            var = tk.StringVar(value=self.config["hotkeys"].get(name, ""))
            hk_vars[name] = var
            self.create_styled_entry(plugin_frame, var).pack(fill=tk.X, padx=10, pady=(0, 5), ipady=3)

        auto_paste_var = tk.BooleanVar(value=self.config["hotkeys"].get("auto_paste", False))
        ap_chk = ttk.Checkbutton(plugin_frame, text="Auto-Paste Code (Inject Keystrokes & Press Enter)", variable=auto_paste_var)
        ap_chk.pack(anchor="w", padx=10, pady=(5, 0))

        delay_var = tk.StringVar(value=str(self.config["hotkeys"].get("auto_login_delay", 0.8)))
        tk.Label(plugin_frame, text="Auto-Login Network Delay (seconds):", bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor="w", padx=10, pady=(5, 0))
        delay_entry = self.create_styled_entry(plugin_frame, delay_var)
        delay_entry.pack(fill=tk.X, padx=10, pady=(0, 5), ipady=3)
        
        ways_var = tk.StringVar(value=str(self.config["hotkeys"].get("auto_login_ways", 2)))
        tk.Label(plugin_frame, text="Auto-Login 'Ways to Verify' count:", bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor="w", padx=10, pady=(5, 0))
        ways_entry = self.create_styled_entry(plugin_frame, ways_var)
        ways_entry.pack(fill=tk.X, padx=10, pady=(0, 5), ipady=3)

        # TAB 3: Advanced
        adv_frame = ttk.Frame(notebook)
        notebook.add(adv_frame, text="Advanced")

        tk.Label(adv_frame, text="Account Backup", font=("Helvetica", 9, "bold"), bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor="w", padx=10, pady=(10, 2))
        
        backup_var = tk.BooleanVar(value=self.config["plugins"].get("Backup & Export", True))
        plugin_vars["Backup & Export"] = backup_var
        chk_backup = ttk.Checkbutton(adv_frame, text="Enable Backup & Export", variable=backup_var)
        chk_backup.pack(anchor="w", padx=10, pady=2)
        ToolTip(chk_backup, PLUGIN_DESCRIPTIONS.get("Backup & Export", ""))
        
        ttk.Button(adv_frame, text="Export Accounts / Secret Keys", command=self.trigger_backup_export).pack(fill=tk.X, padx=10, pady=5)
        ttk.Separator(adv_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)

        tk.Label(adv_frame, text="Network & Broadcast Modules", font=("Helvetica", 9, "bold"), bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor="w", padx=10, pady=(10, 2))

        adv_plugins = ["Local Broadcaster", "Tailscale Phone Sync"]
        for name in adv_plugins:
            var = tk.BooleanVar(value=self.config["plugins"].get(name, False))
            plugin_vars[name] = var
            chk = ttk.Checkbutton(adv_frame, text=f"Enable {name}", variable=var)
            chk.pack(anchor="w", padx=10, pady=2)
            ToolTip(chk, PLUGIN_DESCRIPTIONS.get(name, ""))

        ttk.Separator(adv_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)

        tk.Label(adv_frame, text="Tailscale Server Port:", font=("Helvetica", 9, "bold"), bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor="w", padx=10, pady=(5, 2))
        port_var = tk.StringVar(value=str(self.config["tailscale"].get("port", 50051)))
        self.create_styled_entry(adv_frame, port_var).pack(fill=tk.X, padx=10, pady=2, ipady=3)

        tk.Label(adv_frame, text="Tailscale Secret API Token:", font=("Helvetica", 9, "bold"), bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor="w", padx=10, pady=(15, 2))
        token_frame = tk.Frame(adv_frame, bg=self.colors['bg'])
        token_frame.pack(fill=tk.X, padx=10)
        
        token_var = tk.StringVar(value=self.config["tailscale"].get("api_token", ""))
        self.create_styled_entry(token_frame, token_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        def regen_token():
            if messagebox.askyesno("Confirm", "Regenerate token? You will need to update your phone's shortcut."):
                new_tok = secrets.token_hex(16)
                self.config["tailscale"]["api_token"] = new_tok
                token_var.set(new_tok)

        ttk.Button(token_frame, text="↻", width=3, command=regen_token).pack(side=tk.LEFT, padx=5)

        ttk.Separator(adv_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(adv_frame, text="Danger Zone", font=("Helvetica", 9, "bold"), bg=self.colors['bg'], fg="red").pack(anchor="w", padx=10, pady=(5, 2))
        ttk.Button(adv_frame, text="Factory Reset / Uninstall", command=self.factory_reset).pack(fill=tk.X, padx=10, pady=5)

        # Bottom Buttons
        btn_frame = tk.Frame(top, bg=self.colors['bg'])
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        ttk.Button(btn_frame, text="Help / Tutorial", command=lambda: self.plugin_manager.broadcast('open_tutorial')).pack(side=tk.LEFT)

        def save_and_apply():
            try:
                self.config["start_on_boot"] = boot_var.get()
                self.manage_startup(boot_var.get())
                self.config["auto_update"] = update_var.get()
                self.config["show_tutorial"] = tut_var.get()
                self.config["privacy_mode"] = privacy_var.get()
                self.config["theme"] = theme_var.get()
                
                try:
                    port_val = int(port_var.get())
                except ValueError:
                    port_val = 50051 
                self.config["tailscale"]["port"] = port_val
                
                self.config["hotkeys"]["auto_paste"] = auto_paste_var.get()
                
                try:
                    delay_val = float(delay_var.get())
                except ValueError:
                    delay_val = 0.8
                self.config["hotkeys"]["auto_login_delay"] = delay_val
                
                try:
                    ways_val = int(ways_var.get())
                except ValueError:
                    ways_val = 2
                self.config["hotkeys"]["auto_login_ways"] = ways_val
                
                plugins_changed = False
                for name, var in plugin_vars.items():
                    if self.config["plugins"].get(name) != var.get():
                        plugins_changed = True
                    self.config["plugins"][name] = var.get()
                    
                for name, var in hk_vars.items():
                    self.config["hotkeys"][name] = var.get()
                    
                self.save_config()
                
                self.apply_theme_colors()
                self.refresh_ui()
                self.plugin_manager.broadcast('config_updated')
                
                top.destroy()
                if plugins_changed:
                    messagebox.showinfo("Applied", "Theme, Hotkeys, and settings applied instantly!\n\n(Note: Enabling or Disabling a plugin entirely still requires you to manually exit and reopen OpenAuth).")
            except Exception as e:
                messagebox.showerror("Settings Error", f"An error occurred while saving:\n{str(e)}")

        ttk.Button(btn_frame, text="Save & Apply", command=save_and_apply).pack(side=tk.RIGHT)

    def quit_app(self):
        if self.update_job is not None:
            self.root.after_cancel(self.update_job)
        self.root.destroy()
        os._exit(0)

    def load_plugins(self):
        for name, plugin_class in CORE_PLUGINS.items():
            cli_flag = f"--disable-{name.lower().replace(' ', '-')}"
            if cli_flag not in sys.argv:
                self.plugin_manager.register_plugin(plugin_class)
                
        for name, plugin_class in TOGGLEABLE_PLUGINS.items():
            if self.config["plugins"].get(name, False):
                self.plugin_manager.register_plugin(plugin_class)
                
        self.plugin_manager.register_plugin(SecureStoragePlugin)
        self.refresh_ui()

    def add_toolbar_action(self, text, command, side=tk.LEFT):
        btn = ttk.Button(self.toolbar, text=text, command=command)
        btn.pack(side=side, padx=2, pady=2)
        return btn

    def add_auth_action(self, text, command):
        self.auth_menu.add_command(label=text, command=command)

    def add_account(self, uri):
        try:
            account = StandardAuthAccount(uri)
            self.accounts.append(account)
            self.refresh_ui()
            return True
        except ValueError as e:
            messagebox.showerror("Invalid Account", str(e))
            return False

    def remove_account(self, account):
        if messagebox.askyesno("Confirm Delete", f"Remove {account.name}?"):
            self.accounts.remove(account)
            self.refresh_ui()

    def trigger_save(self):
        pass

    def make_draggable(self, widget, index):
        def on_press(event):
            self._drag_start_y = event.y_root
            widget.config(cursor="fleur")
        def on_release(event):
            widget.config(cursor="hand2")
            y_diff = event.y_root - self._drag_start_y
            slots_moved = round(y_diff / widget.winfo_reqheight())
            new_idx = min(max(0, index + slots_moved), len(self.accounts) - 1)
            if new_idx != index:
                acc = self.accounts.pop(index)
                self.accounts.insert(new_idx, acc)
                self.refresh_ui()
                self.trigger_save() 
        widget.bind("<ButtonPress-1>", on_press)
        widget.bind("<ButtonRelease-1>", on_release)
        widget.config(cursor="hand2")

    def animate_code_reveal(self, acc, step):
        if not getattr(acc, 'is_hovered', False):
            return
            
        if step < 6:
            scramble = f"{random.randint(100,999)} {random.randint(100,999)}"
            if hasattr(acc, 'label_ref'):
                acc.label_ref.config(text=scramble)
            self.root.after(25, lambda: self.animate_code_reveal(acc, step + 1))
        else:
            real_code = acc.get_current_code()
            formatted = f"{real_code[:3]} {real_code[3:]}"
            if hasattr(acc, 'label_ref'):
                acc.label_ref.config(text=formatted)

    def refresh_ui(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        privacy_on = self.config.get("privacy_mode", False)

        for idx, acc in enumerate(self.accounts):
            bg_color = self.colors['highlight'] if idx == 0 else self.colors['frame_bg']
            frame = tk.Frame(self.main_frame, pady=10, borderwidth=1, relief=tk.SOLID, bg=bg_color)
            frame.pack(fill=tk.X, padx=10, pady=5)
            
            header_frame = tk.Frame(frame, bg=bg_color)
            header_frame.pack(fill=tk.X, padx=5)
            
            drag_lbl = tk.Label(header_frame, text=" ≡ ", font=("Helvetica", 14, "bold"), fg=self.colors['handle'], bg=bg_color)
            drag_lbl.pack(side=tk.LEFT, padx=(0, 10))
            self.make_draggable(drag_lbl, idx)
            
            ttk.Label(header_frame, text=f"{acc.issuer} - {acc.name}", font=("Helvetica", 10, "bold"), background=bg_color, foreground=self.colors['fg']).pack(side=tk.LEFT)
            
            del_btn = ttk.Button(header_frame, text="Delete", width=6, command=lambda a=acc: self.remove_account(a))
            del_btn.pack(side=tk.RIGHT)
            
            raw_code = acc.get_current_code()
            display_text = "••• •••" if privacy_on else f"{raw_code[:3]} {raw_code[3:]}"
            
            code_label = ttk.Label(frame, text=display_text, font=("Helvetica", 24, "bold"), foreground=self.colors['code'], background=bg_color, cursor="hand2")
            code_label.pack()
            acc.label_ref = code_label
            acc.is_hovered = False
            
            def copy_code_from_click(event, a=acc):
                code = a.get_current_code()
                self.root.clipboard_clear()
                self.root.clipboard_append(code)
                self.root.update()
                self.show_toast(f"Copied to clipboard: {code}")

            code_label.bind("<Button-1>", copy_code_from_click)
            
            if privacy_on:
                def on_enter(event, a=acc):
                    if not getattr(a, 'is_hovered', False):
                        a.is_hovered = True
                        self.animate_code_reveal(a, 0)
                        
                def on_leave(event, a=acc, f=frame):
                    def check_leave():
                        x, y = self.root.winfo_pointerxy()
                        widget_under_mouse = self.root.winfo_containing(x, y)
                        is_inside = False
                        if widget_under_mouse:
                            temp = widget_under_mouse
                            while temp:
                                if temp == f:
                                    is_inside = True
                                    break
                                temp = temp.master
                        
                        if not is_inside:
                            a.is_hovered = False
                            if hasattr(a, 'label_ref'):
                                a.label_ref.config(text="••• •••")
                                
                    self.root.after(50, check_leave)

                frame.bind("<Enter>", on_enter)
                frame.bind("<Leave>", on_leave)
                for child in frame.winfo_children():
                    child.bind("<Enter>", on_enter)
                    child.bind("<Leave>", on_leave)
            
            if idx == 0:
                tk.Label(frame, text="★ PRIMARY ACCOUNT", font=("Helvetica", 8, "bold"), fg=self.colors['primary_text'], bg=bg_color).pack()

            for hook in self.account_ui_hooks:
                hook(acc, frame)
                
        self.resize_main_window()

    def update_codes(self):
        # EVERYTHING ON THE MAIN THREAD - Prevents macOS 15 HIToolbox Crashes!
        if self.accounts:
            time_remaining = self.accounts[0].get_time_remaining()
            self.root.title(f"OpenAuth ({time_remaining}s)")
            privacy_on = self.config.get("privacy_mode", False)
            
            code_changed = False
            for acc in self.accounts:
                new_code = acc.get_current_code()
                old_code = getattr(acc, 'last_code', None)
                
                if new_code != old_code:
                    if hasattr(acc, 'label_ref'):
                        if not privacy_on or getattr(acc, 'is_hovered', False):
                            formatted = f"{new_code[:3]} {new_code[3:]}"
                            acc.label_ref.config(text=formatted)
                        elif privacy_on and not getattr(acc, 'is_hovered', False):
                            acc.label_ref.config(text="••• •••")
                            
                    acc.last_code = new_code
                    code_changed = True
            if code_changed:
                for hook in self.tick_hooks:
                    hook()
        else:
            self.root.title("OpenAuth")

        self.update_job = self.root.after(1000, self.update_codes)

if __name__ == "__main__":
    if IS_WIN:
        mutex_name = "OpenAuth_Single_Instance_Mutex"
        mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
        if ctypes.windll.kernel32.GetLastError() == 183: 
            sys.exit(0)

    root = tk.Tk()
    app = DesktopAuthenticator(root)
    root.mainloop()