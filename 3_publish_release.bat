@echo off
title OpenAuth Release Manager
echo ========================================
echo 🚀 OpenAuth Automated Release Manager
echo ========================================
echo.

set /p VERSION="Enter new version number (e.g. 1.2.0): "

echo.
echo [*] Updating app.py to v%VERSION%...
python bump_version.py %VERSION%

echo.
echo [*] Opening Notepad++ for release notes...
echo ### What's New in v%VERSION% > release_notes.txt
echo - Added new features >> release_notes.txt
echo - Bug fixes >> release_notes.txt

:: Force Notepad++ to open as a new instance so the script actually pauses!
if exist "C:\Program Files\Notepad++\notepad++.exe" (
    "C:\Program Files\Notepad++\notepad++.exe" -multiInst -nosession release_notes.txt
) else if exist "C:\Program Files (x86)\Notepad++\notepad++.exe" (
    "C:\Program Files (x86)\Notepad++\notepad++.exe" -multiInst -nosession release_notes.txt
) else (
    notepad release_notes.txt
)

echo.
echo [*] Cleaning old builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del /q "*.spec"

echo.
echo [*] Compiling OpenAuth_v%VERSION%.exe...
pyinstaller --noconsole --onefile --name "OpenAuth_v%VERSION%" --icon=plugins/icon.ico --add-data "plugins/*;plugins" --collect-all pyzbar --collect-all keyring --hidden-import PIL._tkinter_finder app.py

echo.
echo [*] Syncing and Pushing source code to GitHub...
:: Pull cloud changes first to prevent the 'rejected' error!
git pull --rebase
git add .
git commit -m "Release v%VERSION%"
git push

echo.
echo [*] Publishing GitHub Release...
gh release create v%VERSION% "dist\OpenAuth_v%VERSION%.exe" -t "OpenAuth v%VERSION%" -F release_notes.txt

del release_notes.txt

echo.
echo ========================================
echo 🎉 SUCCESS! OpenAuth v%VERSION% is live on GitHub!
echo ========================================
pause