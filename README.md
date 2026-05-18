Here is a complete, highly-polished GitHub README.md file for OpenAuth. It is
formatted to industry standards, using clear headings, code blocks, bullet
points, and emojis for readability.

You can save this as README.md in your project folder, and when you push it to
GitHub, it will automatically render into a beautiful documentation page!

🛡️ OpenAuth - The Modular Desktop Authenticator

OpenAuth is a lightning-fast, edge-computed, modular desktop 2FA/MFA
authenticator built in Python. Designed for power users and enterprise
workflows, it bypasses the need to constantly check your phone for TOTP codes by
deeply integrating into Windows.

It features Zero-Trust Secure Storage (Windows Credential Vault), Over-The-Air
(OTA) Updates, and is fully resilient over Remote Desktop (RDP) connections.

📑 Table of Contents

1.  📥 Quick Start Guide
2.  ⚙️ Core Functionality
3.  🧩 Plugin Documentation
4.  🛠️ Settings & Advanced Configuration
5.  🧑‍💻 Developer Guide (Building from Source)
6.  ❓ FAQ

📥 Quick Start Guide

OpenAuth requires no installation or Python environment to run.

1.  Download: Go to the Releases page and download the latest
    OpenAuth_vX.X.X.exe.
2.  Run: Double-click the .exe to launch the app.
3.  Provision an Account:
      - Go to your Microsoft Security Info page (aka.ms/mfasetup) or any other
        service.
      - Click + Add sign-in method -> Authenticator app.
      - ⚠️ Important: Click the small text that says "I want to use a different
        authenticator app".
      - Click Next until the QR code is displayed on your screen.
      - In the OpenAuth app, click Scan Screen in the top toolbar.

The app will instantly grab the QR code, securely encrypt the secret, and begin
generating your 6-digit codes!

⚙️ Core Functionality

🥇 Primary Accounts & Drag-and-Drop

OpenAuth supports multiple accounts, but plugins (like Hotkeys and Phone Sync)
always target your Primary Account.

  - The account at the very top of your list is highlighted in blue and marked
    as your ★ PRIMARY ACCOUNT.
  - To change your Primary Account, click and hold the ≡ drag handle next to any
    account, move it to the top, and let go.
  - Your account order is saved automatically to the OS Keychain.

🔒 Zero-Trust Security

Your MFA secrets (base32 seeds) are never written to a text file. OpenAuth
securely injects them into the native Windows Credential Manager / Keychain.
They cannot be easily extracted by other apps without triggering OS-level
security warnings.

🧩 Plugin Documentation

OpenAuth is built on a modular architecture. You can enable or disable these
modules at any time via Settings -> Plugins & Hotkeys.

1. 📋 Copy Code to Clipboard (Virtual YubiKey)

Provides a global, system-wide keyboard shortcut to interact with your Primary
Account without opening the app.

  - Hotkey Copy: Press the shortcut (Default: Ctrl+Alt+C) anywhere in Windows to
    silently copy the current 6-digit code to your clipboard.
  - Auto-Paste Mode: If enabled in settings, pressing the hotkey will instantly
    type the 6-digit code and press Enter using hardware-level keystroke
    injection.
  - The 3-Second Rule: If a code has 3 seconds or less remaining when you press
    the hotkey, OpenAuth will pop up a warning, wait for the clock to roll over,
    and copy the fresh code so you never paste an expired token.

2. 🤖 Auto-Login

A robust, RDP-safe macro designed to automatically navigate Microsoft Login
screens.

  - How to use: When you reach the Microsoft page asking you to open your
    Authenticator App, press the shortcut (Default: Ctrl+Alt+Q).
  - What it does: The macro releases modifier keys, simulates Tab and Enter
    inputs to navigate the DOM to the manual verification page, waits for the
    RDP network clipboard to sync, pastes the code, and submits the form.
  - Configuration: You can adjust the "Network Delay" and the "Ways to Verify"
    count in settings to perfectly match your enterprise tenant's login flow.

3. 📱 Tailscale Phone Sync

