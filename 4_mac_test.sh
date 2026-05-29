#!/bin/bash

echo "========================================"
echo "🍎 OpenAuth Mac Sync & Test"
echo "========================================"
echo ""

# Ensure we are in the correct directory
cd "$(dirname "$0")"

echo "[*] Pulling latest code from GitHub..."
git pull --rebase
echo ""

echo "[*] Launching OpenAuth..."
# Use python3 (standard for macOS)
python3 app.py

echo ""
echo "========================================"
echo "✅ App closed."
echo "========================================"