import sys
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as messagebox
import time
import json
import os
import secrets
import subprocess
import webbrowser
import ctypes
import winreg 
import threading
import urllib.request
import urllib.error
import re  # Added for parsing Semantic Versioning (v1.2.3)
from PIL import Image, ImageDraw, ImageTk
from core import StandardAuthAccount
from plugin_manager import PluginManager

# Import all plugins
from plugins.qr_scanner import ScreenQRScannerPlugin
from plugins.secure_storage import SecureStoragePlugin
from plugins.tray_icon import TrayIconPlugin
from plugins.broadcaster import LocalBroadcasterPlugin
from plugins.auto_login import AutoLoginPlugin
from plugins.virtual_yubikey import VirtualYubiKeyPlugin
from plugins.tailscale_sync import TailscaleSyncPlugin

APP_VERSION = "v1.3.1"
GITHUB_REPO = "cookietank/OpenAuth"

APPDATA_DIR = os.path.join(os.getenv('APPDATA'), 'OpenAuth')
if not os.path.exists(APPDATA_DIR):
    os.makedirs(APPDATA_DIR)

CONFIG_FILE = os.path.join(APPDATA_DIR, "app_config.json")

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

AVAILABLE_PLUGINS = {
    "Tray Icon": TrayIconPlugin,
    "Screen QR Scanner": ScreenQRScannerPlugin,
    "Copy Code to Clipboard": VirtualYubiKeyPlugin,
    "Auto-Login": AutoLoginPlugin,
    "Local Broadcaster": LocalBroadcasterPlugin,
    "Tailscale Phone Sync": TailscaleSyncPlugin
}

