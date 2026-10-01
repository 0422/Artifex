@echo off
REM 2026-10-01 Kill leftover backend/frontend processes by port (default 8000).
REM Usage: kill-backend.bat [port...]   e.g. kill-backend.bat 5173
setlocal
powershell -ExecutionPolicy Bypass -NoProfile -File "%~dp0kill-backend.ps1" %*
endlocal
