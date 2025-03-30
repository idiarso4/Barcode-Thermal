@echo off
echo Setting up Parking System Autostart...
echo.

:: Create Startup folder shortcut
echo Creating autostart shortcut...
powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut($WshShell.SpecialFolders('Startup') + '\Sistem Parkir RSI BNA.lnk'); $Shortcut.TargetPath = '%~dp0run_parking.bat'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.WindowStyle = 7; $Shortcut.Description = 'Sistem Parkir RSI Banjarnegara'; $Shortcut.IconLocation = '%SystemRoot%\System32\imageres.dll,99'; $Shortcut.Save()"

:: Create Desktop shortcut
echo Creating desktop shortcut...
powershell "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut($WshShell.SpecialFolders('Desktop') + '\Sistem Parkir RSI BNA.lnk'); $Shortcut.TargetPath = '%~dp0run_parking.bat'; $Shortcut.WorkingDirectory = '%~dp0'; $Shortcut.WindowStyle = 1; $Shortcut.Description = 'Sistem Parkir RSI Banjarnegara'; $Shortcut.IconLocation = '%SystemRoot%\System32\imageres.dll,99'; $Shortcut.Save()"

echo.
echo Setup completed!
echo.
echo Shortcut telah dibuat di:
echo 1. Desktop
echo 2. Startup Windows (autostart)
echo.
echo Program akan start otomatis saat Windows dinyalakan
echo.
pause 