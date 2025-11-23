@echo off
cd /d "%~dp0"
call venv\Scripts\activate
echo Starting Garmin Health Data Logger...
echo This window will stay open and run the logger every hour.
echo Press Ctrl+C to stop.
python main.py
pause
