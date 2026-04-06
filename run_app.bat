@echo off
echo ==========================================
echo   MedFuse V2 - Auto Launcher
echo ==========================================

cd backend

echo.
echo [1/2] Installing new dependencies (Database, Auth)...
pip install -r requirements.txt

echo.
echo [2/2] Starting Flask Server...
echo.
echo Open your browser to: http://127.0.0.1:5000
echo.
python app.py

pause
