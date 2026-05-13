@echo off
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
echo [*] Staging and Committing...
git add .
git commit -m "%msg%"

echo [*] Pushing to GitHub...
git push

echo.
echo ========================================
echo ✅ Code safely backed up to GitHub!
echo ========================================
pause