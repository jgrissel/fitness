@echo off
cd /d "%~dp0"
call venv\Scripts\activate
echo.
echo --- Garmin Data Backfill Tool ---
echo.
set /p start_date="Enter Start Date (YYYY-MM-DD): "
set /p end_date="Enter End Date (YYYY-MM-DD): "
echo.
echo Starting backfill from %start_date% to %end_date%...
echo This may take a while depending on the range.
echo.
python backfill.py --start %start_date% --end %end_date%
pause
