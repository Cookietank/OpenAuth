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
import re
import datetime 
import shutil 
from PIL import Image, ImageDraw, ImageTk
from core import StandardAuthAccount
from plugin_manager import PluginManager

# Import all plugins
from plugins.qr_scanner import ScreenQRScannerPlugin
from plugins.manual_entry import ManualEntryPlugin
from plugins.backup_export import BackupExportPlugin  
from plugins.secure_storage import SecureStoragePlugin
from plugins.tray_icon import TrayIconPlugin
from plugins.broadcaster import LocalBroadcasterPlugin
from plugins.auto_login import AutoLoginPlugin
from plugins.virtual_yubikey import VirtualYubiKeyPlugin
from plugins.tailscale_sync import TailscaleSyncPlugin

APP_VERSION = "v0.1.4.1"
GITHUB_REPO = "cookietank/OpenAuth"

# =========================================================================
# SILENT COMMAND-LINE UNINSTALLER
# =========================================================================
if "--uninstall" in sys.argv:
    try:
        import keyring
        keyring.delete_password("ModularDesktopAuthenticator", "TOTP_Secrets")
    except Exception: pass
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
        winreg.DeleteValue(key, "OpenAuth")
        winreg.CloseKey(key)
    except Exception: pass

    vbs_path = os.path.join(os.getenv('APPDATA'), r'Microsoft\Windows\Start Menu\Programs\Startup\OpenAuth.vbs')
    if os.path.exists(vbs_path):
        try: os.remove(vbs_path)
        except: pass

    appdata_dir = os.path.join(os.getenv('APPDATA'), 'OpenAuth')
    if os.path.exists(appdata_dir):
        shutil.rmtree(appdata_dir, ignore_errors=True)

    root = tk.Tk()
    root.withdraw()
    messagebox.showinfo("Uninstall Complete", "OpenAuth has been completely removed from your system.\n\nYou can now safely delete the .exe file.")
    sys.exit(0)


APPDATA_DIR = os.path.join(os.getenv('APPDATA'), 'OpenAuth')
if not os.path.exists(APPDATA_DIR):
    os.makedirs(APPDATA_DIR)

CONFIG_FILE = os.path.join(APPDATA_DIR, "app_config.json")
LOG_FILE = os.path.join(APPDATA_DIR, "openauth.log")

# =========================================================================
# SYSTEM LOGGER
# =========================================================================
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

with open(LOG_FILE, 'a', encoding='utf-8') as f:
    f.write(f"\n\n[{datetime.datetime.now()}] === NEW OPENAUTH SESSION ({APP_VERSION}) ===\n")

sys.stdout = SafeLogger(LOG_FILE, is_stdout=True)
sys.stderr = SafeLogger(LOG_FILE, is_stdout=False)

def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

AVAILABLE_PLUGINS = {
    "Tray Icon": TrayIconPlugin,
    "Screen QR Scanner": ScreenQRScannerPlugin,
    "Manual Entry": ManualEntryPlugin, 
    "Backup & Export": BackupExportPlugin,
    "Copy Code to Clipboard": VirtualYubiKeyPlugin,
    "Auto-Login": AutoLoginPlugin,
    "Local Broadcaster": LocalBroadcasterPlugin,
    "Tailscale Phone Sync": TailscaleSyncPlugin
}

