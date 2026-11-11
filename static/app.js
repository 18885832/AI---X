// 전역 변수
let currentFileId = null;
let selectedFile = null;
let currentMeetingData = null; // 현재 분석된 데이터 저장
let isEditing = false; // 편집 모드 여부

// API 기본 URL
const API_BASE = '';

// HTML 이스케이프 함수
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 파일 선택 이벤트 리스너 (DOMContentLoaded 후에 등록)
function setupEventListeners() {
    const audioFileInput = document.getElementById('audioFile');
    if (audioFileInput) {
        audioFileInput.addEventListener('change', function(e) {
            console.log('[파일선택] change 이벤트 발생');
            const file = e.target.files[0];
            console.log('[파일선택] 선택된 파일:', file);
            if (file) {
                selectedFile = file;
                document.getElementById('fileName').textContent = file.name;
                document.getElementById('uploadStatus').innerHTML = '';
                // 업로드 버튼 활성화
                document.getElementById('uploadBtn').disabled = false;
                console.log('[파일선택] 파일 등록 완료:', file.name, '크기:', file.size);
            } else {
                console.log('[파일선택] 파일이 선택되지 않음');
            }
        });
    }
}

// DOM 준비 완료 후 이벤트 리스너 등록
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupEventListeners);
} else {
    setupEventListeners();
}

// 업로드 버튼 클릭 처리 (파일 선택 또는 업로드)
function handleUploadClick() {
    if (selectedFile) {
        // 파일이 선택되어 있으면 업로드
        uploadFile();
    } else {
        // 파일이 선택되지 않으면 파일 선택 팝업 열기
        document.getElementById('audioFile').click();
    }
}

// 파일 업로드
async function uploadFile() {
    console.log('[업로드] uploadFile 호출됨');
    console.log('[업로드] selectedFile:', selectedFile);

    if (!selectedFile) {
        console.error('[업로드] selectedFile 이 없음');
        showStatus('uploadStatus', '파일을 선택해주세요.', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);

    console.log('[업로드] FormData 준비:', {
        name: selectedFile.name,
        size: selectedFile.size,
        type: selectedFile.type
    });

    showStatus('uploadStatus', '업로드 중...', 'loading');
    setButtonDisabled('uploadBtn', true);

    try {
        console.log('[업로드] fetch 요청 시작: /api/upload');
        const response = await fetch(`${API_BASE}/api/upload`, {
            method: 'POST',
            body: formData
        });

        console.log('[업로드] 응답 받음:', response.status, response.ok);

        // 응답 상태 확인
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[업로드] HTTP 오류:', response.status, errorText);
            throw new Error(`서버 오류 (${response.status}): ${errorText}`);
        }

        const data = await response.json();
        console.log('[업로드] 응답 JSON:', data);

        if (data.success) {
            currentFileId = data.file_id;
            showStatus('uploadStatus', `업로드 완료: ${data.filename}`, 'success');
            setButtonDisabled('analyzeBtn', false);

            // 파일 입력 초기화
            document.getElementById('audioFile').value = '';
            selectedFile = null;
            document.getElementById('fileName').textContent = '';
        } else {
            showStatus('uploadStatus', data.detail || data.message || '업로드 실패', 'error');
        }
    } catch (error) {
        console.error('[업로드] 예외 발생:', error);
        showStatus('uploadStatus', `업로드 실패: ${error.message}`, 'error');
    }

    setButtonDisabled('uploadBtn', false);
}

