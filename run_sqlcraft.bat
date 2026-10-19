@echo off
title SQLCraft Studio - Local Database Workbench
color 0b

echo ========================================================
echo               SQLCRAFT - LOCAL ENGINE
echo   Natural Language to SQL Generator & Explainer
echo       Pranveer Singh Institute of Technology
echo ========================================================
echo.
echo [*] Checking Python environment...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in PATH! Please install Python.
    pause
    exit /b
)

echo [*] Launching local server at http://127.0.0.1:5000...
start "" http://127.0.0.1:5000
python app.py

pause
