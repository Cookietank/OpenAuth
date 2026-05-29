<div align="center">

# 🛡️ OpenAuth
**The Modular Desktop Authenticator for Windows & macOS**

[![OS](https://img.shields.io/badge/OS-Windows%20%7C%20macOS-blue?style=flat-square&logo=windows)](https://github.com/cookietank/OpenAuth)
[![Python](https://img.shields.io/badge/Python-3.10+-yellow?style=flat-square&logo=python)](https://www.python.org/)
[![Status](https://img.shields.io/badge/Status-Beta-success?style=flat-square)]()

OpenAuth is a lightning-fast desktop 2FA/MFA authenticator. Designed specifically for users of Microsoft enterprise services, it deeply integrates into your computer to bypass the friction of constantly checking your phone for login codes—saving you hours of frustration!

### 📥 Download the Latest Version

[![](https://img.shields.io/badge/Download_for-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/cookietank/OpenAuth/releases/latest)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
[![](https://img.shields.io/badge/Download_for-macOS-000000?style=for-the-badge&logo=apple&logoColor=white)](https://github.com/cookietank/OpenAuth/releases/latest)

<br>

[Report a Bug](../../issues) • [Request a Feature](../../issues)

</div>

---

## 🚀 How to Install & Run

OpenAuth requires **no complicated installation**. Just download the file for your computer and follow the quick steps below!

### 🪟 For Windows Users
1. Click the Windows download button above and download the latest **`OpenAuth_vX.X.X.exe`** file.
2. Move the `.exe` file wherever you want to keep it (like your Desktop or Documents folder).
3. **Double-click** the file to run it.

> 🛑 **"Windows protected your PC" Popup?**
> Because OpenAuth is built by an independent developer, Windows SmartScreen will show a blue warning screen the first time you open it. 
> * **The Fix:** Simply click **More info** text right under the warning, then click the **Run anyway** button.

> 🛡️ **Security Check:** You can view the clean [VirusTotal Scan Results for OpenAuth.exe here](https://www.virustotal.com/gui/file/bdf0dfdf976d1630112cd1126e40656ab4b3268e6b48d900b1d293f56f0d7cd7/detection).

<br>

### 🍏 For macOS Users
1. Click the macOS download button above and download the latest **`OpenAuth_vX.X.X_macOS.dmg`** file.
2. Double-click the downloaded `.dmg` file to open it.
3. Drag the **OpenAuth** shield icon into the **Applications** folder right next to it.
4. Open your Mac's Applications folder and find OpenAuth.

> 🛑 **"Developer cannot be verified" Popup?**
> Apple has strict security for apps not downloaded from the App Store. If you double-click the app normally, Apple will block it from opening.
> * **The Fix:** Hold the `Control` key on your keyboard and click the OpenAuth app (or just **Right-Click** it), then select **Open** from the menu. When the warning pops up, click the **Open** button. *(You only have to do this trick on the very first launch!)*

---

### 🎉 Next Steps
Once you have bypassed the security warning, OpenAuth will greet you with a friendly, interactive setup wizard that will guide you step-by-step on how to add your first account!

---

## ✨ Core Features

* 🔒 **Zero-Trust Secure Storage:** Your MFA secrets are never written to plain text. OpenAuth encrypts and stores them directly in the native Windows Credential Vault.
* ☁️ **Automatic Updates:** OpenAuth checks GitHub for updates and hot-swaps itself to the latest version.
* 📉 **System Tray & Startup:** Automatic startup and easy access from the system tray.
* 🪶 **Lightweight** Runs silently in the background consuming <50MB of RAM.
* 🎒 **Data Portability:** Securely backup and export your raw 2FA URIs at any time.

---

## 🗺️ Development Roadmap

We are actively building out OpenAuth to be the ultimate 2FA ecosystem. Here is what is currently planned for future releases:

- [ ] **PRIORITY! macOS Version:** Full cross-platform compatibility with native Keychain secure storage and Apple Silicon support.
- [x] **NTP Time-Drift Protection:** Automatic system clock validation on startup to prevent failing codes caused by out-of-sync Windows clocks.
- [x] **Privacy Blur Mode:** A UI toggle to hide TOTP codes behind a blur effect by default—perfect for preventing leaks when screen-sharing on Zoom or Teams.
- [ ] **Authy & Google Authenticator Importer:** Easy 1-click migration for users looking for an alternative following the discontinuation of Authy Desktop.
- [ ] **Zero-Touch Browser Extension:** A lightweight Chrome/Firefox companion extension that detects Microsoft login pages, talks to the OpenAuth local API, and injects the 6-digit code instantly without keyboard macros.

---

## 🧩 Module Documentation

OpenAuth's functionality is split into modules. You can enable or disable them instantly via the **Settings** menu.

### 1. ⌨️ Copy Code to Clipboard (Virtual YubiKey)
Interact with your primary 2FA account globally, without ever opening the app.
* **Hotkey Copy:** Press `Ctrl+Alt+C` anywhere in Windows to silently copy your current 6-digit code.
* **Auto-Paste:** If enabled in settings, pressing the hotkey will instantly *type* the 6-digit code and press `Enter` using hardware-level keystroke injection.
* **The 3-Second Rule:** If a code is about to expire, OpenAuth will pop up a warning, wait for the clock to roll over, and copy the fresh code automatically.

### 2. 🤖 Auto-Login (RDP Safe)
A robust keystroke macro designed to navigate the Microsoft Login portal automatically. 
* Wait until you reach the Microsoft screen asking you to verify your identity, then press `Ctrl+Alt+Q`.
* OpenAuth will navigate the DOM via `Tab` keystrokes, wait for RDP network clipboards to sync, paste your code, and log you in.
* *Note: You can adjust the "Network Delay" and the "Ways to Verify" count in settings to perfectly match your specific enterprise login flow.*

### 3. 📱 Tailscale Phone Sync
Hosts a micro-API secured by WireGuard and Bearer Tokens to beam codes instantly to your Android phone via your Tailscale VPN.

<details>
<summary><b>👉 Click here for Android Setup Instructions</b></summary>

1. Turn on the **Tailscale Phone Sync** plugin in OpenAuth settings and copy your Secret API Token.
2. On your Android phone, download **[HTTP Request Shortcuts](https://play.google.com/store/apps/details?id=ch.rmy.android.http_shortcuts)**.
3. Create a new `GET` shortcut pointing to `http://<YOUR_DESKTOP_TAILSCALE_IP>:<PORT>`.
4. Add a Request Header: `Authorization: Bearer <YOUR_API_TOKEN>`.
5. Under the **Scripting -> On Success** tab, add this JavaScript:
   ```javascript
   copyToClipboard(response.body);
   showToast("Copied: " + response.body);
   ```
6. Add the shortcut to your Android Quick Settings (Pulldown menu).
7. *Swipe down, tap the tile, and copy your desktop's MFA code to your phone in <80ms!*
</details>

### 4. 📸 Account Provisioning
OpenAuth offers two ways to add your accounts:
* **Screen QR Scanner:** Uses Computer Vision to scan your active monitors, locate a standard Microsoft/Google QR code, decode it, and provision the account instantly.
* **Manual Entry:** Paste an `otpauth://` URI or manually type in your raw Secret Key.

### 5. 📡 Local Broadcaster (For Developers)
When enabled, OpenAuth broadcasts the current 6-digit code over local UDP every 30 seconds. Port mapping starts at `50000` for your Primary account. This allows local scripts (like AutoHotkey or OBS) to listen to the socket and trigger automated workflows.

---

## 🗑️ Uninstallation & Factory Reset

Because OpenAuth is a portable executable, it does not appear in the Windows "Add or Remove Programs" list. To completely wipe all OpenAuth data from your machine, you have two options:

1. **GUI Method:** Open the app, click **Settings -> Advanced**, and click the red **Factory Reset / Uninstall** button.
2. **CLI Method:** Open Command Prompt and run `OpenAuth.exe --uninstall`. 

*Both methods will securely wipe your 2FA keys from the OS Keyring, delete all configurations, remove the app from Windows Startup, and close. You can then safely delete the `.exe` file.*

---

## 🧑‍💻 Developer Guide (Build from Source)

Want to read the code, audit the security, or compile it yourself? OpenAuth is 100% open source.

**Requirements:**
* Python 3.10+
* `pip install pyotp pillow pyzbar keyring pystray keyboard pyautogui`

**To compile the `.exe` manually:**
Ensure you are in the project root directory and run the following PyInstaller command:
```bash
pyinstaller --noconsole --onefile --name "OpenAuth" --icon=plugins/icon.ico --add-data "plugins/*;plugins" --collect-all pyzbar --collect-all keyring --hidden-import PIL._tkinter_finder app.py
```
---

## ❓ FAQ

**Q: Does OpenAuth require an internet connection?**  
**A:** **No.** Generating TOTP codes is mathematically based on your local system clock. Internet is only required if you have OTA Auto-Updates enabled. Tailscale Phone Sync requires a LAN or VPN connection to your phone.

**Q: Where are my configurations saved?**  
**A:** App settings, UI themes, and hotkeys are saved to `%APPDATA%\OpenAuth\app_config.json`. Your 2FA secrets are securely encrypted in the Windows Credential Vault.

**Q: The Auto-Login macro clicks/tabs to the wrong place.**  
**A:** Enterprise tenants configure Azure AD differently. If your login page shows options like "Text message" or "Call my phone" *before* the Authenticator option, increase the **Auto-Login 'Ways to Verify' count** in your settings to `3` or `4` so the macro knows how many times to press `Tab`. 

**Q: How do I report a bug?**  
**A:** Open the app, go to Settings, and click **Report an Issue**. It will automatically copy a bug report template to your clipboard and open the correct folder so you can drag-and-drop your `openauth.log` file directly into GitHub!
