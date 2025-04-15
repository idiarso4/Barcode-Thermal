@echo off
echo Setting up fresh Python environment...

REM Remove existing environments if they exist
if exist "myenv" rmdir /s /q "myenv"
if exist "venv" rmdir /s /q "venv"
if exist "venv311" rmdir /s /q "venv311"

REM Create fresh environment
python -m venv myenv

REM Activate environment
call myenv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip

REM Install dependencies from fixed requirements
pip install -r requirements_fixed.txt

echo Environment setup complete!
echo.
echo To activate the environment, run:
echo call myenv\Scripts\activate.bat
pause 