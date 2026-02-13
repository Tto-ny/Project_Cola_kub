@echo off
echo ========================================
echo   Landslide Early Warning System
echo ========================================
echo.

REM Activate virtual environment
call landslide_env\Scripts\activate.bat

REM Run the system
python run.py

pause