PLUGIN_DESCRIPTIONS = {
    "Tray Icon": "Minimizes OpenAuth silently to the Windows System Tray.",
    "Screen QR Scanner": "Provisions accounts by grabbing and scanning QR codes directly from your screen.",
    "Manual Entry": "Allows you to manually add accounts via a Secret Key or URI.", 
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
            "theme": "Light",
            "plugins": {
                "Tray Icon": True,
                "Screen QR Scanner": True,
                "Manual Entry": True,  
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

        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        
        self.toolbar = tk.Frame(root, bd=1, relief=tk.RAISED, bg=self.colors['bg'])
        self.toolbar.pack(side=tk.TOP, fill=tk.X)
        
        self.auth_menu_btn = ttk.Menubutton(self.toolbar, text="➕ Add Auth Key")
        self.auth_menu = tk.Menu(self.auth_menu_btn, tearoff=0, bg=self.colors['frame_bg'], fg=self.colors['fg'])
        self.auth_menu_btn.configure(menu=self.auth_menu)
        self.auth_menu_btn.pack(side=tk.LEFT, padx=5, pady=2)

        self.add_toolbar_action("Quit", self.quit_app, side=tk.RIGHT)
        self.add_toolbar_action("Settings", self.open_settings, side=tk.RIGHT)
        
        self.main_frame = tk.Frame(root, bg=self.colors['bg'])
        self.main_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

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
                self.root.after(500, self.start_interactive_tutorial)

        if getattr(sys, 'frozen', False) and self.config.get("auto_update", True):
            threading.Thread(target=self.check_for_updates, daemon=True).start()

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
                        asset_name = f"OpenAuth_{latest_version}.exe"
                        
                        for asset in data.get('assets', []):
                            if asset['name'].endswith('.exe'):
                                download_url = asset['browser_download_url']
                                asset_name = asset['name'] 
                                break
                                
                        if download_url:
                            self.root.after(0, lambda: self.prompt_update(latest_version, download_url, asset_name))
        except Exception as e:
            print(f"Update check failed: {e}")

    def prompt_update(self, latest_version, download_url, asset_name):
        if messagebox.askyesno("Update Available", f"A new version of OpenAuth ({latest_version}) is available!\n\nWould you like to automatically download and install it now?"):
            threading.Thread(target=self.perform_update, args=(download_url, asset_name), daemon=True).start()

    def perform_update(self, download_url, asset_name):
        for plugin in self.plugin_manager.plugins:
            if hasattr(plugin, 'show_toast'):
                plugin.show_toast("Downloading update... Please wait.", 5000)
                break
                
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
            
        bat_path = os.path.join(os.path.dirname(current_exe), "apply_openauth_update.bat")
        
        if current_exe != final_exe:
            bat_content = f'''@echo off
:wait
timeout /t 1 /nobreak > NUL
del "{current_exe}"
if exist "{current_exe}" goto wait
start "" "{final_exe}"
del "%~f0"
'''
        else:
            bat_content = f'''@echo off
:wait
timeout /t 1 /nobreak > NUL
del "{current_exe}"
if exist "{current_exe}" goto wait
move /Y "{download_target}" "{final_exe}"
start "" "{final_exe}"
del "%~f0"
'''

        with open(bat_path, "w") as f:
            f.write(bat_content)
            
        env = os.environ.copy()
        env.pop('_MEIPASS', None)
        env.pop('_MEIPASS2', None)
        env.pop('TCL_LIBRARY', None)
        env.pop('TK_LIBRARY', None)
            
        subprocess.Popen(bat_path, shell=True, env=env, creationflags=0x00000008)
        os._exit(0)

    # =========================================================================
    # INTERACTIVE TUTORIAL WIZARD
    # =========================================================================
    def start_interactive_tutorial(self):
        self.tut_win = tk.Toplevel(self.root)
        self.tut_win.title("OpenAuth Setup")
        self.tut_win.geometry("550x750")
        self.tut_win.attributes("-topmost", True)
        self.tut_win.configure(bg=self.colors['bg'])
        self.tut_step = 0
        self.tut_images = [] 
        
        self.tut_content_frame = tk.Frame(self.tut_win, bg=self.colors['bg'])
        self.tut_content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.tut_nav_frame = tk.Frame(self.tut_win, bg=self.colors['bg'])
        self.tut_nav_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=20, pady=20)
        
        self.btn_back = ttk.Button(self.tut_nav_frame, text="< Back", command=self.tut_prev)
        self.btn_next = ttk.Button(self.tut_nav_frame, text="Next >", command=self.tut_next)
        
        self.btn_next.pack(side=tk.RIGHT)
        self.btn_back.pack(side=tk.LEFT)
        
        self.render_tut_step()

    def tut_next(self):
        if self.tut_step < 7:
            self.tut_step += 1
            self.render_tut_step()
        else:
            self.tut_win.destroy()
            
    def tut_prev(self):
        if self.tut_step > 0:
            self.tut_step -= 1
            self.render_tut_step()

    def _add_tut_img(self, img_name):
        img_path = get_resource_path(os.path.join('plugins', img_name))
        if os.path.exists(img_path):
            try:
                orig_img = Image.open(img_path)
                new_size = (orig_img.width * 2, orig_img.height * 2)
                orig_img = orig_img.resize(new_size, Image.Resampling.LANCZOS)
                
                img_canvas = tk.Canvas(self.tut_content_frame, bg=self.colors['bg'], highlightthickness=1, highlightbackground="gray")
                img_canvas.pack(fill=tk.BOTH, expand=True, pady=10)
                
                self.tut_images.append(orig_img)
                
                def resize_image(event, canvas=img_canvas, img=orig_img):
                    canvas.delete("all")
                    ratio = min(event.width / img.width, event.height / img.height)
                    if ratio > 1: ratio = 1 
                    
                    new_w = max(1, int(img.width * ratio))
                    new_h = max(1, int(img.height * ratio))
                    
                    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(resized)
                    
                    canvas.image = photo
                    canvas.create_image(event.width//2, event.height//2, anchor=tk.CENTER, image=photo)

                img_canvas.bind("<Configure>", resize_image)
            except Exception as e:
                print(f"Error drawing image: {e}")
        else:
            tk.Label(self.tut_content_frame, text=f"[ Missing Image: {img_name} ]", bg=self.colors['bg'], fg="red").pack(pady=10)

    def render_tut_step(self):
        for widget in self.tut_content_frame.winfo_children():
            widget.destroy()
            
        self.btn_back.config(state="normal" if self.tut_step > 0 else "disabled")
        self.btn_next.config(text="Finish" if self.tut_step == 7 else "Next >")
        
        bg = self.colors['bg']
        fg = self.colors['fg']
        
        # Dynamically fetch configured hotkeys to display in tutorial
        hk_copy = self.config.get("hotkeys", {}).get("Copy Code to Clipboard", "ctrl+alt+c").upper()
        hk_auto = self.config.get("hotkeys", {}).get("Auto-Login", "ctrl+alt+q").upper()

        if self.tut_step == 0:
            tk.Label(self.tut_content_frame, text="🚀 Welcome to OpenAuth", font=("Helvetica", 18, "bold"), bg=bg, fg=fg).pack(pady=10)
            tk.Label(self.tut_content_frame, text="Let's get your first account set up.\n\nClick the link below to open your Microsoft Security settings in your web browser. You will need to log in.", justify=tk.LEFT, bg=bg, fg=fg, wraplength=450).pack(pady=10)
            
            link = tk.Label(self.tut_content_frame, text="🔗 Open: aka.ms/mfasetup", font=("Helvetica", 12, "bold", "underline"), bg=bg, fg="#4da6ff", cursor="hand2")
            link.pack(pady=20)
            link.bind("<Button-1>", lambda e: webbrowser.open("https://aka.ms/mfasetup"))
            
        elif self.tut_step == 1:
            tk.Label(self.tut_content_frame, text="Step 1: Add Method", font=("Helvetica", 16, "bold"), bg=bg, fg=fg).pack(pady=10)
            tk.Label(self.tut_content_frame, text="On the Microsoft website, click '+ Add sign-in method' and choose 'Microsoft Authenticator' from the options.", justify=tk.LEFT, bg=bg, fg=fg, wraplength=450).pack(pady=10)
            self._add_tut_img('tut_add_method.png')
            
        elif self.tut_step == 2:
            tk.Label(self.tut_content_frame, text="Step 2: Choose Different App", font=("Helvetica", 16, "bold"), bg=bg, fg=fg).pack(pady=10)
            tk.Label(self.tut_content_frame, text="Click the small blue link that says 'Set up a different authentication app'.", justify=tk.LEFT, bg=bg, fg=fg, wraplength=450).pack(pady=10)
            self._add_tut_img('tut_different_app.png')
            
        elif self.tut_step == 3:
            tk.Label(self.tut_content_frame, text="Step 3: Scan the QR Code", font=("Helvetica", 16, "bold"), bg=bg, fg=fg).pack(pady=10)
            tk.Label(self.tut_content_frame, text="Click 'Next' until Microsoft shows a QR code on your screen.\n\nPlease ensure the QR code is fully visible on the screen before clicking the 'Scan Screen' button below. OpenAuth will instantly find the code on your monitor and securely save it!", justify=tk.LEFT, bg=bg, fg=fg, wraplength=450).pack(pady=10)
            self._add_tut_img('tut_qr_code.png')
            
            def test_scan():
                for p in self.plugin_manager.plugins:
                    if isinstance(p, ScreenQRScannerPlugin):
                        p.scan_screen()
            ttk.Button(self.tut_content_frame, text="📸 Scan Screen Now", command=test_scan).pack(pady=10)
            
        elif self.tut_step == 4:
            tk.Label(self.tut_content_frame, text="Step 4: Verify the Code", font=("Helvetica", 16, "bold"), bg=bg, fg=fg).pack(pady=10)
            tk.Label(self.tut_content_frame, text="Now that OpenAuth is generating 6-digit codes on your desktop, click 'Next' on the Microsoft website.\n\nType the 6-digit code OpenAuth is currently displaying into the Microsoft website to verify the link.", justify=tk.LEFT, bg=bg, fg=fg, wraplength=450).pack(pady=10)
            self._add_tut_img('tut_verify.png')
            
        elif self.tut_step == 5:
            tk.Label(self.tut_content_frame, text="Configuration: Hotkeys", font=("Helvetica", 16, "bold"), bg=bg, fg=fg).pack(pady=10)
            
            desc_text = (
                "OpenAuth has two powerful keyboard shortcuts you can press anywhere in Windows:\n\n"
                f"1. Copy Code ({hk_copy}): Instantly copies your code to your clipboard.\n"
                f"2. Auto-Login ({hk_auto}): A macro that automatically navigates the Microsoft login screen, pasting the current code and handling login for you."
            )
            tk.Label(self.tut_content_frame, text=desc_text, justify=tk.LEFT, bg=bg, fg=fg, wraplength=450).pack(pady=10)
            
            self.auto_paste_tut_var = tk.BooleanVar(value=self.config["hotkeys"].get("auto_paste", False))
            ttk.Checkbutton(self.tut_content_frame, text="Enable 'Auto-Paste' for the Copy shortcut (injects keystrokes & hits enter)", variable=self.auto_paste_tut_var, command=self._tut_save_settings).pack(pady=10, anchor="w")

        elif self.tut_step == 6:
            tk.Label(self.tut_content_frame, text="Configuration: Auto-Login", font=("Helvetica", 16, "bold"), bg=bg, fg=fg).pack(pady=10)
            tk.Label(self.tut_content_frame, text="Login as normal and manually click 'I can't use my Outlook mobile app right now'. You will reach the 'Verify your identity' screen shown below.", justify=tk.LEFT, bg=bg, fg=fg, wraplength=450).pack(pady=5)
            self._add_tut_img('tut_waystoverify.png')
            
            tk.Label(self.tut_content_frame, text="How many options appear on this screen for you? (App, Text, Call, etc)", bg=bg, fg=fg).pack(anchor="w", pady=(10,0))
            self.ways_tut_var = tk.StringVar(value=str(self.config["hotkeys"].get("auto_login_ways", 2)))
            self.create_styled_entry(self.tut_content_frame, self.ways_tut_var).pack(fill=tk.X, pady=5)
            self.ways_tut_var.trace_add("write", lambda *args: self._tut_save_settings())

            test_desc = f"Once configured, make sure your browser window is active (clicked on), and press your Auto-Login shortcut ({hk_auto}) to run the macro!"
            tk.Label(self.tut_content_frame, text=test_desc, font=("Helvetica", 10, "italic"), bg=bg, fg="gray", wraplength=450, justify=tk.LEFT).pack(pady=(15,5))

        elif self.tut_step == 7:
            tk.Label(self.tut_content_frame, text="Ready to Go!", font=("Helvetica", 16, "bold"), bg=bg, fg=fg).pack(pady=10)
            tk.Label(self.tut_content_frame, text="OpenAuth is designed to run silently in the background.\n\nWhen you close the window, it hides in your System Tray. Double-click the tray icon to open it, or Right-Click it to instantly copy your code.", justify=tk.LEFT, bg=bg, fg=fg, wraplength=450).pack(pady=10)
            
            self.boot_tut_var = tk.BooleanVar(value=self.config.get("start_on_boot", False))
            ttk.Checkbutton(self.tut_content_frame, text="Start OpenAuth silently with Windows", variable=self.boot_tut_var, command=self._tut_save_settings).pack(pady=10, anchor="w")
            
            tk.Label(self.tut_content_frame, text="You can change all of these settings later by clicking the 'Settings' button in the main app.", justify=tk.LEFT, bg=bg, fg="gray", wraplength=450).pack(pady=20)

    def _tut_save_settings(self):
        try:
            if hasattr(self, 'boot_tut_var'):
                self.config["start_on_boot"] = self.boot_tut_var.get()
                self.manage_startup(self.boot_tut_var.get())
            if hasattr(self, 'auto_paste_tut_var'):
                self.config["hotkeys"]["auto_paste"] = self.auto_paste_tut_var.get()
            if hasattr(self, 'ways_tut_var'):
                try:
                    self.config["hotkeys"]["auto_login_ways"] = int(self.ways_tut_var.get())
                except ValueError:
                    pass
            self.save_config()
            self.plugin_manager.broadcast('config_updated')
        except Exception:
            pass

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

    def manage_startup(self, enable, exe_override=None):
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
                    target_exe = exe_override if exe_override else sys.executable
                    app_path = f'"{target_exe}" --tray'
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
            os.startfile(APPDATA_DIR)

        def open_and_close():
            template = f"**OpenAuth Version:** {APP_VERSION}\n**OS:** Windows\n\n**Bug Description:**\n[Describe what went wrong here]\n\n**Steps to Reproduce:**\n1. \n2. "
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
                   "- OpenAuth from Windows Startup\n\n"
                   "Are you absolutely sure you want to wipe OpenAuth from this computer?")
        if messagebox.askyesno("Factory Reset", warning, icon="warning", parent=self.settings_window):
            try:
                self.manage_startup(False)
                import keyring
                try: keyring.delete_password("ModularDesktopAuthenticator", "TOTP_Secrets")
                except: pass
                
                sys.stdout.close()
                sys.stderr.close()
                
                import shutil
                shutil.rmtree(APPDATA_DIR, ignore_errors=True)
                
                messagebox.showinfo("Uninstall Complete", "OpenAuth has been completely wiped from your system.\n\nThe application will now close. You can safely delete the .exe file.")
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
        ttk.Checkbutton(general_frame, text="Start with Windows (Hidden in Tray)", variable=boot_var).pack(anchor="w", padx=10, pady=(15, 5))
        
        update_var = tk.BooleanVar(value=self.config.get("auto_update", True))
        ttk.Checkbutton(general_frame, text="Check for updates automatically on launch", variable=update_var).pack(anchor="w", padx=10, pady=5)
        
        tut_var = tk.BooleanVar(value=self.config.get("show_tutorial", True))
        ttk.Checkbutton(general_frame, text="Show Tutorial on App Updates", variable=tut_var).pack(anchor="w", padx=10, pady=5)
        
        tk.Label(general_frame, text="App Theme:", bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor="w", padx=10, pady=(10, 0))
        theme_var = tk.StringVar(value=self.config.get("theme", "Light"))
        ttk.Combobox(general_frame, textvariable=theme_var, values=["Light", "Dark"], state="readonly").pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(general_frame, text=f"OpenAuth Version: {APP_VERSION}", bg=self.colors['bg'], fg=self.colors['handle']).pack(anchor="w", padx=10, pady=(30, 0))
        
        ttk.Button(general_frame, text="Report an Issue / Bug", command=self.report_issue).pack(anchor="w", padx=10, pady=(5, 0))

        # TAB 2: Plugins & Hotkeys
        plugin_frame = ttk.Frame(notebook)
        notebook.add(plugin_frame, text="Plugins & Hotkeys")
        
        tk.Label(plugin_frame, text="Core Modules", font=("Helvetica", 9, "bold"), bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor="w", padx=10, pady=(10, 2))

        core_plugins = ["Tray Icon", "Screen QR Scanner", "Manual Entry", "Copy Code to Clipboard", "Auto-Login"]
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

        tk.Label(adv_frame, text="Account Backup", font=("Helvetica", 9, "bold"), bg=self.colors['bg'], fg=self.colors['fg']).pack(anchor="w", padx=10, pady=(10, 2))
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

        ttk.Button(btn_frame, text="Help / Tutorial", command=self.start_interactive_tutorial).pack(side=tk.LEFT)

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
                
        self.resize_main_window()

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