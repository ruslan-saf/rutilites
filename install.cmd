@echo off
rem Double-click to install RuTilites (dependencies, autostart, first launch).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
echo.
pause
