@echo off
:: Force Command Prompt to render UTF-8 Emojis correctly
chcp 65001 >nul

title OpenAuth Save Progress
echo ========================================
echo ☁️ Backing up to GitHub
echo ========================================
echo.

echo [*] Detecting changes...
git status -s
echo.

set /p msg="Enter commit message (Press Enter to auto-generate timestamp): "
if "%msg%"=="" (
    set msg=Auto-update: %date% %time%
)

echo.
echo [*] 1. Staging and Committing local changes...
git add .
git commit -m "%msg%"

echo.
echo [*] 2. Syncing with GitHub cloud...
git pull --rebase

echo.
echo [*] 3. Pushing to GitHub...
git push

echo.
echo ========================================
echo ✅ Code safely backed up to GitHub!
echo ========================================
pause