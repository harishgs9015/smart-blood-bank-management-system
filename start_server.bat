@echo off
cd /d "%~dp0"
echo ========================================================
echo Starting Smart Blood Donation & Blood Bank System...
echo ========================================================
echo App running at: http://127.0.0.1:5000
echo Login Portal:   http://127.0.0.1:5000/login
echo ========================================================
.\.venv\Scripts\python.exe run.py
pause