// AI 분석 실행
async function analyzeAudio() {
    if (!currentFileId) {
        showStatus('analyzeStatus', '먼저 파일을 업로드해주세요.', 'error');
        return;
    }

    // 선택된 모델 가져오기
    const modelSelect = document.getElementById('modelSelect');
    const selectedModel = modelSelect ? modelSelect.value : 'Qwen3.5-122B-A10B-FP16';

    showStatus('analyzeStatus', `분석 중... (모델: ${selectedModel}, 수십 초 소요될 수 있습니다)`, 'loading');
    setButtonDisabled('analyzeBtn', true);
    document.getElementById('analysisResult').classList.remove('show');

    try {
        const response = await fetch(`${API_BASE}/api/analyze?file_id=${currentFileId}&model_name=${encodeURIComponent(selectedModel)}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showStatus('analyzeStatus', '분석 완료!', 'success');
            currentMeetingData = JSON.parse(JSON.stringify(data.data)); // 깊은 복사 저장
            displayAnalysisResult(currentMeetingData);
            setButtonDisabled('generateBtn', false);
            document.getElementById('editBtn').style.display = 'inline-block';

            // 분석 결과 확인 후 상태 업데이트
            await checkStatus();
        } else {
            showStatus('analyzeStatus', data.detail || '분석 실패', 'error');
        }
    } catch (error) {
        showStatus('analyzeStatus', `분석 실패: ${error.message}`, 'error');
    }

    setButtonDisabled('analyzeBtn', false);
}

// 분석 결과 표시
function displayAnalysisResult(data, editable = false) {
    const resultDiv = document.getElementById('analysisResult');

    let html = '<h3>분석 결과</h3>';

    // 회의 제목
    html += '<div class="result-item">';
    html += '<label>회의 제목</label>';
    if (editable) {
        html += `<textarea class="value-edit" id="edit-meetingTitle" rows="2">${data.meetingTitle || ''}</textarea>`;
    } else {
        html += `<div class="value">${data.meetingTitle || 'N/A'}</div>`;
    }
    html += '</div>';

    // 회의 목적
    if (data.purpose || editable) {
        html += '<div class="result-item">';
        html += '<label>회의 목적</label>';
        if (editable) {
            html += `<textarea class="value-edit" id="edit-purpose" rows="3">${data.purpose || ''}</textarea>`;
        } else {
            html += `<div class="value">${data.purpose || ''}</div>`;
        }
        html += '</div>';
    }

    // 참석자
    if ((data.participants && data.participants.length > 0) || editable) {
        html += '<div class="result-item">';
        html += '<label>참석자</label>';
        if (editable) {
            let participantText = '';
            data.participants?.forEach((p, idx) => {
                if (idx > 0) participantText += '\n';
                participantText += `${p.name || ''} | ${p.role || ''} | ${p.department || ''}`;
            });
            html += `<textarea class="value-edit" id="edit-participants" rows="5">${participantText}</textarea>`;
            html += '<small class="hint">각 줄에 한 명씩: 이름 | 직위 | 부서</small>';
        } else {
            html += '<div class="value"><ul>';
            data.participants?.forEach(p => {
                const name = p.name || '';
                const role = p.role ? `(${p.role})` : '';
                const dept = p.department ? `[${p.department}]` : '';
                html += `<li>${name} ${role} ${dept}</li>`;
            });
            html += '</ul></div>';
        }
        html += '</div>';
    }

    // 논의사항
    if ((data.discussions && data.discussions.length > 0) || editable) {
        html += '<div class="result-item">';
        html += '<label>논의사항</label>';
        if (editable) {
            let discussionText = '';
            data.discussions?.forEach((d, idx) => {
                if (idx > 0) discussionText += '\n---\n';
                discussionText += `주제: ${d.topic || ''}`;
                if (d.content) discussionText += `\n내용: ${d.content}`;
            });
            html += `<textarea class="value-edit" id="edit-discussions" rows="10">${discussionText}</textarea>`;
            html += '<small class="hint">각 항목은 "---" 로 구분, 주제: xxx\\n내용: xxx 형식</small>';
        } else {
            html += '<div class="value"><ul>';
            data.discussions?.forEach(d => {
                const topic = d.topic || '';
                const content = d.content ? `<br><small>${d.content}</small>` : '';
                html += `<li><strong>${topic}</strong>${content}</li>`;
            });
            html += '</ul></div>';
        }
        html += '</div>';
    }

    // 결정사항
    if ((data.decisions && data.decisions.length > 0) || editable) {
        html += '<div class="result-item">';
        html += '<label>결정사항</label>';
        if (editable) {
            let decisionText = '';
            data.decisions?.forEach((d, idx) => {
                if (idx > 0) decisionText += '\n---\n';
                decisionText += `결정: ${d.decision || ''}`;
                if (d.reason) decisionText += `\n이유: ${d.reason}`;
            });
            html += `<textarea class="value-edit" id="edit-decisions" rows="8">${decisionText}</textarea>`;
            html += '<small class="hint">각 항목은 "---" 로 구분, 결정: xxx\\n이유: xxx 형식</small>';
        } else {
            html += '<div class="value"><ul>';
            data.decisions?.forEach(d => {
                const decision = d.decision || '';
                const reason = d.reason ? `<br><small>이유: ${d.reason}</small>` : '';
                html += `<li><strong>${decision}</strong>${reason}</li>`;
            });
            html += '</ul></div>';
        }
        html += '</div>';
    }

    // 액션 아이템
    if ((data.actionItems && data.actionItems.length > 0) || editable) {
        html += '<div class="result-item">';
        html += '<label>액션 아이템</label>';
        if (editable) {
            let actionText = '';
            data.actionItems?.forEach((item, idx) => {
                if (idx > 0) actionText += '\n---\n';
                actionText += `업무: ${item.description || ''}`;
                if (item.assignee) actionText += `\n담당: ${item.assignee}`;
                if (item.dueDate) actionText += `\n기한: ${item.dueDate}`;
            });
            html += `<textarea class="value-edit" id="edit-actionItems" rows="10">${actionText}</textarea>`;
            html += '<small class="hint">각 항목은 "---" 로 구분, 업무: xxx\\n담당: xxx\\n기한: xxx 형식</small>';
        } else {
            html += '<div class="value"><ul>';
            data.actionItems?.forEach(item => {
                const desc = item.description || '';
                const assignee = item.assignee ? `담당: ${item.assignee}` : '';
                const dueDate = item.dueDate ? `기한: ${item.dueDate}` : '';
                html += `<li><strong>${desc}</strong><br><small>${assignee} ${dueDate}</small></li>`;
            });
            html += '</ul></div>';
        }
        html += '</div>';
    }

    resultDiv.innerHTML = html;
    resultDiv.classList.add('show');
}

// 편집 모드 토글
function toggleEdit() {
    isEditing = true;
    document.getElementById('editBtn').style.display = 'none';
    document.getElementById('saveBtn').style.display = 'inline-block';
    if (currentMeetingData) {
        displayAnalysisResult(currentMeetingData, true);
    }
}

// 수정 내용 저장
function saveEdit() {
    try {
        // 회의 제목
        const meetingTitleEl = document.getElementById('edit-meetingTitle');
        if (meetingTitleEl) currentMeetingData.meetingTitle = meetingTitleEl.value.trim();

        // 회의 목적
        const purposeEl = document.getElementById('edit-purpose');
        if (purposeEl) currentMeetingData.purpose = purposeEl.value.trim();

        // 참석자 (텍스트 -> JSON 변환)
        const participantsEl = document.getElementById('edit-participants');
        if (participantsEl && participantsEl.value.trim()) {
            const lines = participantsEl.value.trim().split('\n');
            currentMeetingData.participants = lines.map(line => {
                const parts = line.split('|').map(p => p.trim());
                return {
                    name: parts[0] || '',
                    role: parts[1] || '',
                    department: parts[2] || ''
                };
            }).filter(p => p.name);
        }

        // 논의사항 (텍스트 -> JSON 변환)
        const discussionsEl = document.getElementById('edit-discussions');
        if (discussionsEl && discussionsEl.value.trim()) {
            const blocks = discussionsEl.value.trim().split('\n---\n');
            currentMeetingData.discussions = blocks.map(block => {
                const lines = block.split('\n');
                let topic = '';
                let content = '';
                lines.forEach(line => {
                    if (line.startsWith('주제:')) topic = line.substring(3).trim();
                    else if (line.startsWith('내용:')) content = line.substring(3).trim();
                });
                return { topic, content };
            }).filter(d => d.topic);
        }

        // 결정사항 (텍스트 -> JSON 변환)
        const decisionsEl = document.getElementById('edit-decisions');
        if (decisionsEl && decisionsEl.value.trim()) {
            const blocks = decisionsEl.value.trim().split('\n---\n');
            currentMeetingData.decisions = blocks.map(block => {
                const lines = block.split('\n');
                let decision = '';
                let reason = '';
                lines.forEach(line => {
                    if (line.startsWith('결정:')) decision = line.substring(3).trim();
                    else if (line.startsWith('이유:')) reason = line.substring(3).trim();
                });
                return { decision, reason };
            }).filter(d => d.decision);
        }

        // 액션 아이템 (텍스트 -> JSON 변환)
        const actionItemsEl = document.getElementById('edit-actionItems');
        if (actionItemsEl && actionItemsEl.value.trim()) {
            const blocks = actionItemsEl.value.trim().split('\n---\n');
            currentMeetingData.actionItems = blocks.map(block => {
                const lines = block.split('\n');
                let description = '';
                let assignee = '';
                let dueDate = '';
                lines.forEach(line => {
                    if (line.startsWith('업무:')) description = line.substring(3).trim();
                    else if (line.startsWith('담당:')) assignee = line.substring(3).trim();
                    else if (line.startsWith('기한:')) dueDate = line.substring(3).trim();
                });
                return { description, assignee, dueDate };
            }).filter(a => a.description);
        }

        // 수정된 데이터로 다시 표시 (읽기 전용)
        isEditing = false;
        document.getElementById('editBtn').style.display = 'inline-block';
        document.getElementById('saveBtn').style.display = 'none';
        displayAnalysisResult(currentMeetingData, false);

        showStatus('analyzeStatus', '수정이 저장되었습니다.', 'success');
    } catch (error) {
        alert('입력 형식 오류: 확인 후 다시 시도해주세요.\n' + error.message);
    }
}

// PPT 생성
async function generatePPT() {
    if (!currentFileId) {
        showStatus('generateStatus', '먼저 분석을 실행해주세요.', 'error');
        return;
    }

    showStatus('generateStatus', 'PPT 생성 중...', 'loading');
    setButtonDisabled('generateBtn', true);

    try {
        // 수정된 데이터가 있으면 먼저 저장
        if (currentMeetingData) {
            await fetch(`${API_BASE}/api/save-edit?file_id=${currentFileId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(currentMeetingData)
            });
        }

        // PPT 생성
        const response = await fetch(`${API_BASE}/api/generate?file_id=${currentFileId}`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showStatus('generateStatus', 'PPT 생성 완료! 다운로드 버튼을 눌러주세요.', 'success');
            setButtonDisabled('downloadBtn', false);
        } else {
            showStatus('generateStatus', data.detail || 'PPT 생성 실패', 'error');
        }
    } catch (error) {
        showStatus('generateStatus', `PPT 생성 실패: ${error.message}`, 'error');
    }

    setButtonDisabled('generateBtn', false);
}

