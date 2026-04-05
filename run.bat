@echo off
echo ===================================================
echo TRADUTOR GKC - Installing Requirements...
echo ===================================================
pip install -r requirements.txt
echo.
echo ===================================================
echo Starting Application...
echo Press F10 to Start/Stop the Translation Loop
echo Press F9 to Exit the Application entirely
echo ===================================================
python main.py
pause
