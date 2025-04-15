@echo off
setlocal EnableDelayedExpansion

:start
cls
echo.
echo ================================
echo    SISTEM PARKIR RSI BNA
echo ================================
echo.

echo [%date% %time%] Starting parking system...
echo.

REM Activate the correct environment
call myenv\Scripts\activate.bat

REM Run the parking system
python parking_camera_windows.py

echo [%date% %time%] Program ended. Restarting in 5 seconds...
echo.
timeout /t 5 /nobreak
echo.
goto start 