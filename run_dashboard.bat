@echo off
cd /d "%~dp0"
call venv\Scripts\activate
echo Starting Garmin Health Dashboard...
streamlit run dashboard.py
pause
