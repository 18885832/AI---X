@echo off
title Stop Server

taskkill /F /IM python.exe >nul 2>&1
if %errorlevel% equ 0 (
    echo Server stopped.
) else (
    echo No Python server running.
)

pause
