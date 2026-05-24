import tkinter as tk
from tkinter import ttk
import webbrowser
import os
from PIL import Image, ImageTk
from plugin_manager import PluginBase

class TutorialPlugin(PluginBase):
    def setup(self):
        pass

    def open_tutorial(self):
        self.start_interactive_tutorial()

    def start_interactive_tutorial(self):
        self.tut_win = tk.Toplevel(self.app.root)
        self.tut_win.title("OpenAuth Setup")
        self.tut_win.geometry("550x750")
        self.tut_win.attributes("-topmost", True)
        self.tut_win.configure(bg=self.app.colors['bg'])
        self.tut_step = 0
        self.tut_images = [] 
        
        self.tut_content_frame = tk.Frame(self.tut_win, bg=self.app.colors['bg'])
        self.tut_content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.tut_nav_frame = tk.Frame(self.tut_win, bg=self.app.colors['bg'])
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
        img_path = self.app.get_resource_path(os.path.join('plugins', img_name))
        if os.path.exists(img_path):
            try:
                orig_img = Image.open(img_path)
                new_size = (orig_img.width * 2, orig_img.height * 2)
                orig_img = orig_img.resize(new_size, Image.Resampling.LANCZOS)
                
                img_canvas = tk.Canvas(self.tut_content_frame, bg=self.app.colors['bg'], highlightthickness=1, highlightbackground="gray")
                img_canvas.pack(fill=tk.BOTH, expand=True, pady=10)
                
                self.tut_images.append(orig_img)
                
                def resize_image(event, canvas=img_canvas, img=orig_img):
                    canvas.delete("all")
                    if event.width <= 1 or event.height <= 1: return
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
            tk.Label(self.tut_content_frame, text=f"[ Missing Image: {img_name} ]", bg=self.app.colors['bg'], fg="red").pack(pady=10)

    def _add_tut_imgs_side_by_side(self, img_names):
        """Renders multiple images side-by-side responsively."""
        frame = tk.Frame(self.tut_content_frame, bg=self.app.colors['bg'])
        frame.pack(fill=tk.BOTH, expand=True, pady=10)

        for img_name in img_names:
            img_path = self.app.get_resource_path(os.path.join('plugins', img_name))
            if os.path.exists(img_path):
                try:
                    orig_img = Image.open(img_path)
                    new_size = (orig_img.width * 2, orig_img.height * 2)
                    orig_img = orig_img.resize(new_size, Image.Resampling.LANCZOS)

                    img_canvas = tk.Canvas(frame, bg=self.app.colors['bg'], highlightthickness=1, highlightbackground="gray")
                    img_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

                    self.tut_images.append(orig_img)

                    # CRITICAL FIX: Isolated Closure for each individual Canvas
                    def make_resize_handler(c, i):
                        def handler(event):
                            c.delete("all")
                            if event.width <= 1 or event.height <= 1: return
                            ratio = min(event.width / i.width, event.height / i.height)
                            if ratio > 1: ratio = 1

                            new_w = max(1, int(i.width * ratio))
                            new_h = max(1, int(i.height * ratio))

                            resized = i.resize((new_w, new_h), Image.Resampling.LANCZOS)
                            photo = ImageTk.PhotoImage(resized)

                            c.image = photo
                            c.create_image(event.width//2, event.height//2, anchor=tk.CENTER, image=photo)
                        return handler

                    img_canvas.bind("<Configure>", make_resize_handler(img_canvas, orig_img))

                except Exception as e:
                    print(f"Error drawing image: {e}")
            else:
                tk.Label(frame, text=f"[ Missing: {img_name} ]", bg=self.app.colors['bg'], fg="red").pack(side=tk.LEFT, padx=5, expand=True)

    def render_tut_step(self):
        for widget in self.tut_content_frame.winfo_children():
            widget.destroy()
            
        self.btn_back.config(state="normal" if self.tut_step > 0 else "disabled")
        self.btn_next.config(text="Finish" if self.tut_step == 7 else "Next >")
        
        bg = self.app.colors['bg']
        fg = self.app.colors['fg']
        
        hk_copy = self.app.config.get("hotkeys", {}).get("Copy Code to Clipboard", "ctrl+alt+c").upper()
        hk_auto = self.app.config.get("hotkeys", {}).get("Auto-Login", "ctrl+alt+q").upper()

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
                from plugins.qr_scanner import ScreenQRScannerPlugin
                for p in self.app.plugin_manager.plugins:
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
            
            self.auto_paste_tut_var = tk.BooleanVar(value=self.app.config["hotkeys"].get("auto_paste", False))
            ttk.Checkbutton(self.tut_content_frame, text="Enable 'Auto-Paste' for the Copy shortcut (injects keystrokes & hits enter)", variable=self.auto_paste_tut_var, command=self._tut_save_settings).pack(pady=10, anchor="w")

        elif self.tut_step == 6:
            tk.Label(self.tut_content_frame, text="Configuration: Auto-Login", font=("Helvetica", 16, "bold"), bg=bg, fg=fg).pack(pady=10)
            tk.Label(self.tut_content_frame, text="Login as normal and manually click 'I can't use my Outlook mobile app right now'. You will reach the 'Verify your identity' screen shown below.", justify=tk.LEFT, bg=bg, fg=fg, wraplength=450).pack(pady=5)
            
            self._add_tut_imgs_side_by_side(['tut_waystoverify.png', 'tut_waystoverify_3.png'])
            
            tk.Label(self.tut_content_frame, text="How many options appear on this screen for you? (App, Text, Call, etc)", bg=bg, fg=fg).pack(anchor="w", pady=(10,0))
            self.ways_tut_var = tk.StringVar(value=str(self.app.config["hotkeys"].get("auto_login_ways", 2)))
            self.app.create_styled_entry(self.tut_content_frame, self.ways_tut_var).pack(fill=tk.X, pady=5)
            self.ways_tut_var.trace_add("write", lambda *args: self._tut_save_settings())

            test_desc = f"Once configured, make sure your browser window is active (clicked on), and press your Auto-Login shortcut ({hk_auto}) to run the macro!"
            tk.Label(self.tut_content_frame, text=test_desc, font=("Helvetica", 10, "italic"), bg=bg, fg="gray", wraplength=450, justify=tk.LEFT).pack(pady=(15,5))

        elif self.tut_step == 7:
            tk.Label(self.tut_content_frame, text="Ready to Go!", font=("Helvetica", 16, "bold"), bg=bg, fg=fg).pack(pady=10)
            tk.Label(self.tut_content_frame, text="OpenAuth is designed to run silently in the background.\n\nWhen you close the window using the 'X', it will hide in your System Tray. Double-click the tray icon to open it, or Right-Click it to instantly copy your code.", justify=tk.LEFT, bg=bg, fg=fg, wraplength=450).pack(pady=10)
            
            self.boot_tut_var = tk.BooleanVar(value=self.app.config.get("start_on_boot", False))
            ttk.Checkbutton(self.tut_content_frame, text="Start OpenAuth silently with Windows", variable=self.boot_tut_var, command=self._tut_save_settings).pack(pady=10, anchor="w")
            
            tk.Label(self.tut_content_frame, text="You can change all of these settings later by clicking the 'Settings' button in the main app.", justify=tk.LEFT, bg=bg, fg="gray", wraplength=450).pack(pady=20)

    def _tut_save_settings(self):
        try:
            if hasattr(self, 'boot_tut_var'):
                self.app.config["start_on_boot"] = self.boot_tut_var.get()
                self.app.manage_startup(self.boot_tut_var.get())
            if hasattr(self, 'auto_paste_tut_var'):
                self.app.config["hotkeys"]["auto_paste"] = self.auto_paste_tut_var.get()
            if hasattr(self, 'ways_tut_var'):
                try:
                    self.app.config["hotkeys"]["auto_login_ways"] = int(self.ways_tut_var.get())
                except ValueError:
                    pass
            self.app.save_config()
            self.app.plugin_manager.broadcast('config_updated')
        except Exception:
            pass