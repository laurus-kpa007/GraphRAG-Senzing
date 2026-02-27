@echo off
echo ============================================================
echo   Kill All Streamlit Processes
echo ============================================================
echo.

echo Searching for Python/Streamlit processes...
echo.

tasklist | findstr /I "python.exe streamlit.exe"

if %ERRORLEVEL% EQU 0 (
    echo.
    set /p confirm="Kill all Python/Streamlit processes? (Y/N): "

    if /i "%confirm%"=="Y" (
        echo.
        echo Killing all Python processes...
        taskkill /F /IM python.exe 2>nul

        echo Killing all Streamlit processes...
        taskkill /F /IM streamlit.exe 2>nul

        echo.
        echo ============================================================
        echo All processes killed
        echo ============================================================
    ) else (
        echo Operation cancelled.
    )
) else (
    echo.
    echo No Python/Streamlit processes found.
)

echo.
pause
