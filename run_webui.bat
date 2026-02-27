@echo off
echo ============================================================
echo   Agentic GraphRAG Web UI Launcher
echo ============================================================
echo.

:menu
echo Select UI version:
echo   1. Enhanced Modern UI (Recommended)
echo   2. Simple Agentic UI
echo   3. Original UI
echo   0. Exit
echo.
set /p choice="Enter choice (1-3): "

if "%choice%"=="1" goto modern
if "%choice%"=="2" goto simple
if "%choice%"=="3" goto original
if "%choice%"=="0" goto end
goto menu

:modern
echo.
echo Launching Enhanced Modern UI...
echo URL: http://localhost:8501
echo.
streamlit run app_agentic_v2.py --server.port 8501 --server.headless true
goto end

:simple
echo.
echo Launching Simple Agentic UI...
echo URL: http://localhost:8502
echo.
streamlit run app_agentic.py --server.port 8502 --server.headless true
goto end

:original
echo.
echo Launching Original UI...
echo URL: http://localhost:8503
echo.
streamlit run app.py --server.port 8503 --server.headless true
goto end

:end
echo.
echo Exiting...
