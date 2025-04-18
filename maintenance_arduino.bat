@echo off
echo ====================================
echo   Script Pemeliharaan Arduino
echo ====================================
echo.

:: Check for admin privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: Script ini membutuhkan hak administrator.
    echo Mohon jalankan script ini sebagai administrator.
    pause
    exit /b 1
)

:MENU
cls
echo ====================================
echo   MENU PEMELIHARAAN ARDUINO
echo ====================================
echo.
echo  1. Reset Driver USB Serial
echo  2. Periksa Port COM Yang Tersedia
echo  3. Restart Layanan COM
echo  4. Bersihkan Port Yang Tidak Digunakan
echo  5. Periksa Status Koneksi Arduino
echo  6. Bersihkan File Port Terakhir
echo  7. Keluar
echo.
set /p pilihan="Pilih menu (1-7): "

if "%pilihan%"=="1" goto RESET_DRIVER
if "%pilihan%"=="2" goto CHECK_PORTS
if "%pilihan%"=="3" goto RESTART_SERVICES
if "%pilihan%"=="4" goto CLEAN_PORTS
if "%pilihan%"=="5" goto CHECK_CONNECTION
if "%pilihan%"=="6" goto CLEAN_LAST_PORT
if "%pilihan%"=="7" goto EXIT
goto MENU

:RESET_DRIVER
cls
echo ====================================
echo   Reset Driver USB Serial
echo ====================================
echo.
echo Ini akan mereset driver USB Serial dan mencabut-pasang kembali perangkat secara virtual.
echo.
echo Langkah 1: Menghentikan layanan COM dan USB...
sc stop Serial >nul 2>&1
pnputil /scan-devices >nul 2>&1
echo Langkah 2: Mencari dan me-reset perangkat USB Serial...

:: Mencari semua USB Serial dan lakukan reset
set "found=false"
for /f "tokens=1-3 delims=:" %%a in ('pnputil /enum-devices /connected ^| findstr /i "USB Serial"') do (
    echo Menemukan perangkat: %%b
    echo Reset perangkat...
    pnputil /disable-device "%%b" >nul 2>&1
    pnputil /enable-device "%%b" >nul 2>&1
    set "found=true"
)

:: Jika tidak ada perangkat spesifik, reset semua USB
if "%found%"=="false" (
    echo Tidak menemukan perangkat USB Serial spesifik.
    echo Mencoba reset semua USB Controller...
    for /f "tokens=1-3 delims=:" %%a in ('pnputil /enum-devices /connected ^| findstr /i "USB\\ROOT"') do (
        echo Menemukan USB Controller: %%b
        echo Reset controller...
        pnputil /disable-device "%%b" >nul 2>&1
        pnputil /enable-device "%%b" >nul 2>&1
    )
)

echo Langkah 3: Memulai ulang layanan...
sc start Serial >nul 2>&1
pnputil /scan-devices >nul 2>&1

echo.
echo Reset selesai! Silakan cabut dan pasang kembali perangkat Arduino secara fisik juga.
echo.
pause
goto MENU

:CHECK_PORTS
cls
echo ====================================
echo   Periksa Port COM Yang Tersedia
echo ====================================
echo.

echo Mencari port COM yang tersedia...
echo.
wmic path Win32_SerialPort get DeviceID, Caption, Description, PNPDeviceID
echo.

echo Memeriksa port COM yang terpakai oleh proses...
echo.
netstat -ano | findstr "COM"
echo.

echo Memeriksa port terakhir yang digunakan...
if exist "arduino_port.txt" (
    echo Port terakhir yang digunakan:
    type arduino_port.txt
) else (
    echo File arduino_port.txt tidak ditemukan.
)
echo.
pause
goto MENU

:RESTART_SERVICES
cls
echo ====================================
echo   Restart Layanan COM
echo ====================================
echo.

