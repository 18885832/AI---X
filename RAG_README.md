# RAG (Retrieval-Augmented Generation) 참고폴더 기능

## 개요

참고폴더에 문서를 업로드하면 AI 가 회의 분석 시 해당 내용을 참고하여 더 정확한 분석을 수행합니다.

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                    RAG 참고폴더 아키텍처                          │
├─────────────────────────────────────────────────────────────────┤
│  [참고폴더] → [문서 로드] → [임베딩] → [벡터 DB]                  │
│       ↓                                      ↓                  │
│  [회의 내용] → [유사 문서 검색] → [문맥 추가] → [AI 분석]         │
└─────────────────────────────────────────────────────────────────┘
```

## 설치

### 필수 패키지

```bash
# LangChain 및 관련 라이브러리
pip install langchain langchain-community faiss-cpu

# 문서 처리 라이브러리 (선택사항)
pip install python-docx      # Word 문서 (.docx)
pip install PyMuPDF          # PDF 문서 (.pdf)
pip install python-pptx      # PowerPoint (.pptx)
pip install pandas openpyxl  # Excel (.xlsx)

# 임베딩 모델
pip install sentence-transformers
```

### 모든 패키지 한 번에 설치

```bash
pip install langchain langchain-community faiss-cpu python-docx PyMuPDF python-pptx pandas openpyxl sentence-transformers
```

## 사용 방법

### 1. 웹 UI 에서 사용

1. 브라우저에서 http://localhost:8000 접속
2. "4. 참고폴더 (RAG)" 섹션에서 파일 업로드
3. 업로드 완료 후 AI 분석 실행 시 참고파일 내용이 자동으로 반영됨

### 2. 지원되는 파일 형식

| 파일 형식 | 확장자 | 비고 |
|-----------|--------|------|
| 텍스트 파일 | .txt, .md | 바로 읽기 가능 |
| JSON | .json | 구조화된 데이터 |
| CSV | .csv | 테이블 데이터 |
| Word 문서 | .docx | python-docx 필요 |
| PDF | .pdf | PyMuPDF 필요 |
| PowerPoint | .pptx | python-pptx 필요 |
| Excel | .xlsx, .xls | pandas 필요 |

### 3. 기능

- **파일 업로드**: 여러 파일을 한 번에 업로드 가능
- **자동 인덱싱**: 파일 업로드 시 자동으로 RAG 인덱스 구축
- **검색**: 참고파일 내용 검색 가능
- **인덱스 새로고침**: 수동으로 인덱스 재생성 가능
- **파일 삭제**: 불필요한 참고파일 삭제 가능

## 동작 원리

1. **문서 로드**: 참고폴더의 모든 파일을 읽어서 텍스트 추출
2. **청킹**: 긴 문서를 적절한 크기의 청크로 분할
3. **임베딩**: 각 청크를 벡터 형태로 변환 (문장 임베딩)
4. **벡터 저장**: FAISS 벡터 데이터베이스에 저장
5. **검색**: 회의 내용과 유사한 청크 검색 (유사도 기반)
6. **프롬프트 구성**: 검색된 내용을 AI 프롬프트에 포함
7. **분석**: AI 가 참고내용을 반영하여 분석

## API 엔드포인트

| 엔드포인트 | 방법 | 설명 |
|------------|------|------|
| `/api/reference/files` | GET | 참고파일 목록 조회 |
| `/api/reference/upload` | POST | 참고파일 업로드 |
| `/api/reference/files/{filename}` | DELETE | 참고파일 삭제 |
| `/api/reference/refresh` | POST | 인덱스 새로고침 |
| `/api/reference/search` | GET | 참고파일 검색 |

## 폴더 구조

```
프로젝트 루트/
├── Reference/           # 참고폴더 (업로드된 파일 저장)
├── .rag_cache/          # RAG 인덱스 캐시
├── rag_context.py       # RAG 컨텍스트 관리 모듈
├── web_app.py           # FastAPI 웹 애플리케이션
├── ai_analyzer.py       # AI 분석 모듈 (RAG 연동)
└── static/
    ├── index.html       # 웹 UI
    ├── app.js           # 프론트엔드 로직
    └── style.css        # 스타일
```

## 주의사항

1. **처음 처리 시간**: 대용량 파일을 업로드할 경우 인덱싱에 시간이 소요될 수 있습니다.
2. **메모리 사용**: 벡터 임베딩 생성 시 메모리를 사용하므로 대용량 처리 시 주의가 필요합니다.
3. **파일 크기**: 개별 파일은 10MB 이하를 권장합니다.

## 예시 사용 시나리오

1. **회사 정책 문서 업로드**
   - 직원 수칙, 규정 문서 업로드
   - 회의에서 정책 관련 논의 시 AI 가 해당 규정 참고

2. **프로젝트 문서 업로드**
   - 프로젝트 명세서, 요구사항 문서 업로드
   - 관련 회의 시 프로젝트 배경지식 반영

3. **이전 회의록 업로드**
   - 과거 회의록 업로드
   - 연속된 논의의 맥락 유지

## 문제 해결

### "LangChain 이 사용할 수 없습니다" 오류

```bash
pip install langchain langchain-community faiss-cpu
```

### 문서 읽기 오류

- 해당 문서 형식을 처리하는 라이브러리가 설치되어 있는지 확인
- 예: .docx 파일 → `pip install python-docx`

### 검색 결과가 없음

- 참고파일에 검색어가 포함되어 있는지 확인
- 인덱스 새로고침 시도
