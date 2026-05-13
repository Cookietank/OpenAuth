# 🛡️ OpenAuth - Modular Desktop Authenticator

OpenAuth is a lightweight, edge-computed, modular desktop 2FA/MFA authenticator built in Python. It bypasses the need to constantly check your phone for TOTP codes by deeply integrating into Windows.

### 📥 Download
You can download the latest standalone executable from the **[Releases page](../../releases)**. No installation or Python required!

> 🛡️ **Security Check:** View the [VirusTotal Scan Results for OpenAuth.exe](https://www.virustotal.com/gui/file/bdf0dfdf976d1630112cd1126e40656ab4b3268e6b48d900b1d293f56f0d7cd7/detection)

---

### ✨ Features
* **Zero-Trust Secure Storage:** Native integration with Windows Credential Vault. No secrets are stored in plain text.
* **Screen QR Scanning:** Provisions accounts by using Computer Vision to grab QR codes directly off your screen.
* **Virtual YubiKey:** Global keyboard hotkey (`Ctrl+Alt+C`) to instantly copy or automatically type/inject your primary MFA code anywhere in Windows.
* **Tailscale Phone Sync:** Hosts a micro-API secured by WireGuard and Bearer Tokens to beam codes instantly to Android Quick Tiles via Tailscale.
* **Live Reloading:** Instant Dark Mode and plugin toggling without restarting.
* **Stealth Mode:** Sits silently in the Windows System Tray consuming <30MB of RAM.

---

### 🚀 Getting Started (For Developers)
If you want to run OpenAuth from the source code rather than downloading the `.exe`:
1. Run `pip install pyotp pillow pyzbar keyring pystray keyboard pyautogui`
2. Run `python app.py`

### 📦 Building the Executable
To compile OpenAuth into a portable, single `.exe` file yourself:
```bash
pyinstaller --noconsole --onefile --icon=plugins/icon.ico --add-data "plugins/icon.ico;plugins" --collect-all pyzbar --collect-all keyring --hidden-import PIL._tkinter_finder app.py
