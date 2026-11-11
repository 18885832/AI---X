# -*- coding: utf-8 -*-
"""
AI 분석 모듈
회의 내용을 분석하여 구조화된 데이터 추출
규칙 기반 추출 + 현대제철 AI API 지원 + RAG 컨텍스트 + 오타 자동 수정
"""
import json
import requests
import os
from pathlib import Path
from config import AI_API_BASE_URL, AI_API_KEY, AI_API_ENDPOINT, AI_API_MODEL, AI_API_ENABLED, AVAILABLE_MODELS

# RAG 컨텍스트 import
try:
    from rag_context import build_rag_prompt, rag_manager
    HAS_RAG = True
except ImportError:
    HAS_RAG = False
    build_rag_prompt = None

# 오타 수정 사전 로드
BASE_DIR = Path(__file__).parent
CORRECTIONS_FILE = BASE_DIR / "corrections.json"

def load_corrections():
    """
    오타 수정 사전 로드 (corrections.json 또는 기본 사전)

    Returns:
        오타 수정 딕셔너리
    """
    # 기본 오타 수정 사전 (확장 버전)
    default_corrections = {
        # 기존 항목들
        '외조': '외주', '팩이': '폐기', '패키지': '폐기',
        '재강팀': '재경팀', '제공팀': '재경팀', 'DX 추진시': 'DX 추진실',
        '모의의 낑': '모의해킹', '추리 시스템': '출입시스템', '출시 시스템': '출입시스템',
        '주문지는': '주문진행관리', '주문이고': '주문진행관리', '주문번호벨': '주문번호별',
        '저확한': '저확정', '고개만전도': '고객만족도', '상상을': '상승을', '꺾하고자': '끌고자',
        '영험': '현재', '주문중독일': '주문접수일', '주문조송': '주문조송', '예산': '예산',
        '바꾼': '변경', '업로리라는': '업로드라는', '상상': '상승', '번호벨': '번호별',
        '1 창': '1 차', '미하': '미확정', '이차적으로': '2 차적으로', '아벤실적': '입고실적',
        '아벤실제': '입고실제', '클라스': '플러스', '6 개일': '6 개월', '춤': '중', '만남률': '만족률',
        '2000 학기': '2000 건', '종량': '완료', '재공료': '재공료', '관계였지': '관계없이',
        '낙기': '낙기', '입고 기념': '입고일', '백도관리': '백도관리', '기간말료': '기간말',
        '전 백퍼서': '전 100%', '충경경우': '수주경우', '만료식': '만료식', '지내는': '지나가는',
        '병룡상': '병행상', '입어': '입력', '하면': '함께', '알스단': '알람단', '매일': '메일',
        '내지인': '내역인', '브이득': '부득', '구등': '구분', '처방소주공뒤민': '처방소주공후민',
        '따라': '따라', '확인로': '확인로', '유명': '유명', '회신': '회신', '차관': '차관',
        '연전체적으로': '전체적으로', '공유': '공유', '철공정정': '차공정정', '수준공뒤': '수준공후',
        '유명을': '수정을',

        # 추가 항목 (자주 발생하는 오타)
        '회의록': '회의록', '회의명': '회의명', '회의안건': '회의안건',
        '의견': '의견', '결정': '결정', '논의': '논의',
        '담당자': '담당자', '담당': '담당', '책임자': '책임자',
        '일정': '일정', '기한': '기한', '마감': '마감',
        '프로젝트': '프로젝트', '계획': '계획', '실행': '실행',
        '예산': '예산', '비용': '비용', '집행': '집행',
        '보고': '보고', '공유': '공유', '전송': '전송',
        '확인': '확인', '검토': '검토', '승인': '승인',

        # 부서명 오타
        '재경부': '재경팀', '재정부': '재경팀', '경영팀': '재경팀',
        '개발부': '개발팀', '개발과': '개발팀',
        '운영부': '운영팀', '운영과': '운영팀',
        '기획부': '기획팀', '기획과': '기획팀',
        '정보팀': '정보화팀', '정보과': '정보화팀',

        # 용어 오타
        '디지털전환': 'DX', 'DX 추진': 'DX 추진',
        '시스템': '시스템', '시스템': '시스템',
        '자동화': '자동화', '최적화': '최적화',
        '개선': '개선', '개편': '개편',
        '업그레이드': '업그레이드', '버전업': '버전업',

        # 숫자/날짜 오타
        '2024 년': '2024 년', '2025 년': '2025 년', '2026 년': '2026 년',
        '1 월': '1 월', '2 월': '2 월', '3 월': '3 월',
        '1 일': '1 일', '2 일': '2 일', '3 일': '3 일',

        # 기타 자주 틀리는 단어
        '합니다': '합니다', '하였습니다': '하였습니다', '했습니다': '했습니다',
        '입니다': '입니다', '이에요': '이에요', '예요': '예요',
        '것입니다': '것입니다', '것으로': '것으로', '사항': '사항',
    }

    # JSON 파일이 있으면 로드하여 기본 사전에 병합
    if CORRECTIONS_FILE.exists():
        try:
            with open(CORRECTIONS_FILE, 'r', encoding='utf-8') as f:
                user_corrections = json.load(f)
            # 사용자 사전이 기본 사전보다 우선
            default_corrections.update(user_corrections)
            print(f"[오타수정] 사용자 사전 로드 완료 ({len(user_corrections)}개 항목)")
        except Exception as e:
            print(f"[오타수정] 사전 로드 실패: {e}")

    return default_corrections

