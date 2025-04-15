@echo off
echo ===================================
echo    SETUP FIREWALL UNTUK SISTEM PARKIR
echo ===================================
echo.

REM Perlu dijalankan sebagai Administrator
NET SESSION >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Silakan jalankan script ini sebagai Administrator!
    echo Klik kanan pada file dan pilih "Run as administrator"
    pause
    exit
)

echo Menambahkan pengecualian firewall untuk C:\AAA...
echo.

REM Buat aturan untuk Python executables
echo 1. Membuat aturan untuk Python...
netsh advfirewall firewall add rule name="Allow Python (C:\AAA)" dir=in action=allow program="C:\AAA\myenv\Scripts\python.exe" enable=yes profile=any
netsh advfirewall firewall add rule name="Allow Python - Outbound (C:\AAA)" dir=out action=allow program="C:\AAA\myenv\Scripts\python.exe" enable=yes profile=any

REM Buat aturan untuk folder C:\AAA
echo 2. Membuat pengecualian folder untuk C:\AAA...
netsh advfirewall firewall add rule name="Allow C:\AAA Folder Access" dir=in action=allow program="%SystemRoot%\explorer.exe" enable=yes profile=any
netsh advfirewall firewall add rule name="Allow C:\AAA Folder Access - Out" dir=out action=allow program="%SystemRoot%\explorer.exe" enable=yes profile=any

REM Buka port database PostgreSQL
echo 3. Membuka port 5432 untuk PostgreSQL...
netsh advfirewall firewall add rule name="PostgreSQL Database (5432)" dir=in action=allow protocol=TCP localport=5432 enable=yes profile=any
netsh advfirewall firewall add rule name="PostgreSQL Database (5432) - Out" dir=out action=allow protocol=TCP localport=5432 enable=yes profile=any

REM Buka port API
echo 4. Membuka port 5051 untuk API...
netsh advfirewall firewall add rule name="Parking API (5051)" dir=in action=allow protocol=TCP localport=5051 enable=yes profile=any
netsh advfirewall firewall add rule name="Parking API (5051) - Out" dir=out action=allow protocol=TCP localport=5051 enable=yes profile=any

echo.
echo Firewall rules berhasil ditambahkan! Sistem parkir sekarang tidak akan diblokir oleh firewall.
echo.
pause 