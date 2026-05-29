#!/bin/bash
cd "$(dirname "$0")"

echo "========================================"
echo "🍏 OpenAuth macOS Release Publisher"
echo "========================================"
echo ""

read -p "Enter version number (e.g. 0.1.8.5): " VERSION

echo ""
echo "[*] Pulling latest code from GitHub..."
git pull --rebase

echo "[*] Nuclear Cleanup..."
rm -rf build
rm -rf dist
rm -f *.spec
find . -type d -name "__pycache__" -exec rm -rf {} +

echo "[*] Converting icon to macOS .icns format..."
sips -s format icns plugins/icon.ico --out plugins/icon.icns >/dev/null 2>&1

echo "[*] Compiling OpenAuth_v${VERSION}.app bundle..."
python3 -m PyInstaller --noconsole --windowed --name "OpenAuth_v${VERSION}" --icon="plugins/icon.icns" --add-data "plugins/*:plugins" --collect-all pyzbar --collect-all keyring --hidden-import AppKit --hidden-import ApplicationServices app.py

echo "[*] Creating macOS .dmg Installer..."
cd dist
# Create a temporary staging folder for the DMG
mkdir -p dmg_stage
# Move the compiled app into the staging folder
mv "OpenAuth_v${VERSION}.app" dmg_stage/
# Create a shortcut to the Mac Applications folder
ln -s /Applications dmg_stage/Applications
# Use Apple's native hdiutil to build the Disk Image
hdiutil create -volname "OpenAuth v${VERSION}" -srcfolder dmg_stage -ov -format UDZO "OpenAuth_v${VERSION}_macOS.dmg" >/dev/null 2>&1
# Clean up the staging folder
rm -rf dmg_stage
cd ..

echo ""
echo "[*] Syncing and Pushing macOS changes to GitHub..."
git add .
git commit -m "macOS Release v$VERSION build prep"
git pull --rebase
git push

echo ""
echo "[*] Publishing to GitHub Releases..."
# Check if Windows already made this release page
if gh release view v$VERSION >/dev/null 2>&1; then
    echo "Release v$VERSION exists! Uploading Mac .dmg alongside Windows .exe..."
    gh release upload v$VERSION "dist/OpenAuth_v${VERSION}_macOS.dmg"
else
    echo "Release v$VERSION doesn't exist yet! Creating it..."
    gh release create v$VERSION "dist/OpenAuth_v${VERSION}_macOS.dmg" -t "OpenAuth v$VERSION" -n "Includes macOS build."
fi

echo ""
echo "========================================"
echo "🎉 SUCCESS! Mac .dmg uploaded to GitHub!"
echo "========================================"