// PPT 다운로드
async function downloadPPT() {
    if (!currentFileId) {
        alert('다운로드할 PPT 파일이 없습니다.');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/download/${currentFileId}`);

        if (!response.ok) {
            throw new Error('다운로드 실패: ' + response.statusText);
        }

        // blob 으로 받아서 다운로드
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);

        // 다운로드 링크 생성 및 클릭
        const link = document.createElement('a');
        link.href = url;

        // Content-Disposition 에서 파일명 추출 시도
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'meeting_presentation.pptx';

        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
            if (filenameMatch && filenameMatch[1]) {
                filename = filenameMatch[1].replace(/['"]/g, '');
            }
        }

        link.download = filename;
        document.body.appendChild(link);
        link.click();

        // 정리
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);

        showStatus('generateStatus', '다운로드 시작되었습니다.', 'success');
    } catch (error) {
        showStatus('generateStatus', `다운로드 실패: ${error.message}`, 'error');
        alert('다운로드 실패: ' + error.message);
    }
}

// 상태 확인 (polling)
async function checkStatus() {
    if (!currentFileId) return;

    try {
        const response = await fetch(`${API_BASE}/api/status/${currentFileId}`);
        const data = await response.json();

        if (data.success && data.analyzed && data.generated) {
            setButtonDisabled('downloadBtn', false);
        }
    } catch (error) {
        console.error('Status check failed:', error);
    }
}

// 상태 메시지 표시
function showStatus(elementId, message, type) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.className = 'status ' + type;
}

// 버튼 비활성화
function setButtonDisabled(buttonId, disabled) {
    const button = document.getElementById(buttonId);
    if (button) {
        button.disabled = disabled;
    }
}

// 페이지 로드 시 상태 확인
document.addEventListener('DOMContentLoaded', function() {
    console.log('AI 회의록 시스템 ready');

    // 모델 카드 선택 시 숨겨진 input 값 동기화
    const modelCards = document.querySelectorAll('.model-card input[type="radio"]');
    const hiddenSelect = document.getElementById('modelSelect');

    modelCards.forEach(radio => {
        radio.addEventListener('change', function() {
            if (this.checked && hiddenSelect) {
                hiddenSelect.value = this.value;
                console.log('Selected model:', this.value);
            }
        });
    });

    // 참고파일 업로드 처리
    const referenceFileInput = document.getElementById('referenceFile');
    if (referenceFileInput) {
        referenceFileInput.addEventListener('change', handleReferenceUpload);
    }

    // 참고파일 목록 로드
    loadReferenceFiles();

    // 오타 수정 목록 로드
    loadCorrections();
});

// ==================== 참고폴더 (RAG) 기능 ====================

// 참고파일 업로드
async function handleReferenceUpload(e) {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    showStatus('ragStatus', '참고파일 업로드 중...', 'loading');

    let successCount = 0;

    for (let file of files) {
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`${API_BASE}/api/reference/upload`, {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                successCount++;
                console.log('[참고파일] 업로드 완료:', file.name);
            } else {
                showStatus('ragStatus', `${file.name}: 업로드 실패`, 'error');
            }
        } catch (error) {
            showStatus('ragStatus', `${file.name}: ${error.message}`, 'error');
        }
    }

    if (successCount > 0) {
        showStatus('ragStatus', `업로드 완료: ${successCount}개`, 'success');
    }

    // 입력 초기화
    e.target.value = '';

    // ✅ 무조건 목록 새로고침 (업로드 후 즉시 표시)
    setTimeout(() => loadReferenceFiles(), 100);
}

// 참고파일 목록 로드
async function loadReferenceFiles() {
    try {
        const response = await fetch(`${API_BASE}/api/reference/files`);
        const data = await response.json();

        if (data.success) {
            displayReferenceFiles(data.files || []);
            const countEl = document.getElementById('referenceCount');
            if (countEl) countEl.textContent = data.count || 0;
            console.log('[참고파일] 목록 로드:', data.count, '개');
        } else {
            console.error('[참고파일] 목록 로드 실패:', data);
            // 실패 시에도 빈 목록 표시
            displayReferenceFiles([]);
        }
    } catch (error) {
        console.error('[참고파일] 목록 로드 예외:', error);
        displayReferenceFiles([]);
    }
}

// 참고파일 목록 표시
function displayReferenceFiles(files) {
    const fileList = document.getElementById('referenceFileList');

    if (!files || files.length === 0) {
        fileList.innerHTML = '<p class="empty-message">등록된 참고파일이 없습니다.</p>';
        return;
    }

    let html = '';
    files.forEach(file => {
        const fileSize = formatFileSize(file.size);
        const fileIcon = getFileIcon(file.extension);
        html += `
            <div class="file-list-item">
                <div class="file-info">
                    <span class="file-icon">${fileIcon}</span>
                    <div>
                        <div class="file-name-text">${escapeHtml(file.name)}</div>
                        <span class="file-size">${fileSize}</span>
                    </div>
                </div>
                <button class="delete-file-btn" onclick="deleteReferenceFile('${escapeHtml(file.name)}')">삭제</button>
            </div>
        `;
    });

    fileList.innerHTML = html;
}

// 파일 아이콘 반환
function getFileIcon(ext) {
    const icons = {
        '.txt': '📄',
        '.md': '📝',
        '.pdf': '📕',
        '.docx': '📘',
        '.pptx': '📊',
        '.xlsx': '📗',
        '.json': '📋',
        '.csv': '📊'
    };
    return icons[ext] || '📁';
}

// 파일 크기 포맷팅
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// 참고파일 삭제
async function deleteReferenceFile(filename) {
    if (!confirm(`"${filename}" 파일을 삭제하시겠습니까?`)) return;

    try {
        const response = await fetch(`${API_BASE}/api/reference/files/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showStatus('ragStatus', `${filename} 파일 삭제 완료`, 'success');
            // ✅ 즉시 목록 갱신 (await 추가)
            await loadReferenceFiles();
        } else {
            showStatus('ragStatus', `삭제 실패: ${data.detail || '알 수 없는 오류'}`, 'error');
        }
    } catch (error) {
        showStatus('ragStatus', `삭제 실패: ${error.message}`, 'error');
        console.error('[참고파일 삭제 오류]', error);
    }
}

