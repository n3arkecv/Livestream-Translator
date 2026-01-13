@echo off
setlocal EnableExtensions
title Livestream Translator Launcher

echo ======================================================
echo       Livestream Translator Launcher
echo ======================================================

:: 0. First Launch Check & Welcome
if not exist .first_launch_done (
    echo [WELCOME] It seems like this is your first time launching the app.
    echo [INFO] We will set up the environment and check for requirements.
    echo [TIP] You can skip the requirement check in future launches 
    echo       by toggling the option in the GUI Settings.
    echo.
    echo Press any key to continue...
    pause >nul
    type nul > .first_launch_done
)

:: 1. Check Python
echo [INFO] Checking Python...
python --version >nul 2>&1
if %errorlevel% neq 0 goto :nopython

:: 2. Handle Venv
set VENV_DIR=.venv
if not exist %VENV_DIR% (
    echo [INFO] Creating virtual environment...
    python -m venv %VENV_DIR%
)
if %errorlevel% neq 0 goto :venverror

:: 3. Activate
echo [INFO] Activating virtual environment...
call %VENV_DIR%\Scripts\activate
if %errorlevel% neq 0 goto :activateerror

:: 4. Install requirements (unless skipped)
set SKIP_CHECK=False
if exist User_config.txt (
    for /f "tokens=1,2 delims==" %%a in (User_config.txt) do (
        if "%%a"=="SKIP_REQUIREMENTS_CHECK" set SKIP_CHECK=%%b
    )
)

if /i "%SKIP_CHECK%"=="True" (
    echo [INFO] Skipping requirements check as per User_config.txt.
) else (
    if exist requirements.txt (
        echo [INFO] Installing/Checking requirements...
        pip install -r requirements.txt
        if %errorlevel% neq 0 goto :piperror
    )
)

:: 5. Launch
echo [INFO] Launching app...
python main_gui.py
if %errorlevel% neq 0 pause

goto :end

:nopython
echo [ERROR] Python not found.
pause
exit /b 1

:venverror
echo [ERROR] Failed to create venv.
pause
exit /b 1

:activateerror
echo [ERROR] Failed to activate venv.
pause
exit /b 1

:piperror
echo [ERROR] Failed to install requirements.
pause
exit /b 1

:end
call deactivate
echo [INFO] Finished.
pause
