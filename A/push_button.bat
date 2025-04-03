@echo off
echo =============================================
echo         PUSH BUTTON BARCODE PRINTER
echo =============================================
echo.
echo This program will print a ticket when
echo you press the SPACEBAR key.
echo.
echo Press any key to start...
pause > nul

cd /d C:\path
python button_printer.py

echo.
echo Application closed.
pause 