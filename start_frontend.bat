@echo off
cd /d "%~dp0frontend"
set WEB_MODE=1
set WEB_PORT=8082
..\venv\Scripts\python.exe main.py
