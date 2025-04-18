@echo off
echo ====================================
echo   Setup Firewall untuk Aplikasi Parkir
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

echo Membuat pengecualian Firewall untuk aplikasi parkir...
echo.

:: Tambahkan aturan untuk Python
echo Menambahkan pengecualian untuk Python dan semua program Python...
netsh advfirewall firewall add rule name="Python - Parking Application" dir=in action=allow program="%LOCALAPPDATA%\Programs\Python\Python311\python.exe" enable=yes profile=any description="Allow Python for Parking Application"
netsh advfirewall firewall add rule name="Python - Parking Application OUT" dir=out action=allow program="%LOCALAPPDATA%\Programs\Python\Python311\python.exe" enable=yes profile=any description="Allow Python for Parking Application (outbound)"

:: Tambahkan aturan untuk port serial (COM) - lebih spesifik
echo Menambahkan pengecualian untuk port Serial COM...
netsh advfirewall firewall add rule name="Serial COM Ports TCP" dir=in action=allow protocol=TCP localport=0-9 enable=yes profile=any description="Allow serial COM port access (TCP)"
netsh advfirewall firewall add rule name="Serial COM Ports USB" dir=in action=allow program="%SystemRoot%\System32\drivers\usbser.sys" enable=yes profile=any description="Allow USB Serial drivers"
netsh advfirewall firewall add rule name="Serial COM Ports Serial" dir=in action=allow program="%SystemRoot%\System32\drivers\serial.sys" enable=yes profile=any description="Allow Serial Port drivers"
reg add "HKLM\SYSTEM\CurrentControlSet\Services\SharedAccess\Parameters\FirewallPolicy\StandardProfile\GloballyOpenPorts\List" /v "COM1:9600:TCP" /t REG_SZ /d "COM1 9600 (TCP)" /f

:: Tambahkan aturan untuk PostgreSQL
echo Menambahkan pengecualian untuk koneksi database PostgreSQL...
netsh advfirewall firewall add rule name="PostgreSQL Database IN" dir=in action=allow protocol=TCP localport=5432 enable=yes profile=any description="Allow PostgreSQL database connections"
netsh advfirewall firewall add rule name="PostgreSQL Database OUT" dir=out action=allow protocol=TCP remoteport=5432 enable=yes profile=any description="Allow PostgreSQL database connections (outbound)"

:: Tambahkan aturan untuk program printer
echo Menambahkan pengecualian untuk akses printer...
netsh advfirewall firewall add rule name="Printer Spooler Service" dir=in action=allow program="%SystemRoot%\System32\spoolsv.exe" enable=yes profile=any description="Allow Printer Spooler Service"
netsh advfirewall firewall add rule name="Printer Spooler Service OUT" dir=out action=allow program="%SystemRoot%\System32\spoolsv.exe" enable=yes profile=any description="Allow Printer Spooler Service (outbound)"
netsh advfirewall firewall add rule name="Print Driver Host" dir=in action=allow program="%SystemRoot%\System32\printhost.exe" enable=yes profile=any description="Allow Print Driver Host"
netsh advfirewall firewall add rule name="TCPMon Printer Port (LPR)" dir=in action=allow protocol=TCP localport=515 enable=yes profile=any description="Allow LPR Printer Port Monitor"
netsh advfirewall firewall add rule name="TCPMon Printer Port (RAW)" dir=in action=allow protocol=TCP localport=9100 enable=yes profile=any description="Allow RAW Printer Port Monitor"

:: Tambahkan aturan untuk kamera IP
echo Menambahkan pengecualian untuk koneksi kamera IP...
netsh advfirewall firewall add rule name="RTSP Camera Stream" dir=in action=allow protocol=TCP localport=554 enable=yes profile=any description="Allow RTSP streaming (cameras)"
netsh advfirewall firewall add rule name="RTSP Camera Stream OUT" dir=out action=allow protocol=TCP remoteport=554 enable=yes profile=any description="Allow outbound RTSP connections"
netsh advfirewall firewall add rule name="Camera UDP" dir=in action=allow protocol=UDP localport=1025-65535 enable=yes profile=any description="Allow camera UDP communication"

:: Aktifkan layanan spooler dan COM
echo Mengaktifkan layanan Windows yang diperlukan...
sc config Spooler start= auto
sc start Spooler
reg add "HKLM\SYSTEM\CurrentControlSet\Services\Serial" /v Start /t REG_DWORD /d 2 /f
sc start Serial

echo.
echo Pengecualian Firewall telah dibuat.
echo Mohon restart komputer untuk menerapkan semua perubahan.
echo.
pause 