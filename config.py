# -*- coding: utf-8 -*-
"""
설정 파일
"""
import os

# 기본 디렉토리 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "음성")
REPORTS_DIR = os.path.join(BASE_DIR, "Reports")
TRANSCRIPTS_DIR = os.path.join(BASE_DIR, "Transcripts")

# Whisper 모델 옵션
# tiny: 39MB (가장 빠름), base: 74MB (빠름), small: 244MB (정확함), medium: 769MB (가장 정확)
WHISPER_MODEL = "small"  # 정확도가 높은 small 모델 사용

# FFmpeg 경로 (시스템 FFmpeg 사용, 폴더에 ffmpeg 가 있으면 해당 폴더 사용)
FFMPEG_DIR = os.path.join(BASE_DIR, "ffmpeg", "ffmpeg-master-latest-win64-gpl", "bin")
if not os.path.exists(FFMPEG_DIR):
    FFMPEG_DIR = None  # 시스템 FFmpeg 사용

# AI API 설정 (vLLM OpenAI 호환 서버)
# 외부 시스템 발급 API Key 를 사용한 투명 프록시 연동
AI_API_BASE_URL = "https://steel-x-api.hyundai-steel.com"
AI_API_KEY = "sxgw_kRR8VHmhl7tt47h7MbM344clHY0LIL7qP9pBA8rqexQ"

# 엔드포인트 옵션
AI_API_ENDPOINT = "/llm/main/chat/completions"  # text, image, main, sub1 중 선택
AI_API_MODEL = "Qwen3.5-122B-A10B-FP16"  # 해당 엔드포인트에 맞는 모델명

# AI API 사용 여부 (True: AI 사용, False: 규칙 기반 추출 사용)
AI_API_ENABLED = True

# 사용 가능한 AI 모델 목록
AVAILABLE_MODELS = [
    {
        "name": "Qwen3.5-122B-A10B-FP16",
        "endpoint": "/llm/main/chat/completions",
        "description": "메인서버 대형 텍스트 LLM 채팅"
    },
    {
        "name": "Qwen3.5-27B-FP8",
        "endpoint": "/llm/text/chat/completions",
        "description": "텍스트 LLM 채팅"
    },
    {
        "name": "Qwen3-VL-32B-Instruct-FP8",
        "endpoint": "/llm/image/chat/completions",
        "description": "비전 (이미지 포함) LLM 채팅"
    },
    {
        "name": "Qwen3.6-35B-A3B-FP8",
        "endpoint": "/llm/sub1/chat/completions",
        "description": "서브인프라 텍스트 LLM 채팅"
    }
]

# 출력 설정
FONT_NAME = "맑은 고딕"
