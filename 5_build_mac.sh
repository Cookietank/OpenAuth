#!/bin/bash
cd "$(dirname "$0")"

echo "========================================"
echo "🍏 Syncing & Compiling OpenAuth for macOS"
echo "========================================"
echo ""

echo "[*] Pulling latest code from GitHub..."
git pull --rebase
echo ""

echo "[*] Nuclear Cleanup..."
rm -rf build
rm -rf dist
rm -f *.spec
find . -type d -name "__pycache__" -exec rm -rf {} +

echo "[*] Converting icon to macOS .icns format..."
sips -s format icns plugins/icon.ico --out plugins/icon.icns >/dev/null 2>&1

echo "[*] Compiling OpenAuth.app bundle..."
python3 -m PyInstaller --noconsole --windowed --name "OpenAuth" --icon="plugins/icon.icns" --add-data "plugins/*:plugins" --collect-all pyzbar --collect-all keyring --hidden-import AppKit --hidden-import ApplicationServices app.py

echo ""
echo "========================================"
if [ -d "dist/OpenAuth.app" ]; then
    echo "✅ Success! You can find OpenAuth.app in the 'dist' folder."
else
    echo "❌ Build failed. Please check the errors above."
fi
echo "========================================"
