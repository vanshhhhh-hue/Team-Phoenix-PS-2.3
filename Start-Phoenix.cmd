@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First follow the setup commands in README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\run_phoenix.py
if errorlevel 1 pause
