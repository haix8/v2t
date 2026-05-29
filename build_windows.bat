@echo off
echo ========================================
echo   V2T - Audio/Video to Text - Windows Build Tool
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Create virtual environment if it does not exist
if not exist "venv" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install dependencies
echo [3/4] Installing dependencies (may take a while on first run)...
pip install -r requirements.txt -q
pip install pyinstaller -q

REM Run build
echo [4/4] Building package...
echo.
pyinstaller build.spec --clean --noconfirm

echo.
if exist "dist\V2T" (
    echo ========================================
    echo   Build successful!
    echo   Output directory: dist\V2T\
    echo   Run: dist\V2T\V2T.exe
    echo ========================================
) else (
    echo [ERROR] Build failed. Please check the error messages above.
)

echo.
pause
