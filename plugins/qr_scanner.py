from PIL import ImageGrab, Image
from pyzbar.pyzbar import decode
from plugin_manager import PluginBase
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog

class ScreenQRScannerPlugin(PluginBase):
    def setup(self):
        if hasattr(self.app, 'add_auth_action'):
            self.app.add_auth_action("Scan Screen for QR", self.scan_screen)
            self.app.add_auth_action("Upload QR Image", self.upload_image)
        else:
            self.app.add_toolbar_action("Scan Screen", self.scan_screen)
            self.app.add_toolbar_action("Upload Image", self.upload_image)

    def process_image(self, img):
        decoded_objects = decode(img)
        for obj in decoded_objects:
            data = obj.data.decode('utf-8')
            if data.startswith("otpauth://totp/"):
                success = self.app.add_account(data)
                if success:
                    messagebox.showinfo("Success", "Account provisioned successfully!")
                return True
        return False

    def scan_screen(self):
        try:
            screen = ImageGrab.grab(all_screens=True)
            found = self.process_image(screen)
            if not found:
                messagebox.showwarning("Not Found", "Could not find a valid TOTP QR code on the screen.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to scan screen: {str(e)}")

    def upload_image(self):
        try:
            filepath = filedialog.askopenfilename(
                title="Select QR Code Image",
                filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")]
            )
            if not filepath:
                return 
            
            img = Image.open(filepath)
            found = self.process_image(img)
            if not found:
                messagebox.showwarning("Not Found", "Could not find a valid TOTP QR code in the image.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read image: {str(e)}")