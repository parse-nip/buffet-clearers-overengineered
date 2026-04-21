@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python -m pip install -r requirements.txt || exit /b 1
python run_graphs.py || exit /b 1
endlocal
