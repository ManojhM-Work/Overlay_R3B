@echo off
title Expleo PT UPI ACMT Simulator - Dependency Installer
echo ===================================================
echo   INSTALLING EXPLED PT UPI ACMT SIMULATOR PACKAGES
echo ===================================================
echo.
echo Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your system PATH!
    echo Please install Python 3.8+ and try again.
    echo.
    pause
    exit /b 1
)

echo [INFO] Python found! Installing required libraries...
echo.
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Dependency installation failed! Please verify internet connection or permissions.
) else (
    echo.
    echo [SUCCESS] All dependencies (FastAPI, Uvicorn, HTTPX) installed successfully!
    echo you are now ready to launch the simulator using Expleo_ACMT_Simulator_UI.bat.
)
echo.
pause
