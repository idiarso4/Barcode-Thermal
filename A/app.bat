@echo off
cd /d "%~dp0"
echo Starting Barcode Printing Application...
echo.
echo Make sure:
echo 1. Arduino is connected to the computer
echo 2. Push button is connected to pin 2
echo 3. Printer is turned on and connected
echo 4. Database server is running
echo.
echo Press Ctrl+C to exit the application
echo.
python barcode.py
pause