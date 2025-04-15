@echo off
echo ===================================
echo    NONAKTIFKAN FIREWALL
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

echo PERINGATAN: Menonaktifkan firewall bisa menyebabkan risiko keamanan.
echo Gunakan hanya saat troubleshooting dan aktifkan kembali setelah selesai.
echo.
echo 1. Menonaktifkan untuk Profil Domain
echo 2. Menonaktifkan untuk Profil Private
echo 3. Menonaktifkan untuk Profil Public
echo 4. Menonaktifkan untuk SEMUA profil (Tidak direkomendasikan)
echo 5. Aktifkan kembali SEMUA profil
echo.
set /p choice=Pilihan Anda (1-5): 

if "%choice%"=="1" (
    netsh advfirewall set domainprofile state off
    echo Firewall untuk Profil Domain telah dinonaktifkan.
) else if "%choice%"=="2" (
    netsh advfirewall set privateprofile state off
    echo Firewall untuk Profil Private telah dinonaktifkan.
) else if "%choice%"=="3" (
    netsh advfirewall set publicprofile state off
    echo Firewall untuk Profil Public telah dinonaktifkan.
) else if "%choice%"=="4" (
    netsh advfirewall set allprofiles state off
    echo PERINGATAN: Firewall untuk SEMUA profil telah dinonaktifkan!
    echo Aktifkan kembali setelah troubleshooting selesai.
) else if "%choice%"=="5" (
    netsh advfirewall set allprofiles state on
    echo Firewall untuk SEMUA profil telah diaktifkan kembali.
) else (
    echo Input tidak valid. Silakan jalankan kembali dan pilih 1-5.
)

echo.
pause