Hosts a micro-API secured by WireGuard and Bearer Tokens to beam codes instantly
to your Android phone.

  - How it works: OpenAuth runs a lightweight HTTP server on 0.0.0.0:50051.
    Because Tailscale automatically encrypts traffic between your devices, it
    acts as a zero-trust Edge server.
  - Android Setup:
    1.  Download HTTP Request Shortcuts from the Google Play Store.
    2.  Create a new GET shortcut pointing to
        http://<YOUR_DESKTOP_TAILSCALE_IP>:50051.
    3.  Add a Header: Authorization: Bearer <YOUR_API_TOKEN_FROM_SETTINGS>.
    4.  In the Scripting -> "On Success" tab, add:
        copyToClipboard(response.body); showToast("Copied: " + response.body);.
    5.  Add the shortcut to your Android Quick Settings (Pulldown menu).
  - You can now pull down your phone menu, tap the tile, and copy your desktop's
    MFA code in <80 milliseconds!

4. 🖼️ Screen QR Scanner

Uses pyzbar and Computer Vision to take a screenshot of your active monitors,
locate a standard otpauth://totp/ QR code, decode the URI, and provision the
account locally.

5. 📉 Tray Icon

Minimizes the application silently to the Windows System Tray.

  - Double-click the tray icon to restore the window.
  - Right-click the tray icon and select Copy Primary Code to instantly copy
    your code and trigger a native Windows Toast Notification confirming
    success.

6. 📡 Local Broadcaster (Advanced)

Intended for Developers. When enabled, OpenAuth broadcasts the current 6-digit
code over local UDP every 30 seconds.

  - Port mapping starts at 50000 for your Primary account, 50001 for your second
    account, etc.
  - This allows local scripts or OBS integrations to listen to the UDP socket
    and trigger actions automatically upon receiving a new code.

🛠️ Settings & Advanced Configuration

Click the Settings button in the top right of the app to access:

  - Start with Windows: Writes a native OS registry key to silently boot
    OpenAuth into your system tray when you log in.
  - Auto-Update: Silently polls the GitHub API on launch. If a newer release is
    found via semantic versioning (e.g., v1.3.2 > v1.3.1), it prompts you to
    download and seamlessly hot-swaps the .exe file automatically.
  - Theme: Live-toggles the UI between Light and Dark mode.
  - Regenerate API Token: Instantly invalidates your Tailscale Phone Sync token
    and generates a new cryptographically secure 32-character key.

(Note: Configuration data is stored locally in
%APPDATA%\OpenAuth\app_config.json).

🧑‍💻 Developer Guide

If you wish to clone the repository and build the executable yourself:

Requirements

  - Python 3.10+
  - pip install pyotp pillow pyzbar keyring pystray keyboard pyautogui

Adding New Plugins

OpenAuth is designed for infinite extensibility. To add a new feature:

1.  Create a new .py file in the plugins/ directory inheriting from PluginBase.
2.  Use the setup(self) or config_updated(self) hooks to inject UI elements or
    start background threads.
3.  Register the plugin inside app.py in the AVAILABLE_PLUGINS dictionary.

❓ FAQ

Q: Windows Defender flagged the .exe as a virus! Is it safe?
A: This is a common "False Positive" caused by the PyInstaller compiler, which
wraps a Python interpreter into an .exe. We provide a VirusTotal Scan Link on
the Releases page to guarantee safety. You are also encouraged to read the
source code and compile it yourself using the Developer Guide above!

Q: The Auto-Login macro clicks/tabs to the wrong place.
A: Enterprise tenants configure Azure AD differently. If your login page shows
options like "Text message" or "Call my phone" before the Authenticator option,
increase the Auto-Login 'Ways to Verify' count in your settings to 3 or 4 so the
macro knows how many times to press Tab.

Q: Does OpenAuth require an internet connection?
A: No. Generating TOTP codes is 100% offline and mathematically based on your
system clock. Internet is only required if you have OTA Auto-Updates enabled.
Tailscale Phone Sync requires a LAN or VPN connection to your phone.

Q: Where are my configurations saved?
A: App settings, UI themes, and hotkeys are saved to
%APPDATA%\OpenAuth\app_config.json. Your actual 2FA secrets are securely
encrypted in the Windows Credential Vault.

**Q: How do I completely uninstall OpenAuth?**  
**A:** Because OpenAuth runs as a portable `.exe`, it doesn't appear in the Windows "Add or Remove Programs" list. You have two options:
1. **GUI Method:** Open the app, click **Settings -> Advanced**, and click the red **Factory Reset / Uninstall** button.
2. **CLI Method:** Open Command Prompt and run `OpenAuth.exe --uninstall`. 
*Both methods will permanently securely wipe your 2FA keys from the OS Keyring, delete all config files, remove the app from Windows Startup, and close. You can then simply delete the `.exe` file.*
