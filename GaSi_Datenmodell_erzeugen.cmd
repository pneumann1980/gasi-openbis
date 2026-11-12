@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" gasi_model_html.py
) else (
    python gasi_model_html.py
)
if errorlevel 1 (
    echo.
    echo Pakete bei Bedarf installieren: python -m pip install -r requirements-docs.txt
    pause
    exit /b 1
)
start "" "%~dp0docs\GaSi_Datenmodell_einfach.html"
