@echo off
rem Dobbeltklikk for å bygge data\bruk-anthropic.js på nytt.
cd /d "%~dp0"
python build_data.py
echo.
pause
