# -*- coding: utf-8 -*-
"""
Qwen3.5-122B 모델 성능 테스트
"""
import requests
import json
import time
from config import AI_API_BASE_URL, AI_API_KEY, AI_API_ENDPOINT, AI_API_MODEL

def run_test(test_name, prompt, system_prompt="당신은 유용한 AI 어시스턴트입니다."):
    """단일 테스트 실행"""
    print(f"\n{'='*60}")
    print(f"테스트: {test_name}")
    print(f"{'='*60}")

    actual_url = f"{AI_API_BASE_URL}{AI_API_ENDPOINT}"

    headers = {
        "X-API-Key": AI_API_KEY,
        "Content-Type": "application/json"
    }

    body = {
        "model": AI_API_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "stream": False,
        "temperature": 0.7,
        "max_tokens": 500
    }

    start_time = time.time()

    try:
        response = requests.post(actual_url, headers=headers, json=body, timeout=120)
        elapsed_time = time.time() - start_time

        print(f"\n응답 상태: {response.status_code}")
        print(f"응답 시간: {elapsed_time:.2f}초")

        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            usage = result.get("usage", {})

            print(f"\n--- 응답 ---")
            print(content)
            print(f"\n--- 토큰 사용량 ---")
            print(f"  Prompt: {usage.get('prompt_tokens', 0)}")
            print(f"  Completion: {usage.get('completion_tokens', 0)}")
            print(f"  Total: {usage.get('total_tokens', 0)}")

            return {
                "success": True,
                "response": content,
                "elapsed_time": elapsed_time,
                "tokens": usage
            }
        else:
            print(f"오류: {response.text}")
            return {"success": False, "error": response.text}

    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"예외 발생: {e}")
        return {"success": False, "error": str(e), "elapsed_time": elapsed_time}

def main():
    print("\n" + "="*60)
    print("Qwen3.5-122B-A10B-FP16 모델 성능 테스트")
    print("="*60)
    print(f"\n모델: {AI_API_MODEL}")
    print(f"URL: {AI_API_BASE_URL}{AI_API_ENDPOINT}")

    results = []

    # 1. 기본 인사 테스트
    results.append(run_test(
        "1. 기본 인사 테스트",
        "안녕하세요? 자기소개를 해주세요."
    ))

    time.sleep(1)

    # 2. 한국어 답변 테스트
    results.append(run_test(
        "2. 한국어 자연어 처리 테스트",
        "한국어 문법을 설명해주세요. 조사와 어미의 차이를 예시와 함께 설명해주세요."
    ))

    time.sleep(1)

    # 3. 논리적 추론 테스트
    results.append(run_test(
        "3. 논리적 추론 테스트",
        "세 명 (A, B, C) 이 있습니다. A 는 B 보다 키가 크고, B 는 C 보다 키가 큽니다. \n그렇다면 A 와 C 중 누가 키가 더 큽니까? 이유와 함께 설명해주세요."
    ))

    time.sleep(1)

    # 4. 회의록 분석 테스트
    meeting_text = """
    김철수 팀장: 안녕하세요. 이번 분기 실적에 대해 논의하겠습니다.
    이영희 책임: 10 월 매출이 전년 대비 15% 증가했습니다.
    박민수 이사: 좋은 결과네요. 주요 요인이 무엇인가요?
    이영희 책임: 신규 고객 확보와 기존 고객의 재구매율 증가가 주 요인입니다.
    김철수 팀장: 다음 분기 목표는 어떻게 설정할까요?
    이영희 책임: 20% 성장을 목표로 설정하는 것이 좋겠습니다.
    """

    results.append(run_test(
        "4. 회의록 분석 테스트",
        f"다음 회의 내용을 분석해주세요.\n\n{meeting_text}\n\n요약해주세요.",
        "당신은 회의록 분석 전문가입니다."
    ))

    time.sleep(1)

    # 5. 코드 생성 테스트
    results.append(run_test(
        "5. 코드 생성 테스트",
        "파이썬으로 간단한 계산기 함수를 만들어주세요. 더하기, 빼기, 곱하기, 나누기 기능을 포함해주세요."
    ))

    # 결과 요약
    print("\n" + "="*60)
    print("테스트 결과 요약")
    print("="*60)

    success_count = sum(1 for r in results if r.get("success"))
    print(f"\n성공: {success_count}/{len(results)}")

    print("\n응답 시간:")
    for i, r in enumerate(results, 1):
        if r.get("success") and r.get("elapsed_time"):
            print(f"  테스트 {i}: {r['elapsed_time']:.2f}초")
        elif not r.get("success"):
            print(f"  테스트 {i}: 실패")

    print("\n" + "="*60)

if __name__ == "__main__":
    main()
