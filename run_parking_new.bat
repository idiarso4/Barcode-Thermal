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
echo.
echo Tekan 'p' untuk simulasi kendaraan masuk
echo Tekan Ctrl+C untuk keluar
echo.

:: Gunakan Python dari myenv secara langsung
set PYTHON_PATH=C:\AAA\myenv\Scripts\python.exe

:: Jalankan program dengan error handling
:retry
"%PYTHON_PATH%" parking_camera_windows.py 2>&1
if errorlevel 1 (
    echo.
    echo [%date% %time%] Program terminated with error.
    echo.
    echo Press any key to restart...
    pause >nul
    goto retry
)

:: Jika program selesai normal
echo.
echo [%date% %time%] Program ended normally.
echo Press any key to restart...
pause >nul
goto start 