@echo off
echo ============================================
echo   BARCODE TICKET PRINTER SYSTEM
echo ============================================
echo.
echo This program will:
echo 1. Connect to Arduino on COM7
echo 2. Monitor for button presses
echo 3. Generate and print barcodes automatically
echo.
echo Press Ctrl+C to exit when done
echo.

cd /d C:\path
python barcode_printer.py

echo.
echo Application closed.
pause 