@echo off
echo ====================================
echo   Pemeliharaan Database PostgreSQL
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

:: Default PostgreSQL settings
set PGBIN=C:\Program Files\PostgreSQL\15\bin
set PGDATABASE=postgres
set PGUSER=postgres
set PGPORT=5432

:: Cek jika ada config file
if exist "db_config.txt" (
    echo Membaca konfigurasi dari file db_config.txt...
    for /f "tokens=1,* delims==" %%a in (db_config.txt) do (
        if "%%a"=="PGBIN" set PGBIN=%%b
        if "%%a"=="PGDATABASE" set PGDATABASE=%%b
        if "%%a"=="PGUSER" set PGUSER=%%b
        if "%%a"=="PGPORT" set PGPORT=%%b
    )
)

:MENU
cls
echo ====================================
echo   MENU PEMELIHARAAN DATABASE
echo ====================================
echo.
echo  Konfigurasi saat ini:
echo   - Database: %PGDATABASE%
echo   - User: %PGUSER%
echo   - Port: %PGPORT%
echo   - Path: %PGBIN%
echo.
echo  1. Test Koneksi Database
echo  2. Backup Database
echo  3. Restore Database
echo  4. Vacuum Database (Pembersihan)
echo  5. Perbaiki Layanan PostgreSQL
echo  6. Atur Konfigurasi
echo  7. Keluar
echo.
set /p pilihan="Pilih menu (1-7): "

if "%pilihan%"=="1" goto TEST_CONNECTION
if "%pilihan%"=="2" goto BACKUP_DB
if "%pilihan%"=="3" goto RESTORE_DB
if "%pilihan%"=="4" goto VACUUM_DB
if "%pilihan%"=="5" goto FIX_SERVICE
if "%pilihan%"=="6" goto SETUP_CONFIG
if "%pilihan%"=="7" goto EXIT
goto MENU

:TEST_CONNECTION
cls
echo ====================================
echo   Test Koneksi Database
echo ====================================
echo.

echo Mencoba koneksi ke database %PGDATABASE%...
echo.

set /p password="Masukkan password PostgreSQL untuk user %PGUSER%: "

set PGPASSWORD=%password%
"%PGBIN%\psql.exe" -h localhost -p %PGPORT% -U %PGUSER% -d %PGDATABASE% -c "SELECT version();"
set result=%errorlevel%
set PGPASSWORD=

if %result% EQU 0 (
    echo.
    echo Koneksi berhasil!
) else (
    echo.
    echo Koneksi gagal! Kode error: %result%
    echo Periksa kembali password dan konfigurasi database.
)
echo.
pause
goto MENU

:BACKUP_DB
cls
echo ====================================
echo   Backup Database
echo ====================================
echo.

set timestamp=%date:~6,4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%%time:~6,2%
set timestamp=%timestamp: =%
set BACKUP_FILE=backup_%PGDATABASE%_%timestamp%.backup

echo Membuat backup database %PGDATABASE% ke file %BACKUP_FILE%...
echo.

if not exist "backups" mkdir backups

set /p password="Masukkan password PostgreSQL untuk user %PGUSER%: "

set PGPASSWORD=%password%
"%PGBIN%\pg_dump.exe" -h localhost -p %PGPORT% -U %PGUSER% -F c -b -v -f "backups\%BACKUP_FILE%" %PGDATABASE%
set result=%errorlevel%
set PGPASSWORD=

if %result% EQU 0 (
    echo.
    echo Backup berhasil! File disimpan di: backups\%BACKUP_FILE%
) else (
    echo.
    echo Backup gagal! Kode error: %result%
)
echo.
pause
goto MENU

:RESTORE_DB
cls
echo ====================================
echo   Restore Database
echo ====================================
echo.

if not exist "backups" (
    echo Folder backups tidak ditemukan!
    echo Silakan lakukan backup terlebih dahulu.
    echo.
    pause
    goto MENU
)

echo File backup yang tersedia:
echo.
dir /b backups\*.backup
echo.

set /p backup_file="Masukkan nama file backup untuk direstore: "
if not exist "backups\%backup_file%" (
    echo File backup tidak ditemukan!
    echo.
    pause
    goto MENU
)

echo.
echo PERINGATAN: Restore akan menimpa isi database saat ini!
set /p konfirmasi="Anda yakin ingin melanjutkan? (Y/N): "
if /i not "%konfirmasi%"=="Y" goto MENU

set /p password="Masukkan password PostgreSQL untuk user %PGUSER%: "

echo.
echo Melakukan restore database dari file backups\%backup_file%...
echo.

