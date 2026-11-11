# -*- coding: utf-8 -*-
"""
웹 UI 기반 AI 회의록 생성 시스템
FastAPI 를 활용한 웹 애플리케이션
"""
import os
import sys
import json
import shutil
import uuid
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Body
from typing import Optional, List
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from stt_converter import convert_audio_to_text, get_audio_files
from ai_analyzer import call_hyundai_steel_ai
from config import AVAILABLE_MODELS
from ppt_generator import create_meeting_ppt
from config import REPORTS_DIR
from pathlib import Path
REPORTS_DIR = Path(REPORTS_DIR)

# RAG 컨텍스트 import
try:
    from rag_context import rag_manager
    HAS_RAG = True
except ImportError:
    HAS_RAG = False

# 오타 수정 import
try:
    from ai_analyzer import get_corrections, save_user_correction, CORRECTIONS_FILE
    HAS_CORRECTIONS = True
except ImportError:
    HAS_CORRECTIONS = False

# 오타 수정 모델 정의
class CorrectionItem(BaseModel):
    wrong_word: str
    correct_word: str

# 앱 생성
app = FastAPI(title="AI 회의록 생성 시스템")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 디렉토리 설정
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "web_uploads"
STATIC_DIR = BASE_DIR / "static"

UPLOAD_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# 정적 파일 마운팅
try:
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
except:
    pass

# RAG 초기화 (서버 시작 시 참고폴더 인덱싱)
if HAS_RAG:
    try:
        rag_manager.initialize()
        rag_manager.build_vectorstore()
        print("[RAG] 서버 시작 시 참고폴더 인덱싱 완료")
    except Exception as e:
        print(f"[RAG] 초기화 실패: {e}")

# 파일 저장
@app.post("/api/upload")
async def upload_audio(file: UploadFile = File(...)):
    """음성 파일 업로드"""
    # 파일명 확인
    if not file.filename:
        raise HTTPException(status_code=400, detail="파일이 비어있습니다.")

    # 파일 확장자 검증
    allowed_extensions = {'.m4a', '.wav', '.mp3', '.flac'}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail=f"지원하지 않는 파일 형식입니다. (허용: {', '.join(allowed_extensions)})")

    # 고유 ID 생성
    file_id = str(uuid.uuid4())[:8]
    original_filename = file.filename
    saved_filename = f"{file_id}_{original_filename}"
    file_path = UPLOAD_DIR / saved_filename

    # 파일 저장
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        return {
            "success": True,
            "file_id": file_id,
            "filename": original_filename,
            "status": "uploaded",
            "message": "파일 업로드 완료"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장 실패: {str(e)}")


@app.post("/api/analyze")
async def analyze_audio(file_id: Optional[str] = Query(None), model_name: Optional[str] = Query(None)):
    """STT 변환 및 AI 분석 실행"""
    # 파일 찾기
    files = list(UPLOAD_DIR.glob(f"{file_id}_*"))
    m4a_files = [f for f in files if f.suffix.lower() == '.m4a']
    wav_files = [f for f in files if f.suffix.lower() == '.wav']
    mp3_files = [f for f in files if f.suffix.lower() == '.mp3']

    audio_files = m4a_files + wav_files + mp3_files

    if not audio_files:
        raise HTTPException(status_code=404, detail="음성 파일을 찾을 수 없습니다.")

    audio_path = audio_files[0]

    try:
        # 1. STT 변환
        stt_text = convert_audio_to_text(str(audio_path), model_name="base")

        if not stt_text or len(stt_text) < 10:
            raise HTTPException(status_code=500, detail="STT 변환 실패 - 텍스트가 너무 짧습니다.")

        # 2. AI 분석 (모델 선택 지원)
        endpoint = None
        if model_name:
            # 모델명에서 엔드포인트 찾기
            for m in AVAILABLE_MODELS:
                if m["name"] == model_name:
                    endpoint = m["endpoint"]
                    break
        meeting_data = call_hyundai_steel_ai(stt_text, model_name=model_name, endpoint=endpoint)

        if not meeting_data:
            raise HTTPException(status_code=500, detail="AI 분석 실패")

        # 결과 저장
        result_file = UPLOAD_DIR / f"{file_id}_result.json"
        result_data = {
            "stt_text": stt_text,
            "meeting_data": meeting_data,
            "analyzed_at": datetime.now().isoformat()
        }

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "status": "analyzed",
            "data": meeting_data,
            "stt_text": stt_text,
            "message": "분석 완료"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"분석 실패: {str(e)}")


@app.post("/api/save-edit")
async def save_edit(file_id: str = Query(...), meeting_data: dict = Body(...)):
    """분석 결과 수정 저장"""
    result_file = UPLOAD_DIR / f"{file_id}_result.json"

    if not result_file.exists():
        raise HTTPException(status_code=400, detail="결과 파일을 찾을 수 없습니다.")

    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            result_data = json.load(f)

        result_data["meeting_data"] = meeting_data
        result_data["edited_at"] = datetime.now().isoformat()

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "message": "수정 사항이 저장되었습니다."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"저장 실패: {str(e)}")


