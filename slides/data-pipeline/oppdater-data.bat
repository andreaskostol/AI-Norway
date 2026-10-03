@echo off
rem Dobbeltklikk for å bygge data\pipeline-data.js på nytt fra microdata-output.
cd /d "%~dp0"
python build_data.py
echo.
pause
