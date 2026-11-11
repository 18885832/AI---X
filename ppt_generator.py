# -*- coding: utf-8 -*-
"""
PPT 생성 모듈
회의록 양식 기반 세로 방향 PPT 생성
"""
from pptx import Presentation
from pptx.util import Inches, Pt
from datetime import datetime
import os
from config import REPORTS_DIR, FONT_NAME

def set_font(run, size, bold=False):
    """폰트 설정"""
    run.font.size = Pt(size)
    run.font.bold = bold
    try:
        run.font.name = FONT_NAME
        run._element.rPr.rFonts.set(
            '{http://schemas.openxmlformats.org/drawingml/2006/main}eastAsia',
            FONT_NAME
        )
    except:
        pass

def create_meeting_ppt(meeting_data, output_filename=None):
    """
    회의록 PPT 생성 (세로 방향 A4 비율)

    Args:
        meeting_data: 분석된 회의 데이터
        output_filename: 출력 파일명 (None 일 경우 자동 생성)

    Returns:
        생성된 PPT 파일 경로
    """
    # PPT 생성 (세로 방향 - A4 용지 비율)
    prs = Presentation()
    prs.slide_width = Inches(8.27)   # A4 폭
    prs.slide_height = Inches(11.69) # A4 높이

    # Blank 레이아웃 사용
    slide_layout = prs.slide_layouts[5]
    slide = prs.slides.add_slide(slide_layout)

    title = meeting_data.get('meetingTitle', '회의록')
    date_str = meeting_data.get('meetingDate', datetime.now().strftime('%Y-%m-%d'))
    time_str = meeting_data.get('meetingTime', '10:00~11:00')
    author = meeting_data.get('author', '시스템 생성')
    participants = meeting_data.get('participants', [])
    purpose = meeting_data.get('purpose', '')
    discussions = meeting_data.get('discussions', [])
    decisions = meeting_data.get('decisions', [])
    action_items = meeting_data.get('actionItems', [])

    # 제목 (상단 중앙)
    title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(7.3), Inches(0.9))
    title_tf = title_box.text_frame
    title_p = title_tf.paragraphs[0]
    title_p.text = title
    title_p.alignment = 1  # Center
    set_font(title_p.runs[0], 26, True)

    # 날짜, 시간, 작성자
    meta_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.15), Inches(7.3), Inches(0.5))
    meta_tf = meta_box.text_frame
    meta_p = meta_tf.paragraphs[0]
    meta_p.text = f"{date_str}   {time_str}"
    p2 = meta_tf.add_paragraph()
    p2.text = f"작성자: {author}"
    for p in meta_tf.paragraphs:
        for run in p.runs:
            set_font(run, 10)

    # 참석자 (데이터 형식 안전 처리)
    def normalize_participant(p):
        """참석자 데이터를 딕셔너리 형식으로 정규화"""
        if isinstance(p, dict):
            return {
                'name': p.get('name', ''),
                'role': p.get('role', ''),
                'department': p.get('department', '')
            }
        elif isinstance(p, str):
            # 문자열인 경우 (규칙 기반 추출 시 발생)
            return {'name': p.strip(), 'role': '', 'department': ''}
        return {'name': '', 'role': '', 'department': ''}

    # 참석자 리스트 정규화
    normalized_participants = [normalize_participant(p) for p in participants]

    hms_participants = [p for p in normalized_participants if '현대제철' in p.get('department', '') or not p.get('department')]
    partner_participants = [p for p in normalized_participants if 'IT 운영팀' in p.get('department', '') or '노바텍' in p.get('department', '') or '지니시스템' in p.get('department', '')]

    participants_text = "ㆍ현대제철 : " + ", ".join(
        [f"{p['name']} ({p.get('role', '')})" for p in hms_participants[:4] if p.get('name')]
    )
    partners_text = "ㆍIT 운영팀 : " + ", ".join(
        [f"{p['name']} ({p.get('department', '').split('(')[-1].rstrip(')') if '(' in p.get('department', '') else p['name']})" for p in partner_participants if p.get('name')]
    )

    # 참석자가 없으면 participants_text 도 비워둠
    if not normalized_participants:
        participants_text = ""
        partners_text = ""

    if participants_text:
        participants_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.6), Inches(7.3), Inches(0.4))
        participants_tf = participants_box.text_frame
        participants_p = participants_tf.paragraphs[0]
        participants_p.text = participants_text
        for run in participants_p.runs:
            set_font(run, 9.5)

        if partners_text:
            partners_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.85), Inches(7.3), Inches(0.4))
            partners_tf = partners_box.text_frame
            partners_p = partners_tf.paragraphs[0]
            partners_p.text = partners_text
            for run in participants_p.runs:
                set_font(run, 9.5)

    # [회의내용] 제목
    content_title_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.1), Inches(1.8), Inches(0.35))
    content_title_tf = content_title_box.text_frame
    content_title_p = content_title_tf.paragraphs[0]
    content_title_p.text = "[회의내용]"
    set_font(content_title_p.runs[0], 13, True)

    # 본문 내용 구성
    body_lines = []
    short_title = title.replace(" 폐기 회의", "").replace("회의", "").strip()

    body_lines.append(f'■ "{short_title}" 건')
    body_lines.append('')

    # 1. 목적
    if purpose:
        body_lines.append('1. 목적')
        body_lines.append(f'   {purpose}')
        body_lines.append('')

    # 2. 현황/논의사항
    if discussions:
        body_lines.append('2. 논의사항')
        for i, d in enumerate(discussions, 1):
            if isinstance(d, dict):
                topic = d.get('topic', '')
                content = d.get('content', '')
            else:
                topic = str(d) if d else ''
                content = ''
            body_lines.append(f'   {i}) {topic}')
            if content:
                for line in content.split('\n'):
                    if line.strip():
                        body_lines.append(f'      {line}')
        body_lines.append('')

    # 3. 결정사항
    if decisions:
        body_lines.append('3. 결정사항')
        for i, d in enumerate(decisions, 1):
            if isinstance(d, dict):
                decision = d.get('decision', '')
                reason = d.get('reason', '')
            else:
                decision = str(d) if d else ''
                reason = ''
            body_lines.append(f'   {i}) {decision}')
            if reason:
                body_lines.append(f'      이유: {reason}')
        body_lines.append('')

    # 4. 액션 아이템
    if action_items:
        body_lines.append('4. 액션 아이템')
        for i, item in enumerate(action_items, 1):
            if isinstance(item, dict):
                desc = item.get('description', '')
                assignee = item.get('assignee', '')
                due_date = item.get('dueDate', '')
            else:
                desc = str(item) if item else ''
                assignee = ''
                due_date = ''
            body_lines.append(f'   {i}) {desc}')
            body_lines.append(f'      담당: {assignee} / 기한: {due_date}')
        body_lines.append('')

    body_lines.append('- 끝 -')

    # 본문 텍스트 박스
    body_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.35), Inches(7.3), Inches(8.9))
    body_tf = body_box.text_frame
    body_tf.word_wrap = True

    first_para = True
    for line in body_lines:
        if first_para:
            p = body_tf.paragraphs[0]
            first_para = False
        else:
            p = body_tf.add_paragraph()

        p.text = line
        p.space_after = Pt(4)

        for run in p.runs:
            if line.startswith('■') or line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.startswith('4.'):
                set_font(run, 11.5, True)
            elif line.startswith('      ') and not line.startswith('      {'):
                set_font(run, 10)
            else:
                set_font(run, 10)

    # 파일 저장
    os.makedirs(REPORTS_DIR, exist_ok=True)

    if output_filename is None:
        base_name = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_filename = f"{base_name}_회의록.pptx"

    output_path = os.path.join(REPORTS_DIR, output_filename)
    prs.save(output_path)

    print(f"[PPT] 저장 완료: {output_path}")
    return output_path