set PGPASSWORD=%password%
"%PGBIN%\pg_restore.exe" -h localhost -p %PGPORT% -U %PGUSER% -d %PGDATABASE% -c -v "backups\%backup_file%"
set result=%errorlevel%
set PGPASSWORD=

echo.
if %result% EQU 0 (
    echo Restore selesai dengan sukses!
) else (
    echo Restore selesai, tapi ada beberapa error. Kode: %result%
    echo Ini normal jika struktur database berbeda dengan backup.
)
echo.
pause
goto MENU

:VACUUM_DB
cls
echo ====================================
echo   Vacuum Database (Pembersihan)
echo ====================================
echo.

echo Vacuum akan membersihkan dan mengoptimalkan database.
echo Proses ini direkomendasikan untuk dilakukan secara berkala.
echo.
set /p konfirmasi="Anda yakin ingin melanjutkan? (Y/N): "
if /i not "%konfirmasi%"=="Y" goto MENU

set /p password="Masukkan password PostgreSQL untuk user %PGUSER%: "

echo.
echo Melakukan VACUUM FULL ANALYZE pada database %PGDATABASE%...
echo Tunggu hingga proses selesai (mungkin membutuhkan waktu lama)...
echo.

set PGPASSWORD=%password%
"%PGBIN%\vacuumdb.exe" -h localhost -p %PGPORT% -U %PGUSER% -d %PGDATABASE% -f -v -z
set result=%errorlevel%
set PGPASSWORD=

echo.
if %result% EQU 0 (
    echo Vacuum berhasil diselesaikan!
) else (
    echo Vacuum gagal! Kode error: %result%
)
echo.
pause
goto MENU

:FIX_SERVICE
cls
echo ====================================
echo   Perbaiki Layanan PostgreSQL
echo ====================================
echo.

echo Memeriksa status layanan PostgreSQL...
sc query "postgresql-x64-15" | findstr "STATE"

echo.
echo Opsi perbaikan:
echo  1. Restart layanan PostgreSQL
echo  2. Perbaiki izin port 5432
echo  3. Cek penggunaan port
echo  4. Kembali
echo.
set /p fix_option="Pilih opsi (1-4): "

if "%fix_option%"=="1" (
    echo.
    echo Restarting PostgreSQL service...
    net stop "postgresql-x64-15"
    timeout /t 3 >nul
    net start "postgresql-x64-15"
    echo.
    echo Service selesai di-restart.
) else if "%fix_option%"=="2" (
    echo.
    echo Memperbaiki izin port 5432 di firewall...
    netsh advfirewall firewall delete rule name="PostgreSQL Database" >nul 2>&1
    netsh advfirewall firewall add rule name="PostgreSQL Database" dir=in action=allow protocol=TCP localport=5432 enable=yes profile=any description="Allow PostgreSQL database connections"
    echo Izin port telah diperbaiki.
) else if "%fix_option%"=="3" (
    echo.
    echo Memeriksa penggunaan port 5432...
    netstat -ano | findstr "5432"
    echo.
    echo Jika ada program lain yang menggunakan port 5432, 
    echo Anda perlu menutup program tersebut atau mengubah port PostgreSQL.
)

echo.
pause
goto MENU

:SETUP_CONFIG
cls
echo ====================================
echo   Atur Konfigurasi Database
echo ====================================
echo.

echo Konfigurasi saat ini:
echo  - Database: %PGDATABASE%
echo  - User: %PGUSER%
echo  - Port: %PGPORT%
echo  - Path: %PGBIN%
echo.

echo Masukkan nilai baru (atau kosongkan untuk tidak mengubah):
echo.

set /p new_pgbin="Path PostgreSQL bin (misalnya C:\Program Files\PostgreSQL\15\bin): "
if not "%new_pgbin%"=="" set PGBIN=%new_pgbin%

set /p new_pgdatabase="Nama Database: "
if not "%new_pgdatabase%"=="" set PGDATABASE=%new_pgdatabase%

set /p new_pguser="Username: "
if not "%new_pguser%"=="" set PGUSER=%new_pguser%

set /p new_pgport="Port (default 5432): "
if not "%new_pgport%"=="" set PGPORT=%new_pgport%

echo.
echo Menyimpan konfigurasi...
echo PGBIN=%PGBIN%> db_config.txt
echo PGDATABASE=%PGDATABASE%>> db_config.txt
echo PGUSER=%PGUSER%>> db_config.txt
echo PGPORT=%PGPORT%>> db_config.txt

echo.
echo Konfigurasi berhasil disimpan!
echo.
pause
goto MENU

:EXIT
cls
echo Terima kasih telah menggunakan Script Pemeliharaan Database.
echo Sampai jumpa kembali!
echo.
exit /b 0 