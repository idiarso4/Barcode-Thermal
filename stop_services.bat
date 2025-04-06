@echo off
title Stop Parking System Services
echo ================================
echo     STOP PARKING SERVICES
echo ================================
echo.

echo [%date% %time%] Menghentikan semua proses parkir...

:: Menghentikan semua instance Python yang berjalan
echo Menghentikan proses Python...
taskkill /F /IM python.exe /T
taskkill /F /IM py.exe /T

:: Menghentikan proses yang menggunakan port serial
echo Membebaskan port serial...
FOR /F "tokens=1" %%i IN ('wmic process where "commandline like '%%COM%%'" get processid ^| findstr [0-9]') DO (
    echo Menghentikan proses: %%i
    taskkill /F /PID %%i
)

:: Membersihkan koneksi printer
echo Membersihkan koneksi printer...
net stop spooler
ping 127.0.0.1 -n 3 > nul
net start spooler

echo.
echo [%date% %time%] Semua layanan berhasil dihentikan.
echo.
echo Silakan jalankan kembali sistem parkir dengan "start_parking.bat"
echo.

pause 