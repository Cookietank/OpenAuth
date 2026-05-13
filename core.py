import pyotp
import urllib.parse
import time

class StandardAuthAccount:
    def __init__(self, uri):
        self.uri = uri
        
        parsed_uri = urllib.parse.urlparse(uri)
        if parsed_uri.scheme != "otpauth" or parsed_uri.netloc != "totp":
            raise ValueError("Only OATH TOTP is supported.")
            
        qs = urllib.parse.parse_qs(parsed_uri.query)
        if 'secret' not in qs:
            raise ValueError("No secret key found in the QR code.")
            
        secret = qs['secret'][0]
        
        # Extract Meta-data robustly (avoids pyotp's strict mismatch error)
        self.issuer = qs.get('issuer', ['Unknown'])[0]
        path_label = urllib.parse.unquote(parsed_uri.path.lstrip('/'))
        
        # Clean up path label (e.g., "Microsoft:user@domain.com")
        if ':' in path_label:
            parts = path_label.split(':', 1)
            if self.issuer == 'Unknown':
                self.issuer = parts[0]
            self.name = parts[1].strip()
        else:
            self.name = path_label

        # Extract standard parameters
        interval = int(qs.get('period', [30])[0])
        digits = int(qs.get('digits', [6])[0])
        algorithm = qs.get('algorithm', ['SHA1'])[0].upper()

        if interval != 30 or digits != 6:
            raise ValueError("Account does not match 6-digit, 30-second OATH standard.")
        
        if algorithm != 'SHA1':
            print(f"Warning: Microsoft expects SHA1, but {algorithm} was found.")

        # Construct TOTP manually to bypass strict pyotp URI parsing checks
        self.totp = pyotp.TOTP(secret, digits=digits, interval=interval)

    def get_current_code(self):
        return self.totp.now()

    def get_time_remaining(self):
        return 30 - (int(time.time()) % 30)