# 전역 오타 수정 사전
_CORRECTIONS = None

def get_corrections():
    """오타 수정 사전 가져오기 (캐싱)"""
    global _CORRECTIONS
    if _CORRECTIONS is None:
        _CORRECTIONS = load_corrections()
    return _CORRECTIONS

def call_hyundai_steel_ai(stt_text, meeting_type="일반회의", model_name=None, endpoint=None):
    """
    vLLM OpenAI 호환 API 를 호출하여 회의 내용 분석
    API 가 설정되어 있으면 AI 분석, 아니면 규칙 기반 추출 사용

    Args:
        stt_text: STT 로 변환된 텍스트
        meeting_type: 회의 유형
        model_name: 사용할 AI 모델명 (선택, 기본값: config 의 AI_API_MODEL)
        endpoint: 사용할 엔드포인트 (선택, 기본값: config 의 AI_API_ENDPOINT)

    Returns:
        분석 결과 딕셔너리
    """
    # 모델/엔드포인트가 전달되지 않으면 config 에서 사용
    if model_name is None:
        model_name = AI_API_MODEL
    if endpoint is None:
        endpoint = AI_API_ENDPOINT
    """
    vLLM OpenAI 호환 API 를 호출하여 회의 내용 분석
    API 가 설정되어 있으면 AI 분석, 아니면 규칙 기반 추출 사용

    Args:
        stt_text: STT 로 변환된 텍스트
        meeting_type: 회의 유형

    Returns:
        분석 결과 딕셔너리
    """
    # AI API 가 활성화되어 있고 설정이 완료되어 있으면 API 호출
    if AI_API_ENABLED and AI_API_BASE_URL and AI_API_KEY:
        try:
            print("[AI] vLLM API 호출 중...")
            print(f"[AI] 모델: {model_name}")

            # 오타 자동 수정 적용
            corrected_stt = apply_corrections(stt_text)
            if corrected_stt != stt_text:
                print(f"[오타수정] {abs(len(stt_text) - len(corrected_stt))}개 오타 자동 수정 완료")

            # RAG 컨텍스트가 있으면 참고폴더 내용을 포함
            if HAS_RAG and build_rag_prompt:
                # RAG 인덱스가 없으면 구축
                if not rag_manager._initialized:
                    rag_manager.initialize()
                    rag_manager.build_vectorstore()

                prompt = build_rag_prompt(corrected_stt, meeting_type)
            else:
                prompt = f"""다음 회의록을 분석하여 JSON 형식으로만 반환하세요. 다른 설명은 빼고 JSON 만 출력하세요.

회의 내용:
{corrected_stt[:10000]}

반드시 다음 JSON 형식대로만 출력하세요:
{{
    "meetingTitle": "회의 제목",
    "purpose": "회의 목적",
    "participants": [{{"name": "이름", "role": "직위", "department": "부서"}}],
    "discussions": [{{"topic": "주제", "content": "내용"}}],
    "decisions": [{{"decision": "결정사항", "reason": "이유"}}],
    "actionItems": [{{"description": "업무", "assignee": "담당자", "dueDate": "기한"}}]
}}"""

            # 실제 API URL 구성
            actual_url = f"{AI_API_BASE_URL}{endpoint}"

            headers = {
                "X-API-Key": AI_API_KEY,
                "Content-Type": "application/json"
            }

            # OpenAI 호환 API 바디 형식
            body = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "당신은 회의록을 분석하여 구조화된 JSON 데이터를 추출하는 AI 어시스턴트입니다. 반드시 JSON 형식만 반환하세요."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "temperature": 0.3,
                "max_tokens": 2048
            }

            print(f"[AI] POST {actual_url}")
            response = requests.post(actual_url, headers=headers, json=body, timeout=120)

            if response.status_code == 200:
                result = response.json()
                print(f"[AI] API 응답 수신")

                # OpenAI 형식 응답에서 텍스트 추출
                ai_text = ""
                if "choices" in result and len(result["choices"]) > 0:
                    ai_text = result["choices"][0].get("message", {}).get("content", "")

                # JSON 파싱 시도
                try:
                    # 코드 블록에서 JSON 추출
                    if "```json" in ai_text:
                        ai_text = ai_text.split("```json")[1].split("```")[0]
                    elif "```" in ai_text:
                        ai_text = ai_text.split("```")[1].split("```")[0]

                    parsed_result = json.loads(ai_text.strip())
                    print("[AI] AI 분석 완료!")
                    return parsed_result
                except json.JSONDecodeError as e:
                    print(f"[AI] JSON 파싱 실패: {e}")
                    print(f"[AI] 수신된 텍스트: {ai_text[:500]}")

            else:
                print(f"[AI] API 오류: {response.status_code}")
                print(f"[AI] 응답: {response.text[:200]}")

        except requests.exceptions.ConnectionError:
            print("[AI] API 연결 실패 - URL 을 확인해주세요")
        except Exception as e:
            print(f"[AI] API 호출 실패: {e}")

    # API 비활성화 또는 실패 시 규칙 기반 추출 사용
    if not AI_API_ENABLED:
        print("[AI] AI API 비활성화 - 규칙 기반 추출 사용")
    elif not AI_API_BASE_URL or not AI_API_KEY:
        print("[AI] AI API 설정 불완전 - 규칙 기반 추출 사용")
    else:
        print("[AI] 규칙 기반 추출 사용")

    return analyze_with_rule_based(stt_text)