// 참고폴더 인덱스 새로고침
async function refreshRagIndex() {
    showStatus('ragStatus', '검색 준비 다시하는 중...', 'loading');

    try {
        const response = await fetch(`${API_BASE}/api/reference/refresh`, {
            method: 'POST'
        });

        const data = await response.json();

        if (data.success) {
            showStatus('ragStatus', '검색 준비 완료! 이제 검색이 가능합니다.', 'success');
        } else {
            showStatus('ragStatus', `실패: ${data.detail || '알 수 없는 오류'}`, 'error');
        }
    } catch (error) {
        showStatus('ragStatus', `실패: ${error.message}`, 'error');
    }
}

// 참고파일 검색
async function searchReference() {
    const query = document.getElementById('ragSearchInput').value.trim();
    if (!query) {
        alert('검색어를 입력해주세요.');
        return;
    }

    const resultsDiv = document.getElementById('ragSearchResults');
    resultsDiv.innerHTML = '<p class="loading">검색 중...</p>';
    resultsDiv.classList.add('show');

    try {
        const response = await fetch(`${API_BASE}/api/reference/search?query=${encodeURIComponent(query)}&top_k=5`);
        const data = await response.json();

        if (data.success && data.results && data.results.length > 0) {
            displaySearchResults(data.results);
        } else {
            resultsDiv.innerHTML = '<p class="empty-message">검색 결과가 없습니다.</p>';
        }
    } catch (error) {
        resultsDiv.innerHTML = `<p class="error">검색 실패: ${error.message}</p>`;
    }
}