PLUGIN_DESCRIPTIONS = {
    "Tray Icon": "Minimizes OpenAuth silently to the Windows System Tray.",
    "Screen QR Scanner": "Provisions accounts by grabbing and scanning QR codes directly from your screen.",
    "Copy Code to Clipboard": "Provides a global keyboard shortcut to instantly copy (or paste) your primary code.",
    "Auto-Login": "Uses an automated keystroke macro to instantly navigate Microsoft login screens and inject your code.",
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
        self.root.geometry("450x600")
        self.root.minsize(400, 200)
        self.root.attributes("-topmost", True)
        
        if "--tray" in sys.argv:
            self.root.withdraw()
        
        self.accounts =[]
        self.update_job = None
        self.account_ui_hooks = []
        self.tick_hooks =[]
        
        self.config = {
            "version": "v1.0.0",
            "show_tutorial": True,
            "auto_update": True,
            "start_on_boot": False,
            "theme": "Light",
            "plugins": {
                "Tray Icon": True,
                "Screen QR Scanner": True,
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

        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        
        self.toolbar = tk.Frame(root, bd=1, relief=tk.RAISED, bg=self.colors['bg'])
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        
        self.add_toolbar_action("Quit", self.quit_app, side=tk.RIGHT)
        self.add_toolbar_action("Settings", self.open_settings, side=tk.RIGHT)
        
        self.main_frame = tk.Frame(root, bg=self.colors['bg'])
        self.main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.plugin_manager = PluginManager(self)
        self.load_plugins()
        self.update_codes()

        if self.config.get("version") != APP_VERSION:
            self.config["version"] = APP_VERSION
            self.save_config()
            if self.config.get("show_tutorial", True):
                self.root.after(500, self.show_tutorial)

        # Trigger OTA Update Check
        if getattr(sys, 'frozen', False) and self.config.get("auto_update", True):
            threading.Thread(target=self.check_for_updates, daemon=True).start()

    def check_for_updates(self):
        """Silently checks the GitHub API and parses semantic versions correctly."""
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(url, headers={'User-Agent': 'OpenAuth-Updater'})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                latest_version = data.get('tag_name', '')
                
                if latest_version:
                    # Parse "v1.2.3" into (1, 2, 3) to allow mathematical comparison
                    def get_v_tuple(v_str):
                        return tuple(map(int, re.findall(r'\d+', v_str)))
                    
                    latest_tuple = get_v_tuple(latest_version)
                    current_tuple = get_v_tuple(APP_VERSION)
                    
                    # Only trigger if the cloud is mathematically greater than local
                    if latest_tuple > current_tuple:
                        download_url = None
                        for asset in data.get('assets', []):
                            if asset['name'].endswith('.exe'):
                                download_url = asset['browser_download_url']
                                break
                                
                        if download_url:
                            self.root.after(0, lambda: self.prompt_update(latest_version, download_url))
        except Exception as e:
            print(f"Update check failed: {e}")

    def prompt_update(self, latest_version, download_url):
        if messagebox.askyesno("Update Available", f"A new version of OpenAuth ({latest_version}) is available!\n\nWould you like to automatically download and install it now?"):
            threading.Thread(target=self.perform_update, args=(download_url,), daemon=True).start()

    def perform_update(self, download_url):
        for plugin in self.plugin_manager.plugins:
            if hasattr(plugin, 'show_toast'):
                plugin.show_toast("Downloading update... Please wait.", 5000)
                break
                
        try:
            current_exe = sys.executable
            update_exe = current_exe + ".update"
            
            req = urllib.request.Request(download_url, headers={'User-Agent': 'OpenAuth-Updater'})
            with urllib.request.urlopen(req) as response, open(update_exe, 'wb') as out_file:
                out_file.write(response.read())
                
            self.apply_update_and_restart(update_exe, current_exe)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Update Failed", f"Failed to download update:\n{e}"))

    def apply_update_and_restart(self, update_exe, current_exe):
        """Safely swaps the .exe without crashing PyInstaller's DLL loader."""
        bat_path = os.path.join(os.path.dirname(current_exe), "apply_openauth_update.bat")
        
        # Uses a loop to ensure the old file is fully unlocked by Windows before deleting
        bat_content = f'''@echo off
:wait
timeout /t 1 /nobreak > NUL
del "{current_exe}"
if exist "{current_exe}" goto wait
move /Y "{update_exe}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
'''
        with open(bat_path, "w") as f:
            f.write(bat_content)
            
        # CRITICAL FIX: Strip PyInstaller variables before launching the batch script
        env = os.environ.copy()
        env.pop('_MEIPASS2', None)
        env.pop('TCL_LIBRARY', None)
        env.pop('TK_LIBRARY', None)
            
        subprocess.Popen(bat_path, shell=True, env=env, creationflags=0x00000008)
        os._exit(0)

    def show_tutorial(self):
        tut = tk.Toplevel(self.root)
        tut.title("Welcome to OpenAuth")
        tut.geometry("480x750")
        tut.attributes("-topmost", True)
        tut.configure(bg=self.colors['bg'])
        
        title = tk.Label(tut, text="🚀 Welcome to OpenAuth", font=("Helvetica", 16, "bold"), bg=self.colors['bg'], fg=self.colors['fg'])
        title.pack(pady=(15, 5))
        
        link = tk.Label(tut, text="🔗 Click here to open: aka.ms/mfasetup", font=("Helvetica", 11, "bold", "underline"), bg=self.colors['bg'], fg="#4da6ff", cursor="hand2")
        link.pack(pady=5)
        link.bind("<Button-1>", lambda e: webbrowser.open("https://aka.ms/mfasetup"))

        guide_text = (
            "How to provision your first account:\n"
            "1. Click the link above to open Microsoft Security Info.\n"
            "2. Click '+ Add sign-in method' and choose 'Authenticator app'.\n"
            "3. IMPORTANT: Click the small text that says: \n   'I want to use a different authenticator app'.\n"
            "4. Click 'Next' until the QR code is displayed on your screen.\n"
            "5. Click 'Scan Screen' in the OpenAuth toolbar above!\n\n"
            "---\n\n"
            "Copy Code to Clipboard & Phone Sync:\n"
            "Use your hotkey to copy codes instantly, or fetch them on your "
            "Android phone using a Tailscale Quick Tile."
        )
        msg = tk.Message(tut, text=guide_text, font=("Helvetica", 10), bg=self.colors['bg'], fg=self.colors['fg'], width=420, justify=tk.LEFT)
        msg.pack(padx=20, pady=5)
        
        lbl_al = tk.Label(tut, text="Auto Login:", font=("Helvetica", 10, "bold"), bg=self.colors['bg'], fg=self.colors['fg'])
        lbl_al.pack(padx=20, pady=(5, 0), anchor="w")
        
        lbl_al2 = tk.Label(tut, text="Trigger the macro when on the following page:", font=("Helvetica", 10), bg=self.colors['bg'], fg=self.colors['fg'])
        lbl_al2.pack(padx=20, pady=(0, 5), anchor="w")
        
        img_path = get_resource_path(os.path.join('plugins', 'auto_login_help.png'))
        if os.path.exists(img_path):
            try:
                img = Image.open(img_path)
                img.thumbnail((350, 350), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                img_lbl = tk.Label(tut, image=photo, bg=self.colors['bg'], borderwidth=1, relief="solid")
                img_lbl.image = photo 
                img_lbl.pack(pady=5)
            except Exception as e:
                print(f"Could not load tutorial image: {e}")

        ttk.Button(tut, text="Got it!", command=tut.destroy).pack(pady=10)

    def get_icon_image(self):
        icon_path = get_resource_path(os.path.join('plugins', 'icon.ico'))
        if os.path.exists(icon_path):
            return Image.open(icon_path)
            
        image = Image.new('RGBA', (64, 64), color=(255, 255, 255, 0))
        draw = ImageDraw.Draw(image)
        draw.polygon([(32, 4), (8, 16), (8, 40), (32, 60), (56, 40), (56, 16)], fill="#005A9E")
        draw.ellipse([(26, 22), (38, 34)], fill="white")
        draw.polygon([(30, 32), (34, 32), (34, 48), (30, 48)], fill="white")
        return image

    def apply_theme_colors(self):
        is_dark = self.config.get("theme", "Light") == "Dark"
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
                    self.config["version"] = saved_config.get("version", "v1.0.0")
                    self.config["show_tutorial"] = saved_config.get("show_tutorial", True)
                    self.config["auto_update"] = saved_config.get("auto_update", True)
                    self.config["start_on_boot"] = saved_config.get("start_on_boot", False)
                    self.config["theme"] = saved_config.get("theme", "Light")
                    
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

    def manage_startup(self, enable):
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "OpenAuth"
        
        vbs_path = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup\OpenAuth.vbs')
        if os.path.exists(vbs_path):
            try: os.remove(vbs_path)
            except: pass

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
            if enable:
                if getattr(sys, 'frozen', False):
                    app_path = f'"{sys.executable}" --tray'
                else:
                    pythonw_path = sys.executable.replace("python.exe", "pythonw.exe")
                    script_path = os.path.abspath(sys.argv[0])
                    app_path = f'"{pythonw_path}" "{script_path}" --tray'
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception as e:
            print(f"Failed to manage startup registry: {e}")

    def open_settings(self):
        top = tk.Toplevel(self.root)
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
        ttk.Checkbutton(general_frame, text="Start with Windows (Hidden in Tray)", variable=boot_var).pack(anchor="w", padx=10, pady=(15, 5))
        
        update_var = tk.BooleanVar(value=self.config.get("auto_update", True))
        ttk.Checkbutton(general_frame, text="Check for updates automatically on launch", variable=update_var).pack(anchor="w", padx=10, pady=5)
        
        tut_var = tk.BooleanVar(value=self.config.get("show_tutorial", True))
        ttk.Checkbutton(general_frame, text="Show Tutorial on App Updates", variable=tut_var).pack(anchor="w", padx=10, pady=5)
        
        tk.Label(general_frame, text="App Theme:", bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor="w", padx=10, pady=(10, 0))
        theme_var = tk.StringVar(value=self.config.get("theme", "Light"))
        ttk.Combobox(general_frame, textvariable=theme_var, values=["Light", "Dark"], state="readonly").pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(general_frame, text=f"OpenAuth Version: {APP_VERSION}", bg=self.colors['bg'], fg=self.colors['handle']).pack(anchor="w", padx=10, pady=(30, 0))

        # TAB 2: Plugins & Hotkeys
        plugin_frame = ttk.Frame(notebook)
        notebook.add(plugin_frame, text="Plugins & Hotkeys")
        
        tk.Label(plugin_frame, text="Core Modules", font=("Helvetica", 9, "bold"), bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor="w", padx=10, pady=(10, 2))

        core_plugins = ["Tray Icon", "Screen QR Scanner", "Copy Code to Clipboard", "Auto-Login"]
        for name in core_plugins:
            var = tk.BooleanVar(value=self.config["plugins"].get(name, AVAILABLE_PLUGINS.get(name) is not None))
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

        # Bottom Buttons
        btn_frame = tk.Frame(top, bg=self.colors['bg'])
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)

        ttk.Button(btn_frame, text="Help / Tutorial", command=self.show_tutorial).pack(side=tk.LEFT)

        def save_and_apply():
            try:
                self.config["start_on_boot"] = boot_var.get()
                self.manage_startup(boot_var.get())
                self.config["auto_update"] = update_var.get()
                self.config["show_tutorial"] = tut_var.get()
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
        for name, plugin_class in AVAILABLE_PLUGINS.items():
            if self.config["plugins"].get(name, False):
                self.plugin_manager.register_plugin(plugin_class)
        self.plugin_manager.register_plugin(SecureStoragePlugin)
        self.refresh_ui()

    def add_toolbar_action(self, text, command, side=tk.LEFT):
        btn = ttk.Button(self.toolbar, text=text, command=command)
        btn.pack(side=side, padx=2, pady=2)

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

    def refresh_ui(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

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
            
            code_label = ttk.Label(frame, text=acc.get_current_code(), font=("Helvetica", 24, "bold"), foreground=self.colors['code'], background=bg_color)
            code_label.pack()
            acc.label_ref = code_label
            
            if idx == 0:
                tk.Label(frame, text="★ PRIMARY ACCOUNT", font=("Helvetica", 8, "bold"), fg=self.colors['primary_text'], bg=bg_color).pack()

            for hook in self.account_ui_hooks:
                hook(acc, frame)

    def update_codes(self):
        if self.accounts:
            time_remaining = self.accounts[0].get_time_remaining()
            self.root.title(f"OpenAuth ({time_remaining}s)")
            
            code_changed = False
            for acc in self.accounts:
                new_code = acc.get_current_code()
                old_code = getattr(acc, 'last_code', None)
                
                if new_code != old_code:
                    if hasattr(acc, 'label_ref'):
                        acc.label_ref.config(text=new_code)
                    acc.last_code = new_code
                    code_changed = True
            if code_changed:
                for hook in self.tick_hooks:
                    hook()
        else:
            self.root.title("OpenAuth")

        self.update_job = self.root.after(1000, self.update_codes)

if __name__ == "__main__":
    mutex_name = "OpenAuth_Single_Instance_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183: 
        sys.exit(0)

    root = tk.Tk()
    app = DesktopAuthenticator(root)
    root.mainloop()