# -*- coding: utf-8 -*-
"""
Whisper STT 변환 모듈
음성 파일을 텍스트로 변환
"""
import whisper
import os
import sys
import codecs

# Windows 에서 콘솔 출력 인코딩 설정 (간단 버전)
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

from config import FFMPEG_DIR, TRANSCRIPTS_DIR, AUDIO_DIR

def convert_audio_to_text(audio_path, model_name="base", language="ko"):
    """
    음성 파일을 Whisper 모델로 변환하여 텍스트 반환

    Args:
        audio_path: 음성 파일 경로
        model_name: Whisper 모델 이름
        language: 언어 코드

    Returns:
        변환된 텍스트
    """
    print(f"[STT] 음성 파일: {os.path.basename(audio_path)}")
    print(f"[STT] 모델: {model_name}")

    # FFmpeg 경로 설정
    if os.path.exists(FFMPEG_DIR):
        os.environ["PATH"] = FFMPEG_DIR + os.pathsep + os.environ.get("PATH", "")

    # 모델 로드
    print("[STT] 모델 로딩 중...")
    model = whisper.load_model(model_name)

    # STT 변환
    print("[STT] 음성 변환 중...")
    result = model.transcribe(audio_path, language=language, verbose=False)

    text = result["text"]
    print(f"[STT] 변환 완료: {len(text)} 자")

    return text


def save_transcript(audio_filename, text):
    """
    전사본 텍스트 저장

    Args:
        audio_filename: 원본 음성 파일명
        text: 변환된 텍스트

    Returns:
        저장된 파일 경로
    """
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)

    # 출력 파일명 생성
    base_name = os.path.splitext(audio_filename)[0]
    output_path = os.path.join(TRANSCRIPTS_DIR, f"{base_name}_transcript.txt")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text)

    print(f"[STT] 저장 완료: {output_path}")
    return output_path


def get_audio_files(directory=None):
    """
    음성 파일 목록 반환

    Returns:
        음성 파일 경로 목록
    """
    if directory is None:
        directory = AUDIO_DIR

    audio_extensions = ['.m4a', '.wav', '.mp3', '.flac']
    audio_files = []

    if os.path.exists(directory):
        for filename in os.listdir(directory):
            ext = os.path.splitext(filename)[1].lower()
            if ext in audio_extensions:
                audio_files.append(os.path.join(directory, filename))

    return sorted(audio_files)
