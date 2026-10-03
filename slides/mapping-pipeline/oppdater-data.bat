@echo off
rem Dobbeltklikk for å bygge data\mapping-eloundou.js og data\mapping-mouchel.js på nytt.
cd /d "%~dp0"
python build_data.py
echo.
pause
