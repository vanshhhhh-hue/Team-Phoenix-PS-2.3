@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo First follow the setup commands in README.md.
  pause
  exit /b 1
)
echo Phoenix Study: open http://127.0.0.1:8501 in your browser. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501
if errorlevel 1 pause
