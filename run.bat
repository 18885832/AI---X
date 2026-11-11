@echo off
chcp 65001 > nul
title AI 회의록 생성 시스템

echo ============================================
echo    AI 회의록 생성 시스템
echo ============================================
echo.

REM Python 환경 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python 이 설치되어 있지 않습니다.
    echo Python 3.11+ 를 설치해주세요.
    pause
    exit /b 1
)

REM 의존성 확인
echo [정보] 의존성 확인 중...
pip show openai-whisper > nul 2>&1
if errorlevel 1 (
    echo [정보] Whisper 가 설치되지 않았습니다. 설치합니다...
    pip install openai-whisper python-pptx requests
)

echo.
echo [정보] 음성 폴더의 파일을 처리합니다...
echo.

REM 메인 스크립트 실행
python main.py

echo.
echo ============================================
echo    처리 완료!
echo ============================================
echo.
pause
