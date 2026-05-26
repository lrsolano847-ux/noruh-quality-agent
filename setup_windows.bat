@echo off
echo ============================================================
echo  Noruh Quality Agent - Windows Setup Script
echo ============================================================
echo.

REM ── Check Python is installed ────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python was not found on this computer.
    echo.
    echo Please install Python first:
    echo   1. Go to https://www.python.org/downloads/
    echo   2. Download the latest version
    echo   3. Run the installer
    echo   4. IMPORTANT: tick "Add Python to PATH" during install
    echo   5. Close this window, then double-click setup_windows.bat again
    echo.
    pause
    exit /b 1
)

echo Python found. Continuing...
echo.

REM ── Create virtual environment ───────────────────────────────
echo Step 1/5: Creating Python virtual environment...
python -m venv venv
if errorlevel 1 (
    echo ERROR: Could not create virtual environment.
    pause
    exit /b 1
)
echo Done.
echo.

REM ── Activate virtual environment ─────────────────────────────
call venv\Scripts\activate.bat
echo Step 2/5: Installing packages (this may take several minutes)...
echo           If a package times out, just run this script again.
echo.

pip install --timeout 120 numpy pandas
pip install --timeout 120 duckdb sqlglot
pip install --timeout 120 langchain-ollama langchain-core langgraph
pip install --timeout 120 streamlit
pip install --timeout 120 sentence-transformers
pip install --timeout 120 chromadb
pip install --timeout 120 scikit-learn joblib

echo.
echo Step 3/6: Packages installed.
echo.

REM ── Create data directory ────────────────────────────────────
echo Step 4/6: Creating data folder...
if not exist "data" mkdir data
echo Done.
echo.

REM ── Generate database ────────────────────────────────────────
echo Step 5/6: Generating manufacturing database...
echo           This takes about 80 seconds. Please wait...
echo.
python pipeline.py
if errorlevel 1 (
    echo ERROR: Database generation failed. See message above.
    pause
    exit /b 1
)

REM ── Train ML quality classifier ──────────────────────────────
echo.
echo Step 6/6: Training quality classifier (Random Forest)...
echo           This takes 2-4 minutes. Please wait...
echo.
python ml\train.py
if errorlevel 1 (
    echo ERROR: ML training failed. See message above.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Setup complete!
echo.
echo  NEXT STEPS:
echo  1. Install Ollama from: https://ollama.com/download
echo     (download the Windows installer and run it)
echo.
echo  2. Open Command Prompt and run these two commands:
echo     ollama pull qwen3-coder:7b
echo     ollama pull deepseek-r1:8b
echo     (these download ~8 GB total - will take a while)
echo.
echo  3. Once the models are downloaded, double-click start_windows.bat
echo     to launch the app, then open your browser to:
echo     http://localhost:8501
echo ============================================================
echo.
pause
