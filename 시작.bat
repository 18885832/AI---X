@echo off
title AI Meeting Server

taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

python web_app.py
pause
