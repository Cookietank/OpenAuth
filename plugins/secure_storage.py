import json
import os
import sys
import stat
import subprocess
import hashlib
from plugin_manager import PluginBase

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

if IS_WIN:
    try:
        import keyring
    except ImportError:
        pass

class SecureStoragePlugin(PluginBase):
    SERVICE_NAME = "ModularDesktopAuthenticator"
    ACCOUNT_KEY = "TOTP_Secrets"

    def setup(self):
        self._original_add_account = self.app.add_account
        self._original_remove_account = getattr(self.app, 'remove_account', None)
        self._original_trigger_save = getattr(self.app, 'trigger_save', None)
        
        self.app.add_account = self._hooked_add_account
        if self._original_remove_account:
            self.app.remove_account = self._hooked_remove_account
        if self._original_trigger_save:
            self.app.trigger_save = self._hooked_trigger_save

        self.load_accounts()

    # =========================================================
    # MAC-SPECIFIC HARDWARE ENCRYPTION ENGINE
    # =========================================================
    def _get_mac_secrets_path(self):
        appdata = os.path.expanduser('~/Library/Application Support/OpenAuth')
        if not os.path.exists(appdata):
            os.makedirs(appdata)
        return os.path.join(appdata, "secrets.dat")

    def _get_mac_hardware_key(self):
        """Generates a cryptographic key unique to this specific Mac's motherboard."""
        try:
            # Query the macOS I/O Kit for the hardware UUID
            out = subprocess.check_output(['ioreg', '-rd1', '-c', 'IOPlatformExpertDevice']).decode('utf-8')
            for line in out.split('\n'):
                if 'IOPlatformUUID' in line:
                    uuid = line.split('=')[1].strip(' "')
                    # Hash the UUID to create a consistent 32-byte key
                    return hashlib.sha256(uuid.encode('utf-8')).digest()
        except Exception:
            pass
        # Fallback if hardware query fails
        return hashlib.sha256(b"fallback_mac_key_999").digest()

    def _xor_crypt(self, data_bytes, key_bytes):
        """Hardware-bound obfuscation cipher."""
        key_len = len(key_bytes)
        return bytes([b ^ key_bytes[i % key_len] for i, b in enumerate(data_bytes)])

    # =========================================================
    # CORE LOAD & SAVE LOGIC
    # =========================================================
    def load_accounts(self):
        uris = []
        if IS_WIN:
            try:
                stored_data = keyring.get_password(self.SERVICE_NAME, self.ACCOUNT_KEY)
                if stored_data:
                    uris = json.loads(stored_data)
            except Exception as e:
                print(f"Failed to load Windows accounts securely: {e}")
                
        elif IS_MAC:
            secrets_path = self._get_mac_secrets_path()
            if os.path.exists(secrets_path):
                try:
                    with open(secrets_path, "rb") as f:
                        encrypted = f.read()
                    
                    key = self._get_mac_hardware_key()
                    decrypted = self._xor_crypt(encrypted, key).decode('utf-8')
                    uris = json.loads(decrypted)
                except Exception as e:
                    print(f"Failed to load Mac hardware-locked accounts: {e}")

        for uri in uris:
            self._original_add_account(uri)

    def _hooked_add_account(self, uri):
        success = self._original_add_account(uri)
        if success:
            self.save_accounts()
        return success

    def _hooked_remove_account(self, account):
        self._original_remove_account(account)
        self.save_accounts()
        
    def _hooked_trigger_save(self):
        self.save_accounts()

    def save_accounts(self):
        uris = [acc.uri for acc in self.app.accounts]
        
        if IS_WIN:
            try:
                keyring.set_password(self.SERVICE_NAME, self.ACCOUNT_KEY, json.dumps(uris))
            except Exception as e:
                print(f"Failed to save Windows accounts securely: {e}")
                
        elif IS_MAC:
            try:
                secrets_path = self._get_mac_secrets_path()
                key = self._get_mac_hardware_key()
                
                data_bytes = json.dumps(uris).encode('utf-8')
                encrypted = self._xor_crypt(data_bytes, key)
                
                with open(secrets_path, "wb") as f:
                    f.write(encrypted)
                
                # CRITICAL SECURITY: Apply strict OS-level permissions (chmod 600)
                # This ensures NO ONE except the currently logged-in user can read the file!
                os.chmod(secrets_path, stat.S_IRUSR | stat.S_IWUSR)
            except Exception as e:
                print(f"Failed to save Mac hardware-locked accounts: {e}")