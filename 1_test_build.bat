@echo off
title OpenAuth Test Compiler
echo ========================================
echo 🔨 Compiling Test Build
echo ========================================
echo.

echo [*] Cleaning old builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del /q "*.spec"

echo [*] Compiling OpenAuth_Test.exe...
pyinstaller --noconsole --onefile --name "OpenAuth_Test" --icon=plugins/icon.ico --add-data "plugins/*;plugins" --collect-all pyzbar --collect-all keyring --hidden-import PIL._tkinter_finder app.py

echo.
echo ========================================
echo ✅ Test Build complete! Check the 'dist' folder.
echo ========================================
pause