@echo off
cd /d "%~dp0"
echo Starting User Feedback Intelligence Agent on http://localhost:8000 ...
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --log-level info
pause
