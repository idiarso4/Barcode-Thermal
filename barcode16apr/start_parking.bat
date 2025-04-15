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

:: Aktifkan virtual environment
call venv311\Scripts\activate.bat

:: Pastikan semua paket terinstall
pip install -q requests python-dotenv pywin32 psycopg2-binary opencv-python numpy pyserial psutil

:: Cek versi Python
echo [%date% %time%] Python version:
python --version

:: Cek koneksi Arduino
echo [%date% %time%] Checking Arduino connection...
python check_arduino.py

:: Jalankan program dengan error handling
:retry
echo [%date% %time%] Starting main program...
python parking_camera_windows.py

if errorlevel 1 (
    echo.
    echo [%date% %time%] Program terminated with error. Restarting in 5 seconds...
    timeout /t 5 /nobreak
    goto retry
)

echo [%date% %time%] Program ended. Restarting in 5 seconds...
echo.
timeout /t 5 /nobreak
goto start