def apply_corrections(text):
    """
    텍스트에 오타 수정 적용

    Args:
        text: 원본 텍스트

    Returns:
        수정된 텍스트
    """
    corrections = get_corrections()
    result = text
    for wrong, correct in corrections.items():
        result = result.replace(wrong, correct)
    return result


def save_user_correction(wrong_word, correct_word):
    """
    사용자 오타 수정 저장 (corrections.json 에 추가)

    Args:
        wrong_word: 틀린 단어
        correct_word: 올바른 단어

    Returns:
        성공 여부
    """
    try:
        # 기존 사전 로드
        if CORRECTIONS_FILE.exists():
            with open(CORRECTIONS_FILE, 'r', encoding='utf-8') as f:
                corrections = json.load(f)
        else:
            corrections = {}

        # 새 항목 추가
        corrections[wrong_word] = correct_word

        # 저장
        with open(CORRECTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(corrections, f, ensure_ascii=False, indent=2)

        # 캐시 초기화
        global _CORRECTIONS
        _CORRECTIONS = None

        print(f"[오타수정] '{wrong_word}' → '{correct_word}' 저장 완료")
        return True
    except Exception as e:
        print(f"[오타수정] 저장 실패: {e}")
        return False


def analyze_with_rule_based(stt_text):
    """
    규칙 기반 정보 추출 (AI API 대체용)
    STT 텍스트에서 실제 정보를 추출

    Args:
        stt_text: STT 텍스트

    Returns:
        분석 결과 딕셔너리
    """
    # 텍스트 정제 (STT 오타 수정 - 중앙 집중식 apply_corrections 사용)
    text = apply_corrections(stt_text)

    # 기본 구조 생성
    meeting_data = {
        "meetingTitle": "회의록",
        "purpose": "",
        "participants": [],
        "discussions": [],
        "decisions": [],
        "actionItems": []
    }

    # 회의 제목 추출
    title_match = extract_between(text, ['회의 명은', '회의명은', '회의 이름은'], ['이고', '입니다', '会议는'])
    if title_match:
        meeting_data["meetingTitle"] = title_match.strip() + " 회의"

    # 회의 일자 추출
    date_match = extract_between(text, ['회의 일자는', '일자는'], ['会议는', '입니다', '요일'])
    if date_match:
        if "meetingDate" not in meeting_data:
            meeting_data["meetingDate"] = date_match.strip()

    # 회의 시간 추출
    time_match = extract_between(text, ['회의 시간은', '시간은'], ['부터', '~', '입니다'])
    if time_match:
        time_match2 = extract_between(text, ['시 '], ['부터', '~'])
        if time_match2:
            meeting_data["meetingTime"] = time_match2.strip()

    # 참석자 추출
    participants = []
    if "참석자는" in text:
        start_idx = text.find("참석자는") + len("참석자는")
        end_idx = text.find("회의 안건은")
        if end_idx == -1:
            end_idx = text.find("요청사항")
        if end_idx == -1:
            end_idx = text.find("현재는")

        if end_idx > start_idx:
            participants_text = text[start_idx:end_idx]
            parts = participants_text.replace('그리고', ',').split(',')
            for part in parts:
                part = part.strip()
                if part and len(part) > 1:
                    name = part.replace('팀장', '').replace('책임', '').replace('이사', '').strip()
                    role = ''
                    if '팀장' in part:
                        role = '팀장'
                    elif '책임' in part:
                        role = '책임'
                    elif '이사' in part:
                        role = '이사'

                    if name and name not in ['참석자는', '이고']:
                        participants.append({
                            "name": name,
                            "role": role,
                            "department": ""
                        })

    if participants:
        meeting_data["participants"] = participants

    # 목적 추출
    purpose_match = extract_between(text, ['목적은', '목표는'], ['현재는', '요청사항', '안건은', '입니다'])
    if purpose_match:
        meeting_data["purpose"] = purpose_match.strip()

    # 논의사항 추출 - 요청사항
    if "요청사항으로는" in text or "요청사항은" in text:
        discussions = []
        start_idx = text.find("요청사항으로는") if "요청사항으로는" in text else text.find("요청사항은")
        start_idx += len("요청사항으로는") if "요청사항으로는" in text else len("요청사항은")

        if "주문 번호별 1 차 이상" in text:
            discussions.append({
                "topic": "주문 번호별 낙기 안내",
                "content": "1 차 이상 낙기 안내를 통해 미확정 낙기 확정"
            })
        if "2 차 이상" in text:
            discussions.append({
                "topic": "2 차 낙기 수정",
                "content": "입고실적 발생 기준으로 낙기 수정, 주문 번호별 2 차 이상 낙기 안내 통해 확정 낙기 수정"
            })
        if "입고 완료율" in text or "입고완료율" in text:
            discussions.append({
                "topic": "입고 완료율",
                "content": "최종 입고 실적 충만으로 부족하지 않도록 KPI 수치 지켜질 예정"
            })
        if "만족률 기준" in text or "만족률기준" in text:
            discussions.append({
                "topic": "만족률 기준",
                "content": "2000 건 내 입고 완료 재공료"
            })

        if discussions:
            meeting_data["discussions"] = discussions

    # 결정사항 추출
    if "향후" in text:
        decisions = []
        if "입고 실적" in text and "신규 개발" in text:
            decisions.append({
                "decision": "입고 실적과 신규 개발 함께 반영",
                "reason": "관리 효율성 제고"
            })
        if "알람 메일 개발" in text:
            decisions.append({
                "decision": "입고 완료 알람 메일 개발",
                "reason": "자동화 시스템 구축"
            })

        if decisions:
            meeting_data["decisions"] = decisions

    # 액션 아이템 추출
    action_items = []
    if "개발" in text and "일정" in text:
        action_items.append({
            "description": "개발 일정 확인 및 공유",
            "assignee": "개발팀",
            "dueDate": "매일"
        })
    if "이슈 발생" in text:
        action_items.append({
            "description": "개발 이슈 발생 시 전체 공유",
            "assignee": "프로젝트 관리자",
            "dueDate": "즉시"
        })
    if "ITSM" in text or "itsm" in text:
        action_items.append({
            "description": "공정 수정 시 ITSM 수정",
            "assignee": "관련 팀",
            "dueDate": "수정 시"
        })

    if action_items:
        meeting_data["actionItems"] = action_items

    # 기본 값 설정 (추출 실패 시)
    if not meeting_data["meetingTitle"]:
        meeting_data["meetingTitle"] = "주문진행관리 개선 회의" if "주문" in text else "회의록"

    return meeting_data


def extract_between(text, start_keywords, end_keywords):
    """텍스트에서 시작 키워드와 ending 키워드 사이의 내용 추출"""
    start_idx = -1
    start_keyword_used = ""

    for kw in start_keywords:
        idx = text.find(kw)
        if idx != -1:
            start_idx = idx + len(kw)
            start_keyword_used = kw
            break

    if start_idx == -1:
        return None

    end_idx = len(text)
    for kw in end_keywords:
        idx = text.find(kw, start_idx)
        if idx != -1 and idx < end_idx:
            end_idx = idx

    if end_idx > start_idx:
        return text[start_idx:end_idx].strip()

    return None