@app.post("/api/generate")
async def generate_ppt(file_id: Optional[str] = Query(None)):
    """PPT 생성"""
    result_file = UPLOAD_DIR / f"{file_id}_result.json"

    if not result_file.exists():
        raise HTTPException(status_code=400, detail="먼저 분석을 실행해주세요.")

    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            result_data = json.load(f)

        meeting_data = result_data.get("meeting_data", {})

        # Reports 폴더에 file_id 포함하여 저장
        output_filename = f"{file_id}_회의록.pptx"
        output_path = REPORTS_DIR / output_filename

        # PPT 생성 (Reports 폴더에 저장됨)
        created_path = create_meeting_ppt(meeting_data, output_filename)

        # 결과 저장
        result_data["ppt_path"] = created_path
        result_data["generated_at"] = datetime.now().isoformat()

        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)

        return {
            "success": True,
            "status": "generated",
            "ppt_path": created_path,
            "message": "PPT 생성 완료"
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"PPT 생성 실패: {str(e)}")


@app.get("/api/download/{file_id}")
async def download_ppt(file_id: str):
    """PPT 다운로드"""
    # 결과 JSON 에서 PPT 경로 확인
    result_file = UPLOAD_DIR / f"{file_id}_result.json"

    if result_file.exists():
        with open(result_file, 'r', encoding='utf-8') as f:
            result_data = json.load(f)
        ppt_path = result_data.get("ppt_path")
        if ppt_path and os.path.exists(ppt_path):
            download_filename = Path(ppt_path).stem
            return FileResponse(
                ppt_path,
                media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                filename=download_filename
            )

    # web_uploads 에서 찾기
    ppt_files = list(UPLOAD_DIR.glob(f"{file_id}_*.pptx"))

    # 없으면 Reports 폴더에서 찾기
    if not ppt_files:
        reports_dir = BASE_DIR / "Reports"
        ppt_files = list(reports_dir.glob(f"{file_id}_*.pptx"))

    # 그래도 없으면 Reports 에서 모든 PPT 파일 찾기 (file_id 없이)
    if not ppt_files:
        ppt_files = list(reports_dir.glob("*.pptx"))

    if not ppt_files:
        raise HTTPException(status_code=404, detail="PPT 파일을 찾을 수 없습니다.")

    ppt_path = ppt_files[0]

    # 파일명 인코딩 처리
    download_filename = ppt_path.stem

    return FileResponse(
        str(ppt_path),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=download_filename
    )


@app.get("/api/status/{file_id}")
async def get_status(file_id: str):
    """파일 처리 상태 확인"""
    result_file = UPLOAD_DIR / f"{file_id}_result.json"

    if not result_file.exists():
        return {
            "success": True,
            "file_id": file_id,
            "status": "uploaded",
            "analyzed": False,
            "generated": False
        }

    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            result_data = json.load(f)

        return {
            "success": True,
            "file_id": file_id,
            "status": "analyzed",
            "analyzed": True,
            "generated": "ppt_path" in result_data,
            "data": result_data.get("meeting_data", {})
        }
    except:
        return {
            "success": True,
            "file_id": file_id,
            "status": "unknown",
            "analyzed": False,
            "generated": False
        }


# 참고폴더 관리 API
class ReferenceFileResponse(BaseModel):
    name: str
    path: str
    size: int
    extension: str


