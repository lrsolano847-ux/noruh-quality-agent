@echo off
echo ============================================================
echo  Noruh Quality Agent - Starting App
echo ============================================================
echo.

REM ── Check virtual environment exists ─────────────────────────
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Setup has not been run yet.
    echo Please double-click setup_windows.bat first.
    echo.
    pause
    exit /b 1
)

REM ── Check database exists ────────────────────────────────────
if not exist "data\noruh_quality.db" (
    echo ERROR: Database not found.
    echo Please double-click setup_windows.bat first.
    echo.
    pause
    exit /b 1
)

REM ── Activate environment and launch ──────────────────────────
call venv\Scripts\activate.bat
echo Launching Noruh Quality Agent...
echo.
echo When you see "You can now view your Streamlit app in your browser"
echo open your browser and go to: http://localhost:8501
echo.
echo To stop the app, close this window.
echo.
python -m streamlit run app.py
