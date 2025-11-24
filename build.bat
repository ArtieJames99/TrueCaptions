REM Test build to check for import issues
call .venv\Scripts\pyinstaller.exe TrueCaptions.py ^
    --noconsole ^
    --onedir ^
    --add-binary "ffmpeg/ffmpeg.exe;ffmpeg" ^
    --icon sword_of_laban.ico ^
    --collect-all AutoCaptions ^
    --hidden-import=whisper

    then do this in build.bat
    REM filepath: C:\Development\TrueEdit\TrueCaptions\build.bat
@echo off
echo Building TrueCaptions with PyInstaller...

REM Clean previous builds
echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

echo Testing imports first...
call .venv\Scripts\python.exe test_imports.py
if %errorlevel% neq 0 (
    echo Import test failed! Please fix import issues before building.
    pause
    exit /b 1
)

echo.
echo Running PyInstaller with improved configuration...
call .venv\Scripts\pyinstaller.exe TrueCaptions.py ^
    --noconsole ^
    --onedir ^
    --add-binary "ffmpeg/ffmpeg.exe;ffmpeg" ^
    --icon sword_of_laban.ico ^
    --collect-all AutoCaptions ^
    --collect-all WhisperBase ^
    --collect-all WhisperConfiguration ^
    --collect-all WhisperSettings ^
    --collect-all WhisperTranscriber ^
    --collect-all WhisperUtils ^
    --collect-all WhisperWorker ^
    --collect-all WhisperWorkerManager ^
    --collect-all WhisperWorkerPool ^
    --collect-all WhisperWorkerResult ^
    --collect-all WhisperWorkerTask ^
    --collect-all WhisperWorkerType ^
    --collect-all WhisperWorkerStatus ^
    --collect-all WhisperWorkerPriority ^
    --collect-all WhisperWorkerQueue ^
    --collect-all WhisperWorkerPoolConfig ^
    --collect-all WhisperWorkerPoolManager ^
    --collect-all WhisperWorkerPoolResult ^
    --collect-all WhisperWorkerPoolTask ^
    --collect-all WhisperWorkerPoolType ^
    --collect-all WhisperWorkerPoolStatus ^
    --collect-all WhisperWorkerPoolPriority ^
    --collect-all WhisperWorkerPoolQueue ^
    --collect-all WhisperWorkerPoolUtils ^
    --collect-all WhisperWorkerPoolBase ^
    --collect-all WhisperWorkerPoolConfiguration ^
    --collect-all WhisperWorkerPoolSettings ^
    --collect-all WhisperWorkerPoolWhisper ^
    --collect-all WhisperWorkerPoolWorker ^
    --collect-all WhisperWorkerPoolWorkerManager ^
    --collect-all WhisperWorkerPoolWorkerPool ^
    --collect-all WhisperWorkerPoolWorkerResult ^
    --collect-all WhisperWorkerPoolWorkerTask ^
    --collect-all WhisperWorkerPoolWorkerType ^
    --collect-all WhisperWorkerPoolWorkerStatus ^
    --collect-all WhisperWorkerPoolWorkerPriority ^
    --collect-all WhisperWorkerPoolWorkerQueue ^
    --collect-all WhisperWorkerPoolWorkerUtils ^
    --collect-all WhisperWorkerPoolWorkerBase ^
    --collect-all WhisperWorkerPoolWorkerConfiguration ^
    --collect-all WhisperWorkerPoolWorkerSettings ^
    --collect-all WhisperWorkerPoolWorkerWhisper ^
    --hidden-import=whisper ^
    --exclude-module matplotlib ^
    --exclude-module scipy ^
    --exclude-module pandas ^
    --exclude-module tensorboard ^
    --exclude-module sklearn

if %errorlevel% equ 0 (
    echo.
    echo Build successful!
    echo Your executable is in: dist\TrueCaptions\TrueCaptions.exe
    echo.
    echo To test the executable, run it from the command line to see any error messages:
    echo cd dist\TrueCaptions
    echo TrueCaptions.exe
) else (
    echo Build failed with errors!
)

pause