@app.get("/api/reference/files")
async def get_reference_files():
    """참고폴더의 파일 목록 조회"""
    if not HAS_RAG:
        return JSONResponse(
            status_code=501,
            content={"error": "RAG 모듈이 사용할 수 없습니다. LangChain 을 설치해주세요."}
        )

    try:
        files = rag_manager.get_reference_files()
        return {
            "success": True,
            "files": files,
            "count": len(files),
            "reference_dir": str(rag_manager.reference_dir)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 목록 조회 실패: {str(e)}")


@app.post("/api/reference/upload")
async def upload_reference_file(file: UploadFile = File(...)):
    """참고폴더에 파일 업로드"""
    if not HAS_RAG:
        raise HTTPException(status_code=510, detail="RAG 모듈이 사용할 수 없습니다.")

    try:
        # 파일 저장
        file_path = rag_manager.reference_dir / file.filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # 인덱스 새로고침
        rag_manager.refresh()

        return {
            "success": True,
            "filename": file.filename,
            "message": "참고파일 업로드 완료. RAG 인덱스가 새로고침되었습니다."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 업로드 실패: {str(e)}")


@app.delete("/api/reference/files/{filename:path}")
async def delete_reference_file(filename: str):
    """참고폴더에서 파일 삭제"""
    if not HAS_RAG:
        raise HTTPException(status_code=510, detail="RAG 모듈이 사용할 수 없습니다.")

    try:
        file_path = rag_manager.reference_dir / filename
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

        # 안전 확인: 참고폴더 밖으로 나가는 경로 차단
        try:
            file_path.resolve().relative_to(rag_manager.reference_dir.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="유효하지 않은 경로입니다.")

        file_path.unlink()

        # 인덱스 새로고침
        rag_manager.refresh()

        return {
            "success": True,
            "filename": filename,
            "message": "참고파일 삭제 완료. RAG 인덱스가 새로고침되었습니다."
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 삭제 실패: {str(e)}")


@app.post("/api/reference/refresh")
async def refresh_reference_index():
    """참고폴더 인덱스 새로고침"""
    if not HAS_RAG:
        raise HTTPException(status_code=510, detail="RAG 모듈이 사용할 수 없습니다.")

    try:
        rag_manager.refresh()
        return {
            "success": True,
            "message": "RAG 인덱스 새로고침 완료"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"인덱스 새로고침 실패: {str(e)}")


@app.get("/api/reference/search")
async def search_reference(query: str, top_k: int = 5):
    """참고폴더 검색"""
    if not HAS_RAG:
        raise HTTPException(status_code=510, detail="RAG 모듈이 사용할 수 없습니다.")

    try:
        results = rag_manager.search(query, top_k=top_k)
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"검색 실패: {str(e)}")


# ==================== 오타 수정 API ====================

@app.get("/api/corrections")
async def get_corrections_list():
    """오타 수정 사전 목록 조회"""
    if not HAS_CORRECTIONS:
        return JSONResponse(
            status_code=501,
            content={"error": "오타 수정 모듈이 사용할 수 없습니다."}
        )

    try:
        corrections = get_corrections()
        return {
            "success": True,
            "corrections": corrections,
            "count": len(corrections)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"사전 조회 실패: {str(e)}")


@app.post("/api/corrections")
async def add_correction(correction: CorrectionItem):
    """오타 수정 항목 추가"""
    if not HAS_CORRECTIONS:
        raise HTTPException(status_code=510, detail="오타 수정 모듈이 사용할 수 없습니다.")

    try:
        success = save_user_correction(correction.wrong_word, correction.correct_word)
        if success:
            return {
                "success": True,
                "message": f"'{correction.wrong_word}' → '{correction.correct_word}' 저장 완료"
            }
        else:
            raise HTTPException(status_code=500, detail="저장 실패")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추가 실패: {str(e)}")


@app.delete("/api/corrections/{wrong_word:path}")
async def delete_correction(wrong_word: str):
    """오타 수정 항목 삭제"""
    if not HAS_CORRECTIONS:
        raise HTTPException(status_code=510, detail="오타 수정 모듈이 사용할 수 없습니다.")

    try:
        if not CORRECTIONS_FILE.exists():
            raise HTTPException(status_code=404, detail="사전 파일이 없습니다.")

        with open(CORRECTIONS_FILE, 'r', encoding='utf-8') as f:
            corrections = json.load(f)

        if wrong_word not in corrections:
            raise HTTPException(status_code=404, detail="해당 항목이 없습니다.")

        del corrections[wrong_word]

        with open(CORRECTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(corrections, f, ensure_ascii=False, indent=2)

        # 캐시 초기화
        global _CORRECTIONS
        try:
            from ai_analyzer import _CORRECTIONS
            import ai_analyzer
            ai_analyzer._CORRECTIONS = None
        except:
            pass

        return {
            "success": True,
            "message": f"'{wrong_word}' 항목 삭제 완료"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"삭제 실패: {str(e)}")


@app.get("/", response_class=HTMLResponse)
async def root():
    """메인 페이지"""
    static_index = STATIC_DIR / "index.html"

    if static_index.exists():
        with open(static_index, 'r', encoding='utf-8') as f:
            return f.read()

    return """
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>AI 회의록 생성 시스템</title>
        <style>
            body { font-family: '맑은 고딕', sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }
            .section { background: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 8px; }
            button { background: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; margin: 5px; }
            button:disabled { background: #ccc; cursor: not-allowed; }
            input[type="file"] { margin: 10px 0; }
            .status { margin: 10px 0; padding: 10px; background: #e9ecef; border-radius: 4px; }
        </style>
    </head>
    <body>
        <h1>AI 회의록 생성 시스템</h1>
        <p>정적 파일 (static/index.html) 을 생성해주세요.</p>
    </body>
    </html>
    """


if __name__ == "__main__":
    import uvicorn
    print("\n=== AI 회의록 웹 서버 ===")
    print("브라우저에서 http://localhost:8000 접속")
    print("종료: Ctrl+C\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
