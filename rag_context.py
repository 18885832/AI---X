# -*- coding: utf-8 -*-
"""
RAG (Retrieval-Augmented Generation) 컨텍스트 모듈
참고폴더의 문서를 로드, 임베딩, 검색하여 AI 분석에 활용
"""
import os
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional
import re

# 문서 로드 모듈
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import FAISS
    HAS_LANGCHAIN = True
except ImportError:
    HAS_LANGCHAIN = False


class RAGContextManager:
    """RAG 컨텍스트 관리 클래스"""

    def __init__(self, reference_dir: Optional[str] = None):
        """
        RAG 컨텍스트 관리자 초기화

        Args:
            reference_dir: 참고폴더 경로 (기본값: 프로젝트 루트의 'Reference' 폴더)
        """
        base_dir = Path(__file__).parent
        self.reference_dir = Path(reference_dir) if reference_dir else base_dir / "Reference"
        self.cache_dir = base_dir / ".rag_cache"
        self.vectorstore = None
        self.embeddings = None
        self.text_splitter = None
        self.documents = []
        self._initialized = False

        # 디렉토리 생성
        self.reference_dir.mkdir(exist_ok=True)
        self.cache_dir.mkdir(exist_ok=True)

    def initialize(self):
        """RAG 시스템 초기화"""
        if self._initialized:
            return

        if not HAS_LANGCHAIN:
            print("[RAG] LangChain 미설치 - 간단한 텍스트 기반 검색 사용 (시작 시 1 회 표시)")
            self._initialized = True
            return
        print("[RAG] LangChain 기반 RAG 시스템 활성화됨")

        try:
            # 텍스트 분할기 설정
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                length_function=len,
                separators=["\n\n", "\n", "。", ".", " ", ""]
            )

            # 임베딩 모델 설정 (경량 모델 사용)
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True}
            )

            self._initialized = True
            print("[RAG] RAG 시스템 초기화 완료")

        except Exception as e:
            print(f"[RAG] 초기화 실패: {e}")
            self._initialized = False

    def load_documents(self) -> List[Dict]:
        """
        참고폴더의 모든 문서를 로드

        Returns:
            로드된 문서 목록
        """
        documents = []

        if not self.reference_dir.exists():
            print(f"[RAG] 참고폴더가 없습니다: {self.reference_dir}")
            return documents

        # 모든 파일 탐색
        for file_path in self.reference_dir.rglob("*"):
            if file_path.is_file():
                try:
                    content = self._load_file(file_path)
                    if content and len(content.strip()) > 0:
                        documents.append({
                            "path": str(file_path),
                            "filename": file_path.name,
                            "content": content,
                            "extension": file_path.suffix.lower()
                        })
                except Exception as e:
                    print(f"[RAG] 파일 로드 실패 ({file_path}): {e}")

        self.documents = documents
        print(f"[RAG] {len(documents)}개의 문서 로드 완료")
        return documents

    def _load_file(self, file_path: Path) -> Optional[str]:
        """
        파일을 로드하여 텍스트 추출

        Args:
            file_path: 파일 경로

        Returns:
            추출된 텍스트
        """
        ext = file_path.suffix.lower()

        try:
            # 텍스트 파일
            if ext in ['.txt', '.md', '.json', '.csv', '.py', '.js', '.html', '.css']:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()

            # Word 문서 (.docx)
            elif ext == '.docx':
                try:
                    from docx import Document
                    doc = Document(file_path)
                    return '\n'.join([para.text for para in doc.paragraphs])
                except ImportError:
                    print("[RAG] python-docx 가 설치되지 않았습니다.")
                    return None

            # PDF
            elif ext == '.pdf':
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(file_path)
                    text = []
                    for page in doc:
                        text.append(page.get_text())
                    return '\n'.join(text)
                except ImportError:
                    print("[RAG] PyMuPDF 가 설치되지 않았습니다.")
                    return None

            # PowerPoint
            elif ext == '.pptx':
                try:
                    from pptx import Presentation
                    prs = Presentation(file_path)
                    text = []
                    for slide in prs.slides:
                        for shape in slide.shapes:
                            if hasattr(shape, "text"):
                                text.append(shape.text)
                    return '\n'.join(text)
                except ImportError:
                    print("[RAG] python-pptx 가 설치되지 않았습니다.")
                    return None

            # Excel
            elif ext in ['.xlsx', '.xls']:
                try:
                    import pandas as pd
                    df = pd.read_excel(file_path)
                    return df.to_string()
                except ImportError:
                    print("[RAG] pandas 가 설치되지 않았습니다.")
                    return None

            else:
                # 다른 파일은 시도하지 않음
                return None

        except Exception as e:
            print(f"[RAG] 파일 읽기 실패 ({file_path}): {e}")
            return None

    def build_vectorstore(self):
        """벡터 저장소 구축"""
        if not self.documents:
            self.load_documents()

        if not self.documents:
            return

        if HAS_LANGCHAIN and self.embeddings and self.text_splitter:
            try:
                # 문서를 청크로 분할
                all_texts = []
                for doc in self.documents:
                    chunks = self.text_splitter.split_text(doc["content"])
                    for chunk in chunks:
                        all_texts.append({
                            "text": chunk,
                            "source": doc["filename"],
                            "path": doc["path"]
                        })

                # 벡터 저장소 구축
                texts = [item["text"] for item in all_texts]
                self.vectorstore = FAISS.from_texts(
                    texts,
                    self.embeddings,
                    metadatas=all_texts
                )

                # 캐시 저장
                self._save_cache(all_texts)

                print(f"[RAG] 벡터 저장소 구축 완료 ({len(texts)}개의 청크)")

            except Exception as e:
                print(f"[RAG] 벡터 저장소 구축 실패: {e}")
        else:
            # 간단한 텍스트 기반 검색을 위해 모든 텍스트 저장
            self._simple_index = self.documents
            print("[RAG] 간단한 인덱싱 완료")

    def _save_cache(self, all_texts: List[Dict]):
        """벡터 저장소 캐시"""
        cache_file = self.cache_dir / "vectorstore_cache.json"
        cache_data = {
            "texts": all_texts,
            "timestamp": __import__('datetime').datetime.now().isoformat()
        }
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)

    def _load_cache(self) -> Optional[List[Dict]]:
        """캐시 로드"""
        cache_file = self.cache_dir / "vectorstore_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get("texts", [])
            except:
                return None
        return None

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        참고 문서 검색

        Args:
            query: 검색 쿼리
            top_k: 반환할 문서 수

        Returns:
            유사한 문서 목록
        """
        if not self._initialized:
            self.initialize()

        # 벡터 저장소가 없으면 구축
        if HAS_LANGCHAIN and self.vectorstore is None:
            # 캐시 확인
            cached = self._load_cache()
            if cached and self.embeddings:
                try:
                    self.vectorstore = FAISS.from_texts(
                        [item["text"] for item in cached],
                        self.embeddings,
                        metadatas=cached
                    )
                except:
                    pass

            if self.vectorstore is None:
                self.build_vectorstore()

        if HAS_LANGCHAIN and self.vectorstore and self.embeddings:
            try:
                # 유사도 검색
                results = self.vectorstore.similarity_search_with_score(query, k=top_k)
                return [
                    {
                        "content": result.page_content,
                        "source": result.metadata.get("source", "unknown"),
                        "score": 1 - score  # 점수를 유사도로 변환
                    }
                    for result, score in results
                ]
            except Exception as e:
                print(f"[RAG] 검색 실패: {e}")
                return []
        else:
            # 간단한 키워드 기반 검색
            return self._simple_search(query, top_k)

    def _simple_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        간단한 키워드 기반 검색 (LangChain unavailable 시)

        Args:
            query: 검색 쿼리
            top_k: 반환할 문서 수

        Returns:
            유사한 문서 목록
        """
        if not self.documents:
            self.load_documents()

        query_keywords = set(re.findall(r'\w+|\S', query.lower()))
        results = []

        for doc in self.documents:
            content_lower = doc["content"].lower()
            match_count = sum(1 for kw in query_keywords if kw in content_lower)

            if match_count > 0:
                # 관련 있는 문장 추출
                sentences = re.split(r'[.!?.\n]', doc["content"])
                relevant_sentences = []
                for sentence in sentences:
                    if any(kw in sentence.lower() for kw in query_keywords):
                        relevant_sentences.append(sentence.strip())

                results.append({
                    "content": "\n".join(relevant_sentences[:5]),  # 최대 5 문장
                    "source": doc["filename"],
                    "score": match_count / len(query_keywords) if query_keywords else 0
                })

        # 점수로 정렬
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def get_relevant_context(self, query: str, max_length: int = 3000) -> str:
        """
        쿼리와 관련된 컨텍스트 추출

        Args:
            query: 검색 쿼리
            max_length: 최대 텍스트 길이

        Returns:
            관련 컨텍스트 텍스트
        """
        results = self.search(query, top_k=5)

        if not results:
            return ""

        # 컨텍스트 조립
        context_parts = []
        current_length = 0

        for result in results:
            if current_length >= max_length:
                break

            source = result["source"]
            content = result["content"]

            # 각 소스별 요약
            part = f"[{source}]\n{content}"
            part_length = len(part)

            if current_length + part_length <= max_length:
                context_parts.append(part)
                current_length += part_length
            elif len(context_parts) == 0:
                # 첫 번째 문서는 부분 포함
                part = f"[{source}]\n{content[:max_length]}"
                context_parts.append(part)
                current_length = max_length
            else:
                break

        return "\n\n---\n\n".join(context_parts)

    def build_rag_prompt(self, stt_text: str, meeting_type: str = "일반회의") -> str:
        """
        RAG 컨텍스트를 포함한 프롬프트 생성

        Args:
            stt_text: STT 변환 텍스트
            meeting_type: 회의 유형

        Returns:
            RAG 프롬프트
        """
        # 쿼리 추출 (간단히 처음 500 자)
        query = stt_text[:500] if len(stt_text) > 500 else stt_text

        # 관련 컨텍스트 검색
        context = self.get_relevant_context(query)

        if context:
            return f"""다음 회의 내용과 참고 자료를 분석하여 JSON 형식으로만 반환하세요. 다른 설명은 빼고 JSON 만 출력하세요.

== 참고 자료 (참고폴더에서 검색된 관련 정보) ==
{context}
== 참고 자료 끝 ==

회의 내용:
{stt_text[:10000]}

반드시 다음 JSON 형식대로만 출력하세요:
{{
    "meetingTitle": "회의 제목",
    "purpose": "회의 목적",
    "participants": {{"name": "이름", "role": "직위", "department": "부서"}},
    "discussions": [{{"topic": "주제", "content": "내용"}}],
    "decisions": [{{"decision": "결정사항", "reason": "이유"}}],
    "actionItems": [{{"description": "업무", "assignee": "담당자", "dueDate": "기한"}}]
}}

참고 자료의 내용을 회의 분석에 최대한 반영하세요. 특히 용어, 프로젝트명, 관련 배경지식이 있으면 활용하세요."""
        else:
            return f"""다음 회의록을 분석하여 JSON 형식으로만 반환하세요. 다른 설명은 빼고 JSON 만 출력하세요.

회의 내용:
{stt_text[:10000]}

반드시 다음 JSON 형식대로만 출력하세요:
{{
    "meetingTitle": "회의 제목",
    "purpose": "회의 목적",
    "participants": [{{"name": "이름", "role": "직위", "department": "부서"}}],
    "discussions": [{{"topic": "주제", "content": "내용"}}],
    "decisions": [{{"decision": "결정사항", "reason": "이유"}}],
    "actionItems": [{{"description": "업무", "assignee": "담당자", "dueDate": "기한"}}]
}}"""

    def get_reference_files(self) -> List[Dict]:
        """
        참고폴더의 파일 목록 반환

        Returns:
            파일 목록
        """
        files = []
        if self.reference_dir.exists():
            for file_path in self.reference_dir.rglob("*"):
                if file_path.is_file():
                    files.append({
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "extension": file_path.suffix.lower()
                    })
        return files

    def refresh(self):
        """RAG 인덱스 새로고침"""
        self.vectorstore = None
        self.documents = []
        self._initialized = False
        self.initialize()
        self.build_vectorstore()
        print("[RAG] 인덱스 새로고침 완료")


# 전역 RAG 관리자
rag_manager = RAGContextManager()


def get_rag_context(query: str) -> str:
    """
    전역 RAG 관리자에서 컨텍스트 가져오기

    Args:
        query: 검색 쿼리

    Returns:
        관련 컨텍스트
    """
    return rag_manager.get_relevant_context(query)


def build_rag_prompt(stt_text: str, meeting_type: str = "일반회의") -> str:
    """
    전역 RAG 관리자에서 RAG 프롬프트 생성

    Args:
        stt_text: STT 텍스트
        meeting_type: 회의 유형

    Returns:
        RAG 프롬프트
    """
    return rag_manager.build_rag_prompt(stt_text, meeting_type)
