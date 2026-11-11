# -*- coding: utf-8 -*-
"""
vLLM API 연결 테스트 스크립트
"""
import requests
import json
from config import AI_API_BASE_URL, AI_API_KEY, AI_API_ENDPOINT, AI_API_MODEL

def test_api_connection():
    """API 연결 테스트"""
    print("=" * 60)
    print("vLLM API 연결 테스트")
    print("=" * 60)

    # 테스트 정보 출력
    print(f"\n[설정 정보]")
    print(f"  Base URL: {AI_API_BASE_URL}")
    print(f"  Endpoint: {AI_API_ENDPOINT}")
    print(f"  Model: {AI_API_MODEL}")
    print(f"  API Key: {AI_API_KEY[:10]}...{AI_API_KEY[-5:]}")

    # 실제 URL 구성
    actual_url = f"{AI_API_BASE_URL}{AI_API_ENDPOINT}"
    print(f"\n[호출 URL]")
    print(f"  {actual_url}")

    # 테스트 메시지
    test_messages = [
        {
            "role": "system",
            "content": "당신은 친절한 AI 어시스턴트입니다."
        },
        {
            "role": "user",
            "content": "안녕하세요? 간단한 인사말만 해주세요."
        }
    ]

    # 요청 헤더
    headers = {
        "X-API-Key": AI_API_KEY,
        "Content-Type": "application/json"
    }

    # 요청 바디
    body = {
        "model": AI_API_MODEL,
        "messages": test_messages,
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 100
    }

    print(f"\n[요청]")
    print(json.dumps(body, ensure_ascii=False, indent=2))

    print(f"\n API 호출 중...")

    try:
        response = requests.post(actual_url, headers=headers, json=body, timeout=30)

        print(f"\n[응답 상태]")
        print(f"  Status Code: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"\n[응답 데이터]")
            print(json.dumps(result, ensure_ascii=False, indent=2))

            # 응답 내용 추출
            if "choices" in result and len(result["choices"]) > 0:
                content = result["choices"][0].get("message", {}).get("content", "")
                print(f"\n[AI 응답]")
                print("-" * 40)
                print(content)
                print("-" * 40)

                # 토큰 사용량
                if "usage" in result:
                    usage = result["usage"]
                    print(f"\n[토큰 사용량]")
                    print(f"  Prompt Tokens: {usage.get('prompt_tokens', 0)}")
                    print(f"  Completion Tokens: {usage.get('completion_tokens', 0)}")
                    print(f"  Total Tokens: {usage.get('total_tokens', 0)}")

                print("\n[성공] API 연결이 정상적으로 작동합니다!")
                return True
            else:
                print("\n[오류] 응답 형식이 예상과 다릅니다.")
                return False
        else:
            print(f"\n[오류 응답]")
            print(response.text)
            return False

    except requests.exceptions.ConnectionError as e:
        print(f"\n[연결 오류]")
        print(f"  API 서버에 연결할 수 없습니다.")
        print(f"  세부 사항: {e}")
        return False
    except requests.exceptions.Timeout as e:
        print(f"\n[시간 초과 오류]")
        print(f"  API 응답 시간이 초과되었습니다.")
        return False
    except Exception as e:
        print(f"\n[예외 발생]")
        print(f"  {type(e).__name__}: {e}")
        return False


def test_meeting_analysis():
    """회의록 분석 테스트"""
    print("\n" + "=" * 60)
    print("회의록 분석 테스트")
    print("=" * 60)

    from ai_analyzer import call_hyundai_steel_ai

    # 테스트 회의록 텍스트
    test_stt = """
    회의 명은 주문진행관리 개선 회의이고, 참석자는 김팀장 이책임 박이사 입니다.
    목적은 현재 주문 처리 시스템을 개선하기 위한 논의입니다.
    요청사항으로는 주문 번호별 1 차 이상 낙기 안내가 필요합니다.
    2 차 이상 낙기 수정도 함께 진행해야 합니다.
    입고 완료율을 100% 로 맞추는 것이 목표입니다.
    향후 입고 실적과 신규 개발을 함께 반영할 예정입니다.
    알람 메일 개발도 진행하겠습니다.
    """

    print(f"\n[테스트 입력]")
    print(test_stt[:200] + "...")

    print("\n[AI 분석 중...]")
    result = call_hyundai_steel_ai(test_stt)

    print("\n[분석 결과]")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    return result


if __name__ == "__main__":
    print("\n")

    # 1. 간단한 연결 테스트
    success = test_api_connection()

    if success:
        # 2. 회의록 분석 테스트
        test_meeting_analysis()
    else:
        print("\n[경고] API 연결 테스트 실패 - 규칙 기반 추출이 사용됩니다.")

    print("\n" + "=" * 60)
    print("테스트 완료")
    print("=" * 60)
