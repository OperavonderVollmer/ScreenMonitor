@echo off
setlocal

cd /d "%~dp0"

title ScreenMonitor

start "" ".\venv\Scripts\pythonw.exe" ".\main.py"
