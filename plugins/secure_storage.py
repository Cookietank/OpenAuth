import json
import keyring
from plugin_manager import PluginBase

class SecureStoragePlugin(PluginBase):
    SERVICE_NAME = "ModularDesktopAuthenticator"
    ACCOUNT_KEY = "TOTP_Secrets"

    def setup(self):
        # Intercept app's add/remove/reorder methods to trigger saving
        self._original_add_account = self.app.add_account
        self._original_remove_account = getattr(self.app, 'remove_account', None)
        self._original_trigger_save = getattr(self.app, 'trigger_save', None)
        
        self.app.add_account = self._hooked_add_account
        if self._original_remove_account:
            self.app.remove_account = self._hooked_remove_account
        if self._original_trigger_save:
            self.app.trigger_save = self._hooked_trigger_save

        self.load_accounts()

    def load_accounts(self):
        stored_data = keyring.get_password(self.SERVICE_NAME, self.ACCOUNT_KEY)
        if stored_data:
            try:
                uris = json.loads(stored_data)
                for uri in uris:
                    self._original_add_account(uri)
            except Exception as e:
                print(f"Failed to load accounts securely: {e}")

    def _hooked_add_account(self, uri):
        success = self._original_add_account(uri)
        if success:
            self.save_accounts()
        return success

    def _hooked_remove_account(self, account):
        self._original_remove_account(account)
        self.save_accounts()
        
    def _hooked_trigger_save(self):
        """Intercepts the empty trigger_save hook from app.py when drag&drop happens"""
        self.save_accounts()

    def save_accounts(self):
        uris = [acc.uri for acc in self.app.accounts]
        try:
            keyring.set_password(self.SERVICE_NAME, self.ACCOUNT_KEY, json.dumps(uris))
        except Exception as e:
            print(f"Failed to save accounts securely: {e}")