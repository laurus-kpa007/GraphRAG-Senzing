@echo off
echo ============================================================
echo   Port Checker for Streamlit
echo ============================================================
echo.

set PORT=%1
if "%PORT%"=="" set PORT=8501

echo Checking port %PORT%...
echo.

netstat -ano | findstr :%PORT%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ============================================================
    echo Port %PORT% is OCCUPIED
    echo ============================================================
    echo.
    echo To see process details, use:
    echo   tasklist ^| findstr [PID]
    echo.
    echo To kill the process, use:
    echo   taskkill /F /PID [PID]
    echo.

    set /p kill="Do you want to kill the process? (Y/N): "
    if /i "%kill%"=="Y" (
        for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT%') do (
            echo Killing process %%a...
            taskkill /F /PID %%a
        )
    )
) else (
    echo.
    echo ============================================================
    echo Port %PORT% is FREE
    echo ============================================================
    echo.
)

pause
