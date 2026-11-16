@echo off
cd /d "%~dp0"
echo ========================================================
echo   Rajasthan Royals Scouting Engine - SupeRR Selector
echo ========================================================
echo.
echo Starting Django server on http://127.0.0.1:8000 ...
echo Press Ctrl+C in this terminal to stop the server.
echo.
python manage.py runserver 127.0.0.1:8000
pause
