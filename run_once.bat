@echo off
cd /d "%~dp0"
call venv\Scripts\activate
echo Running Garmin Health Data Logger (Once)...
python main.py --once
pause