// 검색 결과 표시
function displaySearchResults(results) {
    const resultsDiv = document.getElementById('ragSearchResults');

    let html = '';
    results.forEach(result => {
        const snippet = result.content.length > 200 ? result.content.substring(0, 200) + '...' : result.content;
        html += `
            <div class="search-result-item">
                <div class="search-result-source">
                    ${escapeHtml(result.source)}
                    <span class="search-result-score">유사도: ${(result.score * 100).toFixed(1)}%</span>
                </div>
                <div class="search-result-content">${escapeHtml(snippet)}</div>
            </div>
        `;
    });

    resultsDiv.innerHTML = html;
}

// ==================== 오타 수정 관리 기능 ====================

// 오타 수정 등록
async function addCorrection() {
    const wrongWord = document.getElementById('wrongWordInput').value.trim();
    const correctWord = document.getElementById('correctWordInput').value.trim();

    if (!wrongWord || !correctWord) {
        showStatus('correctionStatus', '틀리는 단어와 올바른 단어를 모두 입력해주세요.', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/api/corrections`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ wrong_word: wrongWord, correct_word: correctWord })
        });

        const data = await response.json();

        if (data.success) {
            showStatus('correctionStatus', data.message, 'success');
            document.getElementById('wrongWordInput').value = '';
            document.getElementById('correctWordInput').value = '';
            loadCorrections();
        } else {
            showStatus('correctionStatus', data.detail || '등록 실패', 'error');
        }
    } catch (error) {
        showStatus('correctionStatus', `등록 실패: ${error.message}`, 'error');
    }
}

// 오타 수정 목록 로드
async function loadCorrections() {
    try {
        const response = await fetch(`${API_BASE}/api/corrections`);
        const data = await response.json();

        if (data.success) {
            displayCorrections(data.corrections);
            document.getElementById('correctionCount').textContent = data.count;
        }
    } catch (error) {
        console.error('오타 수정 목록 로드 실패:', error);
    }
}

// 오타 수정 목록 표시
function displayCorrections(corrections) {
    const listDiv = document.getElementById('correctionList');

    if (!corrections || Object.keys(corrections).length === 0) {
        listDiv.innerHTML = '<p class="empty-message">등록된 오타 수정이 없습니다.</p>';
        return;
    }

    let html = '';
    Object.entries(corrections).forEach(([wrong, correct]) => {
        html += `
            <div class="correction-item">
                <div class="correction-word">
                    <span class="correction-wrong">${escapeHtml(wrong)}</span>
                    <span class="correction-arrow">→</span>
                    <span class="correction-correct">${escapeHtml(correct)}</span>
                </div>
                <button class="correction-delete-btn" onclick="deleteCorrection('${escapeHtml(wrong)}')">삭제</button>
            </div>
        `;
    });

    listDiv.innerHTML = html;
}

// 오타 수정 삭제
async function deleteCorrection(wrongWord) {
    if (!confirm(`'${wrongWord}' 오타 수정을 삭제하시겠습니까?`)) return;

    try {
        const response = await fetch(`${API_BASE}/api/corrections/${encodeURIComponent(wrongWord)}`, {
            method: 'DELETE'
        });

        const data = await response.json();

        if (data.success) {
            showStatus('correctionStatus', data.message, 'success');
            loadCorrections();
        } else {
            showStatus('correctionStatus', `삭제 실패: ${data.detail || '알 수 없는 오류'}`, 'error');
        }
    } catch (error) {
        showStatus('correctionStatus', `삭제 실패: ${error.message}`, 'error');
    }
}
