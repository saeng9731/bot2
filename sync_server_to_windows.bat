@echo off
rem ============================================================
rem  sync_server_to_windows.bat  (launcher)
rem ============================================================
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0sync_server_to_windows.ps1"
pause
