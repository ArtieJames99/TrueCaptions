@echo off
setlocal EnableDelayedExpansion

REM ============================================
REM Resolve project root (directory of this .bat)
REM ============================================
set "PROJECT_ROOT=%~dp0"
cd /d "%PROJECT_ROOT%"

echo.
echo ============================================
echo Building TrueCaptions
echo Project root: %PROJECT_ROOT%
echo ============================================
echo.

REM ============================================
REM Verify virtual environment exists
REM ============================================
if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found.
    echo Expected: %PROJECT_ROOT%.venv\Scripts\python.exe
    pause
    exit /b 1
)

set "PYTHON=.venv\Scripts\python.exe"

REM ============================================
REM Clean previous builds
REM ============================================
echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist __pycache__ rmdir /s /q __pycache__

REM ============================================
REM Verify required resources
REM ============================================
if not exist "ffmpeg\ffmpeg.exe" (
    echo ERROR: ffmpeg.exe not found at:
    echo %PROJECT_ROOT%ffmpeg\ffmpeg.exe
    pause
    exit /b 1
)

if not exist "sword_of_laban.ico" (
    echo ERROR: Icon file not found:
    echo %PROJECT_ROOT%sword_of_laban.ico
    pause
    exit /b 1
)

REM ============================================
REM Test imports first
REM ============================================
echo.
echo Testing imports...
"%PYTHON%" test_imports.py
if errorlevel 1 (
    echo.
    echo ERROR: Import test failed.
    pause
    exit /b 1
)

REM ============================================
REM Run PyInstaller (via python -m for portability)
REM ============================================
echo.
echo Running PyInstaller...
"%PYTHON%" -m PyInstaller TrueCaptions.py ^
    --noconsole ^
    --onedir ^
    --name TrueCaptions ^
    --icon "%PROJECT_ROOT%sword_of_laban.ico" ^
    --add-binary "%PROJECT_ROOT%ffmpeg\ffmpeg.exe;ffmpeg" ^
    --collect-all AutoCaptions ^
    --hidden-import whisper ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    --exclude-module pandas ^
    --exclude-module tensorboard ^
    --exclude-module sklearn

REM ============================================
REM Result
REM ============================================
if errorlevel 1 (
    echo.
    echo ❌ BUILD FAILED
    pause
    exit /b 1
)

echo.
echo ✅ BUILD SUCCESSFUL
echo Output:
echo %PROJECT_ROOT%dist\TrueCaptions\TrueCaptions.exe
echo.
pause
