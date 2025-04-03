@echo off
echo =============================================
echo       STANDALONE BARCODE PRINTER
echo =============================================
echo.
echo This program will print barcode tickets
echo without requiring Arduino connection.
echo.
echo Press any key to start...
pause > nul

cd /d C:\path
python standalone_printer.py

echo.
echo Application closed.
pause 