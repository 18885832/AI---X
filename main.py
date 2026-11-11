# -*- coding: utf-8 -*-
"""
AI 회의록 생성 시스템 - 메인 스크립트
음성 파일 → STT → AI 분석 → PPT 생성
"""
import os
import sys
import glob
from datetime import datetime

# 인코딩 설정 (Windows)
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from config import AUDIO_DIR
from stt_converter import convert_audio_to_text, get_audio_files
from ai_analyzer import call_hyundai_steel_ai
from ppt_generator import create_meeting_ppt

def process_audio_file(audio_path):
    """
    단일 음성 파일을 처리하여 PPT 생성

    Args:
        audio_path: 음성 파일 경로
    """
    print("\n" + "=" * 60)
    print("AI 회의록 생성 시스템")
    print("=" * 60)

    filename = os.path.basename(audio_path)
    print(f"\n[1/3] 음성 파일: {filename}")

    # 1. STT 변환
    print("\n--- STT 변환 ---")
    stt_text = convert_audio_to_text(audio_path, model_name="base")

    if not stt_text or len(stt_text) < 10:
        print("[ERROR] STT 변환 실패 - 텍스트가 너무 짧습니다")
        return None

    # 2. AI 분석
    print("\n--- AI 분석 ---")
    meeting_data = call_hyundai_steel_ai(stt_text)

    if not meeting_data:
        print("[ERROR] AI 분석 실패")
        return None

    print(f"회의 제목: {meeting_data.get('meetingTitle', 'N/A')}")
    print(f"참석자: {len(meeting_data.get('participants', []))} 명")
    print(f"논의사항: {len(meeting_data.get('discussions', []))} 개")
    print(f"결정사항: {len(meeting_data.get('decisions', []))} 개")
    print(f"액션 아이템: {len(meeting_data.get('actionItems', []))} 개")

    # 3. PPT 생성
    print("\n--- PPT 생성 ---")
    base_name = os.path.splitext(filename)[0]
    output_filename = f"{base_name}_회의록.pptx"

    output_path = create_meeting_ppt(meeting_data, output_filename)

    print("\n" + "=" * 60)
    print("완료!")
    print(f"생성된 파일: {output_path}")
    print("=" * 60)

    return output_path


def main():
    """메인 실행 함수"""
    print("\n=== AI 회의록 생성 시스템 ===\n")

    # 음성 파일 목록
    audio_files = get_audio_files()

    if not audio_files:
        print(f"[WARN] '{AUDIO_DIR}' 폴더에 음성 파일이 없습니다.")
        print("음성 파일 (m4a, wav, mp3) 을 추가해주세요.")
        return

    print(f"찾은 음성 파일: {len(audio_files)} 개\n")

    for audio_path in audio_files:
        filename = os.path.basename(audio_path)
        print(f"처리: {filename}")

        try:
            process_audio_file(audio_path)
        except Exception as e:
            print(f"[ERROR] {filename} 처리 실패: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "-" * 60 + "\n")

    print("모든 파일 처리 완료!")


if __name__ == "__main__":
    main()