echo Menghentikan layanan Serial...
sc stop Serial >nul 2>&1
echo Menunggu 3 detik...
timeout /t 3 >nul
echo Memulai ulang layanan Serial...
sc start Serial >nul 2>&1

echo Menjalankan pembaruan perangkat...
pnputil /scan-devices >nul 2>&1

echo Memastikan layanan Serial diset ke Automatic...
sc config Serial start= auto >nul 2>&1

echo.
echo Layanan Serial berhasil di-restart!
echo.
pause
goto MENU

:CLEAN_PORTS
cls
echo ====================================
echo   Bersihkan Port Yang Tidak Digunakan
echo ====================================
echo.

echo Ini akan membersihkan semua port COM yang tidak digunakan dari registry.
echo PERHATIAN: Gunakan dengan hati-hati, hanya saat mengalami masalah port phantom.
echo.
set /p konfirmasi="Anda yakin ingin melanjutkan? (Y/N): "
if /i not "%konfirmasi%"=="Y" goto MENU

echo.
echo Membersihkan registry dan port yang tidak digunakan...
reg delete "HKLM\SYSTEM\CurrentControlSet\Control\COM Name Arbiter" /v ComDB /f >nul 2>&1
reg add "HKLM\SYSTEM\CurrentControlSet\Control\COM Name Arbiter" /v ComDB /t REG_BINARY /d 00000000 /f >nul 2>&1
echo Memulai ulang layanan perangkat... 
sc stop Serial >nul 2>&1
timeout /t 2 >nul
sc start Serial >nul 2>&1
pnputil /scan-devices >nul 2>&1

echo.
echo Pembersihan selesai. Silakan cabut dan pasang kembali perangkat Arduino.
echo.
pause
goto MENU

:CHECK_CONNECTION
cls
echo ====================================
echo   Periksa Status Koneksi Arduino
echo ====================================
echo.

:: Mencoba mendeteksi Arduino yang terhubung
echo Mencari perangkat Arduino yang terhubung...
echo.
wmic path Win32_SerialPort get DeviceID, Description | findstr /i "Arduino"
if %errorlevel% EQU 0 (
    echo.
    echo Arduino terdeteksi! Lihat detail di atas.
) else (
    echo.
    echo Arduino tidak terdeteksi.
    echo Silakan periksa apakah:
    echo  - Arduino terhubung ke komputer melalui kabel USB
    echo  - Driver Arduino terinstal dengan benar
    echo  - Kabel USB berfungsi dengan baik
)

echo.
echo Memeriksa penggunaan port terakhir...
if exist "arduino_port.txt" (
    set /p lastport=<arduino_port.txt
    echo Port terakhir yang digunakan: %lastport%
    
    :: Periksa apakah port tersebut tersedia
    wmic path Win32_SerialPort get DeviceID | findstr /i "%lastport%"
    if %errorlevel% EQU 0 (
        echo Port %lastport% tersedia di sistem.
    ) else (
        echo Port %lastport% tidak tersedia di sistem.
    )
) else (
    echo File arduino_port.txt tidak ditemukan.
)
echo.
pause
goto MENU

:CLEAN_LAST_PORT
cls
echo ====================================
echo   Bersihkan File Port Terakhir
echo ====================================
echo.

echo Memeriksa file arduino_port.txt...
if exist "arduino_port.txt" (
    echo File arduino_port.txt ditemukan.
    set /p konfirmasi="Apakah Anda ingin menghapusnya? (Y/N): "
    if /i "%konfirmasi%"=="Y" (
        del /f arduino_port.txt
        echo File arduino_port.txt berhasil dihapus.
        echo Aplikasi akan mencari ulang port Arduino saat dijalankan.
    ) else (
        echo Pembatalan penghapusan file.
    )
) else (
    echo File arduino_port.txt tidak ditemukan.
)
echo.
pause
goto MENU

:EXIT
cls
echo Terima kasih telah menggunakan Script Pemeliharaan Arduino.
echo Sampai jumpa kembali!
echo.
exit /b 0 