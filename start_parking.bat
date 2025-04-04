@echo off
title Sistem Parkir RSI BNA
cd /d "C:\AAA"

:start
echo.
echo ================================
echo    SISTEM PARKIR RSI BNA
echo ================================
echo.
echo [%date% %time%] Starting parking system...

:: Aktifkan Python virtual environment jika ada
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

:: Jalankan program dengan error handling
:retry
py -3.11 parking_camera_windows.py
if errorlevel 1 (
    echo.
    echo [%date% %time%] Program terminated with error. Restarting in 5 seconds...
    timeout /t 5 /nobreak
    goto retry
)

:: Jika program selesai normal, tunggu 5 detik sebelum restart
echo.
echo [%date% %time%] Program ended. Restarting in 5 seconds...
timeout /t 5 /nobreak
goto start 