import streamlit as st
import requests
import re
import io
import html
import zipfile

# ==========================================
# 0. 다국어 텍스트 정의 (사전)
# ==========================================
TEXTS = {
    "한국어": {
        "app_title": "🎬 VOD 자막 다국어 일괄 처리 & 에디터",
        "tab1": "🌐 1. 일괄 다운로드 & 전처리",
        "tab2": "📁 2. 수동 VTT -> SRT",
        "tab3": "🔙 3. 최종 SRT -> VTT",
        "tab4": "✂️ 4. 구간 자막 덮어쓰기",
        "tab5": "🕐 5. 전체 자막 시프트",

        # 탭 1 (다운로드)
        "t1_sub": "MP4 주소로 다국어 자막 복수 다운로드",
        "t1_info": "➕ 버튼을 눌러 작업을 원하는 만큼 추가하세요. 언어별 자막을 설정한 파일명 규칙으로 한 번에 묶어줍니다.",
        "t1_link_title": "##### 🔗 다운로드 링크 및 파일명 설정",
        "t1_url_label": "MP4 URL #{num}",
        "t1_url_ph": "https://.../stream1.mp4",
        "t1_prefix_label": "파일명 구조 #{num}",
        "t1_prefix_ph": "예: 20260000_ART_day{num}",
        "t1_btn_add": "➕ 링크 입력칸 추가",
        
        "t1_opt_title": "##### 🧹 옵션: 테스트 자막 정리 (다운로드 시 자동 적용)",
        "t1_chk_clean": "초반 자막 지우기 기능 사용",
        "t1_min_label": "기준 시간 (분 단위):",
        "t1_radio_label": "처리 방식 선택:",
        "t1_radio_1": "완전 삭제 (기본값)",
        "t1_radio_2": "점(.)으로 남기기 (0.1초 노출)",
        
        "t1_lang_label": "다운로드할 언어 선택",
        "t1_team_share_label": "자막팀 공유 폴더에 포함할 언어 (사람이 직접 작업하는 언어)",
        "t1_btn_run": "🚀 일괄 다운로드 및 변환 실행",
        
        "t1_err_nolink": "최소 1개 이상의 URL과 파일명을 정확히 입력해주세요.",
        "t1_sp_loading": "서버에서 자막을 받고 폴더별로 자동 분류 중입니다...",
        "t1_msg_success": "✅ [{prefix}] {lang} 처리 완료",
        "t1_msg_err_fmt": "⚠️ [{prefix}] {lang} 형식 오류: {msg}",
        "t1_msg_err_sys": "❌ [{prefix}] {lang} 처리 중 에러: {e}",
        "t1_success_all": "🎉 총 {cnt}개의 파일이 성공적으로 처리되었습니다!",
        "t1_btn_download_zip": "📦 완성된 전체 패키지 다운로드 (.zip)",
        "t1_share_folder": "자막팀공유",

        # 탭 1 + 탭 5 공용: 전체 시프트
        "shift_sign_lbl": "방향",
        "shift_sign_plus": "➕ 미루기 (뒤로 / 시간 증가)",
        "shift_sign_minus": "➖ 당기기 (앞으로 / 시간 감소)",
        "shift_offset_lbl": "이동 시간 (HH:MM:SS)",
        "t1_shift_title": "##### ⏱️ 옵션: 전체 자막 시프트 (다운로드 시 자동 적용)",
        "t1_chk_shift": "전체 타임코드 시프트 사용",

        # 탭 2 & 3 (수동 변환)
        "t2_sub": "📁 로컬 VTT 파일을 SRT로 수동 변환",
        "t2_upload": "VTT 파일 업로드",
        "t2_btn_dl": "⬇️ {name} 다운로드",
        "t2_chk_lint": "업로드 시 라인별 형식 검사",
        "t2_fix_title": "##### 일괄 수정 (선택한 항목만 적용 후 변환·다운로드)",
        
        "t3_sub": "🔙 프리미어 검수 완료된 SRT를 VOD 업로드용 VTT로 변환",
        "t3_upload": "수정 완료된 SRT 업로드",
        "t3_btn_dl": "⬇️ {name} 다운로드",
        "t3_chk_lint": "업로드 시 라인별 형식 검사",
        "t3_fix_title": "##### 일괄 수정 (선택한 항목만 적용 후 변환·다운로드)",

        "fix_escape_amp": "'&' → &amp; 이스케이프",
        "fix_strip_tags": "VTT/HTML 태그 제거 (텍스트 유지)",
        "fix_strip_bad_tags": "잘못된 <> 태그 제거",
        "fix_remove_cue_id": "VTT cue ID 줄 삭제",
        "fix_strip_vtt_settings": "VTT 타임코드 정렬·위치 설정 삭제",
        "fix_tc_separator": "타임코드 밀리초 구분자 수정 (VTT: 점 / SRT: 쉼표)",
        "fix_arrow_text": "텍스트 내 '-->' → '→' 치환",
        "fix_remove_orphan": "타임코드 없는 블록 삭제",
        "fix_remove_empty": "빈 자막 cue 삭제",
        "btn_fix_dl": "⬇️ 선택 수정 적용 & {name} 다운로드",
        "btn_fix_zip": "⬇️ 선택 수정 적용 & ZIP 다운로드",
        "val_fix_title": "##### 자동 수정 (선택 항목만 적용)",
        "val_fix_timestamp": "타임코드 형식 수정",
        "val_fix_vtt_extra": "VTT cue ID·위치 설정 제거",
        "val_fix_entities": "& 이스케이프",
        "val_fix_markup": "태그 제거 · '-->' 치환",
        "val_fix_remove_invalid": "빈 cue·타임코드 없는 블록 삭제",
        "val_legend": "🔴 **수정 필요** = 형식 위반, 변환·재생 오류 가능 · 🔵 **참고** = VTT/SRT 규격상 허용, 변환 시에만 영향",
        "val_required_header": "🔴 수정 필요",
        "val_optional_header": "🔵 참고 (수정 안 해도 됨)",
        "val_tag_required": "수정 필요",
        "val_tag_optional": "참고",
        "val_has_required": "수정 필요 항목이 있습니다. 아래 자동 수정을 켜거나 원본을 고친 뒤 다운로드하세요.",
        "val_fix_required_title": "##### 🔴 수정 필요 항목 자동 수정",
        "val_fix_optional_title": "##### 🔵 참고 항목 자동 수정 (선택)",
        "val_no_autofix": "자동 수정 가능한 검사 항목이 없습니다.",
        "t4_sub": "✂️ SRT 특정 구간 밀어내기 & 새 자막 삽입",
        "t4_info": "지정한 시간 사이에 있는 자막을 비우고, 새로 입력한 텍스트들을 엔터(줄바꿈) 기준으로 자동 분배하여 넣습니다. (나머지 뒤쪽 자막들의 번호와 시간은 밀리지 않고 유지됩니다)",
        "t4_upload": "수정할 원본 SRT 파일 업로드",
        "t4_start_lbl": "교체 시작 시간 (예: 10:00 또는 00:10:00)",
        "t4_end_lbl": "교체 종료 시간 (예: 11:00 또는 00:11:00)",
        "t4_text_lbl": "새로 넣을 자막 텍스트 입력 (엔터키를 기준으로 분할됩니다)",
        "t4_text_ph": "안녕하세요.\n반갑습니다.\n이 줄바꿈 그대로 자막이 나뉩니다.",
        "t4_btn_run": "✨ 구간 교체 적용하고 다운로드",
        "t4_err_time": "시간 형식을 다시 확인해주세요. (예: 10:00 또는 00:10:00,000)",
        "t4_success": "✅ 자막 교체 및 인덱스 정렬 완료!",
        "t4_err_input": "원본 SRT 파일, 시작/종료 시간, 추가할 자막을 모두 입력해주세요.",

        # 탭 4 일괄 처리 모드
        "t4_mode_lbl": "처리 모드",
        "t4_mode_single": "단일 파일 (기존)",
        "t4_mode_batch": "일괄 처리 (기준 언어 + 자동번역 언어)",
        "t4_batch_info": "기준 언어 1개와 다른 언어들을 함께 올린 후, 동일한 시간 범위에 대해 언어별 번역문을 각각 입력하세요. 파일명 마지막 `_언어코드.srt` 패턴으로 언어를 자동 감지합니다 (예: `..._en.srt`).",
        "t4_ref_upload": "기준 언어 SRT 업로드 (1개)",
        "t4_target_upload": "자동번역 언어 SRT 업로드 (여러 개)",
        "t4_lang_text_lbl": "[{lang}] {filename} - 새 자막 텍스트 (줄바꿈으로 분할)",
        "t4_btn_batch_run": "✨ 일괄 적용 & ZIP 다운로드",
        "t4_batch_success": "✅ {cnt}개 파일 처리 완료",
        "t4_err_batch_nofile": "최소 한 개 이상의 SRT 파일을 업로드해주세요.",
        "t4_err_batch_notext": "각 언어 SRT 파일마다 새 자막 텍스트를 입력해야 합니다.",

        # 탭 5 (전체 시프트)
        "t5_sub": "🕐 자막 전체 타임코드를 한 번에 당기거나 미루기",
        "t5_info": "SRT/VTT 파일을 올린 뒤 방향(+/-)과 이동 시간을 정하면 전체 자막이 한꺼번에 이동합니다. 당겨서 0초 이전으로 밀려난 자막은 삭제됩니다. 업로드한 파일 포맷 그대로 다운로드됩니다.",
        "t5_upload": "시프트할 SRT/VTT 파일 업로드 (여러 개 가능)",
        "t5_btn_run": "🚀 시프트 적용 & 다운로드",
        "t5_success": "✅ {cnt}개 파일 시프트 완료 ({sign}{offset})",
        "t5_err_nofile": "최소 한 개 이상의 자막 파일을 업로드해주세요.",
        "t5_err_offset": "이동 시간을 HH:MM:SS 형식으로 0보다 크게 입력해주세요. (예: 01:00:00)",

        # 검증 (SRT/VTT validator 표준 항목)
        "err_vtt_header": "WEBVTT 헤더 누락",
        "err_tc": "타임코드(-->) 없음",
        "val_title": "##### 검사 결과",
        "val_ok": "문제 없음",
        "val_empty_file": "빈 파일",
        "val_missing_file_header": "WEBVTT 헤더 없음",
        "val_no_timestamp": "타임코드 없음",
        "val_bad_timestamp": "타임코드 형식 오류",
        "val_bad_timestamp_order": "종료 시간이 시작보다 앞섬",
        "val_bad_index": "자막 번호 오류",
        "val_bad_block": "cue 블록 구조 오류",
        "val_bad_cue_id": "cue identifier 줄 (VTT 정상)",
        "val_bad_cue_settings": "cue 설정 align 등 (VTT 정상)",
        "val_bad_markup": "잘못된 태그 (일부 플레이어)",
        "val_unescaped_entity": "& 미이스케이프 (HTML 플레이어)",
        "val_empty_text": "자막 텍스트 없음 (빈 cue)",
        "val_timestamp_conflict": "텍스트에 '-->' 포함 (파싱 깨짐)",
        "val_expander_none": "{lang} — 문제 없음",
        "val_expander_count": "{lang} — {total}건 (수정 {req} / 참고 {opt})",
        "val_legend": "🔴 **수정 필요** = 형식 위반, 변환·재생 오류 가능 · 🔵 **참고** = 규격상 허용, 변환 시에만 영향",
        "val_required_header": "🔴 수정 필요",
        "val_optional_header": "🔵 참고 (수정 안 해도 됨)",
        "val_tag_required": "수정 필요",
        "val_tag_optional": "참고",
        "val_has_required": "수정 필요 항목이 있습니다. 아래 자동 수정을 켜거나 원본을 고친 뒤 다운로드하세요.",
        "val_fix_required_title": "##### 🔴 수정 필요 항목 자동 수정",
        "val_fix_optional_title": "##### 🔵 참고 항목 자동 수정 (선택)",
    },
    "English": {
        "app_title": "🎬 VOD Subtitle Batch Processor & Editor",
        "tab1": "🌐 1. Batch Download & Pre-process",
        "tab2": "📁 2. Manual VTT -> SRT",
        "tab3": "🔙 3. Final SRT -> VTT",
        "tab4": "✂️ 4. Override Subtitle Section",
        "tab5": "🕐 5. Global Time Shift",

        # Tab 1 (Download)
        "t1_sub": "Batch Download Multilingual Subtitles via MP4 URLs",
        "t1_info": "Click ➕ to add multiple tasks. Subtitles for each language will be bundled automatically based on the filename prefix.",
        "t1_link_title": "##### 🔗 Download Links & Filename Setup",
        "t1_url_label": "MP4 URL #{num}",
        "t1_url_ph": "https://.../stream1.mp4",
        "t1_prefix_label": "Filename Prefix #{num}",
        "t1_prefix_ph": "e.g., 20260000_ART_day{num}",
        "t1_btn_add": "➕ Add Link Input",
        
        "t1_opt_title": "##### 🧹 Option: Clean Up Test Subtitles (Applied on Download)",
        "t1_chk_clean": "Enable early subtitles cleanup",
        "t1_min_label": "Target duration (in minutes):",
        "t1_radio_label": "Action mode:",
        "t1_radio_1": "Delete completely (Default)",
        "t1_radio_2": "Replace with dot (.) for 0.1s",
        
        "t1_lang_label": "Select languages to download",
        "t1_team_share_label": "Languages to include in Team Share folder (human-edited languages)",
        "t1_btn_run": "🚀 Run Batch Download & Convert",
        
        "t1_err_nolink": "Please enter at least one valid URL and filename prefix.",
        "t1_sp_loading": "Downloading subtitles and organizing folders...",
        "t1_msg_success": "✅ [{prefix}] {lang} processed",
        "t1_msg_err_fmt": "⚠️ [{prefix}] {lang} Format Error: {msg}",
        "t1_msg_err_sys": "❌ [{prefix}] {lang} System Error: {e}",
        "t1_success_all": "🎉 A total of {cnt} files processed successfully!",
        "t1_btn_download_zip": "📦 Download Complete Package (.zip)",
        "t1_share_folder": "Team_Share",

        # Tab 1 + Tab 5 shared: global shift
        "shift_sign_lbl": "Direction",
        "shift_sign_plus": "➕ Push later (delay / increase time)",
        "shift_sign_minus": "➖ Pull earlier (advance / decrease time)",
        "shift_offset_lbl": "Shift amount (HH:MM:SS)",
        "t1_shift_title": "##### ⏱️ Option: Global Time Shift (Applied on Download)",
        "t1_chk_shift": "Enable global timecode shift",

        # Tab 2 & 3 (Manual Convert)
        "t2_sub": "📁 Manually convert local VTT to SRT",
        "t2_upload": "Upload VTT file(s)",
        "t2_btn_dl": "⬇️ Download {name}",
        "t2_chk_lint": "Line-by-line format check on upload",
        "t2_fix_title": "##### Batch fix (apply selected fixes, then convert & download)",
        
        "t3_sub": "🔙 Convert reviewed SRT back to VOD VTT",
        "t3_upload": "Upload modified SRT file(s)",
        "t3_btn_dl": "⬇️ Download {name}",
        "t3_chk_lint": "Line-by-line format check on upload",
        "t3_fix_title": "##### Batch fix (apply selected fixes, then convert & download)",

        "fix_escape_amp": "Escape '&' → &amp;",
        "fix_strip_tags": "Remove VTT/HTML tags (keep text)",
        "fix_strip_bad_tags": "Remove invalid <> tags",
        "fix_remove_cue_id": "Remove VTT cue ID lines",
        "fix_strip_vtt_settings": "Remove VTT align/position settings on timecodes",
        "fix_tc_separator": "Fix ms separator (VTT: dot / SRT: comma)",
        "fix_arrow_text": "Replace '-->' in text with '→'",
        "fix_remove_orphan": "Delete blocks without timecode",
        "fix_remove_empty": "Delete empty subtitle cues",
        "fix_remove_empty": "Delete empty subtitle cues",
        "btn_fix_dl": "⬇️ Apply selected fixes & download {name}",
        "btn_fix_zip": "⬇️ Apply selected fixes & download ZIP",
        "val_fix_title": "##### Auto-fix (selected items only)",
        "val_fix_timestamp": "Fix timestamp format",
        "val_fix_vtt_extra": "Remove VTT cue ID & position settings",
        "val_fix_entities": "Escape &",
        "val_fix_markup": "Remove tags · replace '-->'",
        "val_fix_remove_invalid": "Delete empty cues & blocks without timestamp",
        
        # Tab 4 (Editor)
        "t4_sub": "✂️ Override Specific SRT Section",
        "t4_info": "Clears subtitles between the specified timecodes and replaces them by equally dividing the newly entered text (separated by line breaks). The rest of the subtitles remain intact.",
        "t4_upload": "Upload original SRT file to edit",
        "t4_start_lbl": "Start Time (e.g., 10:00 or 00:10:00)",
        "t4_end_lbl": "End Time (e.g., 11:00 or 00:11:00)",
        "t4_text_lbl": "Enter new subtitles (1 line break = 1 subtitle block)",
        "t4_text_ph": "Hello.\nNice to meet you.\nThis will be divided accordingly.",
        "t4_btn_run": "✨ Apply & Download",
        "t4_err_time": "Please check the time format. (e.g., 10:00 or 00:10:00,000)",
        "t4_success": "✅ Subtitle override & index realignment complete!",
        "t4_err_input": "Please provide the SRT file, start/end times, and the new subtitles.",

        # Tab 4 batch mode
        "t4_mode_lbl": "Processing mode",
        "t4_mode_single": "Single file (legacy)",
        "t4_mode_batch": "Batch (reference + auto-translated languages)",
        "t4_batch_info": "Upload one reference-language SRT and any number of other-language SRTs, then enter the translated text for each language. Language is auto-detected from filename pattern `..._<lang>.srt` (e.g., `..._en.srt`).",
        "t4_ref_upload": "Reference language SRT (1 file)",
        "t4_target_upload": "Auto-translated language SRTs (multiple)",
        "t4_lang_text_lbl": "[{lang}] {filename} - New subtitles (line break = block)",
        "t4_btn_batch_run": "✨ Apply Batch & Download ZIP",
        "t4_batch_success": "✅ {cnt} files processed",
        "t4_err_batch_nofile": "Please upload at least one SRT file.",
        "t4_err_batch_notext": "Each language SRT requires new subtitle text.",

        # Tab 5 (Global Shift)
        "t5_sub": "🕐 Shift all subtitle timecodes at once",
        "t5_info": "Upload SRT/VTT files, pick a direction (+/-) and amount, and every subtitle moves together. Subtitles pushed before 0s are removed. Output keeps each file's original format.",
        "t5_upload": "Upload SRT/VTT files to shift (multiple allowed)",
        "t5_btn_run": "🚀 Apply Shift & Download",
        "t5_success": "✅ {cnt} files shifted ({sign}{offset})",
        "t5_err_nofile": "Please upload at least one subtitle file.",
        "t5_err_offset": "Enter a shift amount greater than 0 in HH:MM:SS format. (e.g., 01:00:00)",

        # Validation (standard SRT/VTT validator rules)
        "err_vtt_header": "Missing WEBVTT header",
        "err_tc": "Missing timecode (-->)",
        "val_title": "##### Validation results",
        "val_ok": "No issues",
        "val_empty_file": "Empty file",
        "val_missing_file_header": "Missing WEBVTT header",
        "val_no_timestamp": "Missing timestamp",
        "val_bad_timestamp": "Invalid timestamp format",
        "val_bad_timestamp_order": "End time before start time",
        "val_empty_text": "Empty cue text",
        "val_bad_index": "Invalid subtitle index",
        "val_bad_block": "Invalid cue block structure",
        "val_bad_cue_id": "Cue identifier line (valid in VTT)",
        "val_bad_cue_settings": "Cue settings align etc. (valid in VTT)",
        "val_bad_markup": "Invalid tags (some players)",
        "val_unescaped_entity": "Unescaped & (HTML players)",
        "val_empty_text": "Empty cue text",
        "val_timestamp_conflict": "'-->' in text (breaks parsing)",
        "val_expander_none": "{lang} — no issues",
        "val_expander_count": "{lang} — {total} issue(s) (required {req} / optional {opt})",
        "val_legend": "🔴 **Required** = format violation, may break convert/playback · 🔵 **Optional** = allowed by spec, convert-only impact",
        "val_required_header": "🔴 Required fixes",
        "val_optional_header": "🔵 Optional notes (can skip)",
        "val_tag_required": "Required",
        "val_tag_optional": "Optional",
        "val_has_required": "Required fixes pending. Enable auto-fix below or edit the source before download.",
        "val_fix_required_title": "##### 🔴 Auto-fix required issues",
        "val_fix_optional_title": "##### 🔵 Auto-fix optional notes",
        "val_no_autofix": "No auto-fixable issues detected.",
    }
}

DOWNLOAD_LANGS = [
    'en', 'ja', 'zh-CN', 'zh-TW', 'th', 'id', 'vi', 'es', 'fr', 'pt', 'fil', 'ko',
    'ar', 'de', 'it', 'ru', 'bn', 'hi',
]
LANG_LABELS = {
    'en': 'en · English', 'ja': 'ja · 日本語', 'zh-CN': 'zh-CN · 中文(简体)',
    'zh-TW': 'zh-TW · 中文(繁體)', 'th': 'th · ไทย', 'id': 'id · Indonesia',
    'vi': 'vi · Tiếng Việt', 'es': 'es · Español', 'fr': 'fr · Français',
    'pt': 'pt · Português', 'fil': 'fil · Filipino', 'ko': 'ko · 한국어',
    'ar': 'ar · العربية', 'de': 'de · Deutsch', 'it': 'it · Italiano',
    'ru': 'ru · Русский', 'bn': 'bn · বাংলা', 'hi': 'hi · हिन्दी',
}
DEFAULT_TEAM_SHARE_LANGS = ['en', 'ja', 'zh-CN', 'ko']

def _lang_label(code):
    return LANG_LABELS.get(code, code)

def _init_multiselect_langs(state_key, all_langs, default_selection):
    if state_key not in st.session_state:
        st.session_state[state_key] = list(default_selection)
    else:
        st.session_state[state_key] = [
            lang for lang in st.session_state[state_key] if lang in all_langs
        ]

# 기본 설정 및 사이드바 언어 선택기
st.set_page_config(page_title="Subtitle Editor", layout="wide")
selected_lang = st.sidebar.selectbox("Language / 언어", ["한국어", "English"])
t = TEXTS[selected_lang] # 💡 여기서 선택된 언어의 텍스트 꾸러미를 불러옵니다!

# ==========================================
# 1. 시간(타임코드) 계산 헬퍼 함수
# ==========================================
def parse_tc_to_ms(tc_str):
    tc_str = tc_str.replace(',', '.').strip()
    if '-->' in tc_str:
        tc_str = tc_str.split('-->')[0].strip()
    parts = tc_str.split(':')
    if len(parts) == 2:
        h = 0
        m, s = parts
    elif len(parts) == 3:
        h, m, s = parts
    else:
        return 0
    s_parts = s.split('.')
    sec = s_parts[0]
    ms = s_parts[1] if len(s_parts) > 1 else 0
    ms_val = int(str(ms).ljust(3, '0')[:3])
    return int(h) * 3600000 + int(m) * 60000 + int(sec) * 1000 + ms_val

def ms_to_srt_tc(ms):
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(ms):03d}"

def ms_to_vtt_tc(ms):
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    if h > 0:
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}.{int(ms):03d}"
    return f"{int(m):02d}:{int(s):02d}.{int(ms):03d}"

def format_time_for_srt(tc):
    tc = tc.strip().replace('.', ',')
    if tc.count(':') == 1:
        tc = f"00:{tc}"
    return tc

# ==========================================
# 2. [기능 1] 앞부분 테스트 자막 정리 로직
# ==========================================
def process_test_subtitles(vtt_content, test_min, action_type):
    threshold_ms = int(test_min * 60 * 1000)
    blocks = re.split(r'\n\s*\n', vtt_content.strip())
    new_blocks =[]
    
    for block in blocks:
        lines = block.split('\n')
        if 'WEBVTT' in lines[0] or 'NOTE' in lines[0]:
            new_blocks.append(block)
            continue
        
        tc_idx = next((i for i, line in enumerate(lines) if '-->' in line), -1)
        if tc_idx == -1: 
            new_blocks.append(block)
            continue
        
        tc_line = re.sub(r'\s*align:.*', '', lines[tc_idx])
        start_str = tc_line.split('-->')[0].strip()
        start_ms = parse_tc_to_ms(start_str)
        
        if start_ms < threshold_ms:
            # t1_radio_1 에 해당하는 값이 "완전 삭제"를 의미하는지 확인
            if action_type == t["t1_radio_1"]:
                continue 
            else:
                end_ms = start_ms + 100
                new_tc = f"{ms_to_vtt_tc(start_ms)} --> {ms_to_vtt_tc(end_ms)}"
                new_block_lines = lines[:tc_idx] + [new_tc, "."]
                new_blocks.append("\n".join(new_block_lines))
        else:
            new_blocks.append(block)
            
    return "\n\n".join(new_blocks) + "\n\n"

# ==========================================
# 3. [기능 2] 구간 자막 교체 및 밀어넣기 로직
# ==========================================
def replace_srt_section(srt_content, start_str, end_str, new_text):
    try:
        window_start = parse_tc_to_ms(start_str)
        window_end = parse_tc_to_ms(end_str)
    except Exception:
        return False, t["t4_err_time"]
        
    new_lines =[line.strip() for line in new_text.strip().split('\n') if line.strip()]
    
    blocks = re.split(r'\n\s*\n', srt_content.strip())
    before_blocks = []
    after_blocks =[]
    
    for block in blocks:
        lines = block.split('\n')
        if len(lines) < 3: continue
        
        tc_idx = next((i for i, line in enumerate(lines) if '-->' in line), -1)
        if tc_idx == -1: continue
        
        b_start_str = lines[tc_idx].split('-->')[0].strip()
        b_start_ms = parse_tc_to_ms(b_start_str)
        
        if b_start_ms < window_start:
            before_blocks.append("\n".join(lines[tc_idx:]))
        elif b_start_ms >= window_end:
            after_blocks.append("\n".join(lines[tc_idx:]))
            
    generated_blocks =[]
    if new_lines:
        total_window_ms = window_end - window_start
        duration_ms = total_window_ms // len(new_lines)
        if duration_ms > 2000:
            duration_ms = 2000
            
        current_time = window_start
        for text_line in new_lines:
            t_start = ms_to_srt_tc(current_time)
            t_end = ms_to_srt_tc(current_time + duration_ms)
            generated_blocks.append(f"{t_start} --> {t_end}\n{text_line}")
            current_time += duration_ms
            
    final_srt_lines =[]
    idx = 1
    for b in (before_blocks + generated_blocks + after_blocks):
        final_srt_lines.append(str(idx))
        final_srt_lines.append(b)
        final_srt_lines.append("")
        idx += 1
        
    return True, "\n".join(final_srt_lines)

# ==========================================
# 3-1. [기능 3] 전체 자막 타임코드 시프트 로직
# ==========================================
def parse_offset_to_ms(sign, hms_str):
    """부호(+/-)와 'HH:MM:SS' 문자열을 받아 밀리초 오프셋(부호 포함)으로 변환."""
    base = parse_tc_to_ms(hms_str)
    return -base if sign == "-" else base

def shift_subtitle_content(content, offset_ms, fmt):
    """자막 전체 타임코드를 offset_ms 만큼 이동. fmt('srt'|'vtt')에 맞춰 출력.
    시작 TC가 0 이전(음수)이 되는 블록은 삭제하고 인덱스를 1부터 재정렬한다."""
    blocks = re.split(r'\n\s*\n', content.strip())
    shifted =[]
    for block in blocks:
        lines = block.split('\n')
        if lines and ('WEBVTT' in lines[0] or 'NOTE' in lines[0]):
            continue  # 헤더/노트는 버리고 vtt 출력 시 다시 붙임
        tc_idx = next((i for i, line in enumerate(lines) if '-->' in line), -1)
        if tc_idx == -1:
            continue
        tc_line = re.sub(r'\s*align:.*', '', lines[tc_idx])
        start_str, end_str = tc_line.split('-->')
        start_ms = parse_tc_to_ms(start_str) + offset_ms
        end_ms = parse_tc_to_ms(end_str) + offset_ms
        if start_ms < 0:  # 당겨서 0 이전으로 밀려난 자막은 삭제
            continue
        text_lines = lines[tc_idx+1:]
        shifted.append((start_ms, end_ms, text_lines))

    if fmt == 'vtt':
        out = ["WEBVTT", ""]
        for start_ms, end_ms, text_lines in shifted:
            tc = f"{ms_to_vtt_tc(start_ms)} --> {ms_to_vtt_tc(end_ms)}"
            out.extend([tc] + text_lines + [""])
        return "\n".join(out)

    out =[]
    for i, (start_ms, end_ms, text_lines) in enumerate(shifted, 1):
        tc = f"{ms_to_srt_tc(start_ms)} --> {ms_to_srt_tc(end_ms)}"
        out.extend([str(i), tc] + text_lines + [""])
    return "\n".join(out)

# ==========================================
# 4. 기본 포맷 변환 (VTT <-> SRT) 함수
# ==========================================
def vtt_to_srt_str(vtt_content):
    blocks = re.split(r'\n\s*\n', vtt_content.strip())
    srt_lines =[]
    index = 1
    for block in blocks:
        lines = block.split('\n')
        if 'WEBVTT' in lines[0] or 'NOTE' in lines[0]: continue
        
        tc_idx = next((i for i, line in enumerate(lines) if '-->' in line), -1)
        if tc_idx == -1: continue

        tc_line = re.sub(r'\s*align:.*', '', lines[tc_idx])
        start_time, end_time = tc_line.split('-->')
        srt_tc = f"{format_time_for_srt(start_time)} --> {format_time_for_srt(end_time)}"
        text_lines = lines[tc_idx+1:]

        srt_lines.extend([str(index), srt_tc] + text_lines + [""])
        index += 1
    return "\n".join(srt_lines)

def srt_to_vtt_str(srt_content):
    blocks = re.split(r'\n\s*\n', srt_content.strip())
    vtt_lines = ["WEBVTT\n"]
    for block in blocks:
        lines = block.split('\n')
        if len(lines) < 3: continue
        
        tc_idx = next((i for i, line in enumerate(lines) if '-->' in line), -1)
        if tc_idx == -1: continue

        tc_line = lines[tc_idx].replace(',', '.')
        text_lines = lines[tc_idx+1:]
        vtt_lines.extend([tc_line] + text_lines + [""])
    return "\n".join(vtt_lines)

# ==========================================
# 5. 변환 검사 (VTT <-> SRT)
# ==========================================
SRT_TC_RE = re.compile(
    r'^(\d{1,2}:\d{2}:\d{2},\d{1,3}|\d{1,2}:\d{2},\d{1,3})\s*-->\s*'
    r'(\d{1,2}:\d{2}:\d{2},\d{1,3}|\d{1,2}:\d{2},\d{1,3})'
)
VTT_TC_RE = re.compile(
    r'^((?:\d{1,2}:)?\d{1,2}:\d{2}\.\d{1,3})\s*-->\s*((?:\d{1,2}:)?\d{1,2}:\d{2}\.\d{1,3})'
)
VTT_TAG_RE = re.compile(r'</?(?:c|b|i|u|ruby|rt|lang|v|voice)(?:\s[^>]*)?>', re.I)
VTT_SETTINGS_RE = re.compile(r'\s+(align|position|line|size|vertical):[^\s]*', re.I)
REQUIRED_RULES = frozenset({
    "empty_file", "missing_file_header", "no_timestamp", "bad_timestamp",
    "bad_timestamp_order", "bad_index", "bad_block", "timestamp_conflict",
})

def _finding(line, tc, text, rule, severity=None):
    if severity is None:
        severity = "required" if rule in REQUIRED_RULES else "optional"
    preview = (text or "").strip()
    if len(preview) > 100:
        preview = preview[:97] + "..."
    return {
        "line": line,
        "tc": (tc or "-").strip(),
        "text": preview or "",
        "rule": rule,
        "severity": severity,
    }

def _rule_label(rule):
    return t.get(f"val_{rule}", rule)

def split_blocks_with_lines(content):
    lines = content.splitlines()
    blocks = []
    current = []
    block_start = None
    for i, line in enumerate(lines, 1):
        if not line.strip():
            if current:
                blocks.append((block_start, current))
                current = []
                block_start = None
        else:
            if block_start is None:
                block_start = i
            current.append((i, line))
    if current:
        blocks.append((block_start, current))
    return blocks

def _clean_vtt_tc(tc_line):
    return VTT_SETTINGS_RE.sub('', tc_line).strip()

def _tc_short(tc_line):
    tc = _clean_vtt_tc(tc_line) if tc_line else "-"
    return tc[:45] + "..." if len(tc) > 48 else tc

def detect_lang_from_filename(name):
    stem = re.sub(r'\.(srt|vtt)$', '', name, flags=re.IGNORECASE)
    parts = stem.rsplit('_', 1)
    return parts[-1] if len(parts) > 1 and parts[-1] else name

def _check_cue_text(line_no, tc_short, text, findings):
    stripped = text.strip()
    if not stripped:
        return
    if '-->' in stripped:
        findings.append(_finding(line_no, tc_short, text, "timestamp_conflict"))
    if '<' in stripped:
        cleaned = VTT_TAG_RE.sub('', stripped)
        if '<' in cleaned or '>' in cleaned:
            findings.append(_finding(line_no, tc_short, text, "bad_markup"))
    if '&' in stripped and not re.search(r'&(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);', stripped):
        findings.append(_finding(line_no, tc_short, text, "unescaped_entity"))

def validate_vtt_file(content):
    findings = []
    if not content.strip():
        return [_finding(1, "-", "", "empty_file")]

    lines = content.splitlines()
    if not lines[0].strip().startswith("WEBVTT"):
        findings.append(_finding(1, "-", lines[0], "missing_file_header"))

    for block_start, block_lines in split_blocks_with_lines(content):
        first_text = block_lines[0][1]
        if first_text.strip().startswith("NOTE"):
            continue
        if block_start == 1 and not any("-->" in txt for _, txt in block_lines):
            continue

        tc_entries = [(ln, txt) for ln, txt in block_lines if "-->" in txt]
        if not tc_entries:
            findings.append(_finding(block_start, "-", first_text, "no_timestamp"))
            continue

        tc_line_no, tc_text = tc_entries[0]
        tc_short = _tc_short(tc_text)

        for ln, txt in block_lines:
            if ln < tc_line_no and txt.strip():
                findings.append(_finding(ln, tc_short, txt, "bad_cue_id"))

        if VTT_SETTINGS_RE.search(tc_text):
            findings.append(_finding(tc_line_no, tc_short, tc_text, "bad_cue_settings"))

        tc_clean = _clean_vtt_tc(tc_text)
        if not VTT_TC_RE.match(tc_clean):
            findings.append(_finding(tc_line_no, tc_short, tc_text, "bad_timestamp"))
        else:
            start_s, end_s = tc_clean.split('-->', 1)
            if parse_tc_to_ms(start_s) >= parse_tc_to_ms(end_s):
                findings.append(_finding(tc_line_no, tc_short, tc_text, "bad_timestamp_order"))

        text_lines = [(ln, txt) for ln, txt in block_lines if ln > tc_line_no]
        if not any(txt.strip() for _, txt in text_lines):
            findings.append(_finding(tc_line_no, tc_short, "", "empty_text"))
        else:
            for ln, txt in text_lines:
                _check_cue_text(ln, tc_short, txt, findings)

    return findings

def validate_srt_file(content):
    findings = []
    if not content.strip():
        return [_finding(1, "-", "", "empty_file")]

    if "-->" not in content:
        lines = content.splitlines()
        findings.append(_finding(1, "-", lines[0] if lines else "", "no_timestamp"))
        return findings

    for block_start, block_lines in split_blocks_with_lines(content):
        if len(block_lines) < 2:
            findings.append(_finding(block_start, "-", block_lines[0][1], "bad_block"))
            continue

        idx_line_no, idx_text = block_lines[0]
        if not idx_text.strip().isdigit():
            findings.append(_finding(idx_line_no, "-", idx_text, "bad_index"))

        tc_entries = [(ln, txt) for ln, txt in block_lines if "-->" in txt]
        if not tc_entries:
            findings.append(_finding(block_start, "-", block_lines[0][1], "no_timestamp"))
            continue

        tc_line_no, tc_text = tc_entries[0]
        tc_short = tc_text.strip()
        if len(tc_short) > 48:
            tc_short = tc_short[:45] + "..."

        if not SRT_TC_RE.match(tc_text.strip()):
            findings.append(_finding(tc_line_no, tc_short, tc_text, "bad_timestamp"))
        else:
            start_s, end_s = tc_text.strip().split('-->', 1)
            if parse_tc_to_ms(start_s) >= parse_tc_to_ms(end_s):
                findings.append(_finding(tc_line_no, tc_short, tc_text, "bad_timestamp_order"))

        text_lines = [(ln, txt) for ln, txt in block_lines if ln > tc_line_no]
        if not any(txt.strip() for _, txt in text_lines):
            findings.append(_finding(tc_line_no, tc_short, "", "empty_text"))
        else:
            for ln, txt in text_lines:
                _check_cue_text(ln, tc_short, txt, findings)

    return findings

def _escape_bare_amp(text):
    out = []
    i = 0
    while i < len(text):
        if text[i] == '&':
            m = re.match(r'&(?:[a-zA-Z]+|#\d+|#x[0-9a-fA-F]+);', text[i:])
            if m:
                out.append(m.group(0))
                i += len(m.group(0))
            else:
                out.append('&amp;')
                i += 1
        else:
            out.append(text[i])
            i += 1
    return ''.join(out)

def _fix_tc_separator_line(line, fmt):
    if '-->' not in line:
        return line
    if fmt == 'vtt':
        return re.sub(r'(\d),(\d)', r'\1.\2', line)
    return re.sub(r'(\d)\.(\d)', r'\1,\2', line)

def _ui_fixes_to_internal(ui, fmt):
    return {
        'fix_tc_separator': ui.get('fix_timestamp', False),
        'escape_amp': ui.get('fix_entities', False),
        'strip_vtt_tags': ui.get('fix_markup', False),
        'strip_bad_tags': ui.get('fix_markup', False),
        'fix_arrow_text': ui.get('fix_markup', False),
        'remove_cue_id': ui.get('fix_vtt_extra', False) if fmt == 'vtt' else False,
        'strip_vtt_settings': ui.get('fix_vtt_extra', False) if fmt == 'vtt' else False,
        'remove_orphan': ui.get('fix_remove_invalid', False),
        'remove_empty': ui.get('fix_remove_invalid', False),
    }

RULE_TO_FIX = {
    "bad_timestamp": {"fix_timestamp"},
    "bad_timestamp_order": {"fix_timestamp"},
    "bad_cue_id": {"fix_vtt_extra"},
    "bad_cue_settings": {"fix_vtt_extra"},
    "unescaped_entity": {"fix_entities"},
    "bad_markup": {"fix_markup"},
    "timestamp_conflict": {"fix_markup"},
    "no_timestamp": {"fix_remove_invalid"},
    "bad_block": {"fix_remove_invalid"},
    "empty_text": {"fix_remove_invalid"},
}
REQUIRED_FIX_IDS = {"fix_timestamp"}

def fixes_needed_from_sections(sections, fmt):
    rules = set()
    for section in sections:
        for f in section[1]:
            rules.add(f["rule"])
    needed = set()
    for rule in rules:
        needed.update(RULE_TO_FIX.get(rule, ()))
    if fmt != "vtt":
        needed.discard("fix_vtt_extra")
    return needed

def _get_fix_option_defs(fmt):
    required = [("fix_timestamp", "val_fix_timestamp", True)]
    optional = [
        ("fix_entities", "val_fix_entities", False),
        ("fix_markup", "val_fix_markup", False),
        ("fix_remove_invalid", "val_fix_remove_invalid", False),
    ]
    if fmt == 'vtt':
        optional.insert(0, ("fix_vtt_extra", "val_fix_vtt_extra", False))
    return required, optional

def apply_subtitle_fixes(content, fmt, ui_fixes):
    fixes = _ui_fixes_to_internal(ui_fixes, fmt)
    if not any(fixes.values()):
        return content

    blocks_out = []
    for block_start, block_lines in split_blocks_with_lines(content):
        lines = [txt for _, txt in block_lines]
        if not lines:
            continue

        if block_start == 1 and not any('-->' in ln for ln in lines):
            if fmt == 'vtt':
                blocks_out.append(lines)
            continue

        if lines[0].strip().startswith('NOTE'):
            blocks_out.append(lines)
            continue

        tc_idx = next((i for i, ln in enumerate(lines) if '-->' in ln), -1)
        if tc_idx == -1:
            if not fixes.get('remove_orphan'):
                blocks_out.append(lines)
            continue

        if fixes.get('remove_cue_id') and fmt == 'vtt' and tc_idx > 0:
            lines = lines[tc_idx:]
            tc_idx = 0

        if fixes.get('strip_vtt_settings') and fmt == 'vtt':
            lines[tc_idx] = VTT_SETTINGS_RE.sub('', lines[tc_idx]).strip()

        if fixes.get('fix_tc_separator'):
            lines[tc_idx] = _fix_tc_separator_line(lines[tc_idx], fmt)

        fixed_text = []
        for tl in lines[tc_idx + 1:]:
            s = tl
            if fixes.get('escape_amp'):
                s = _escape_bare_amp(s)
            if fixes.get('strip_vtt_tags'):
                s = VTT_TAG_RE.sub('', s)
            if fixes.get('strip_bad_tags'):
                s = re.sub(r'<[^>]*>', '', s)
            if fixes.get('fix_arrow_text'):
                s = s.replace('-->', '→')
            fixed_text.append(s)

        if fixes.get('remove_empty') and not any(x.strip() for x in fixed_text):
            continue

        blocks_out.append(lines[:tc_idx + 1] + fixed_text)

    if fmt == 'vtt':
        if not blocks_out or not blocks_out[0][0].strip().startswith('WEBVTT'):
            blocks_out.insert(0, ['WEBVTT'])
        return '\n\n'.join('\n'.join(bl) for bl in blocks_out if bl).rstrip() + '\n'

    out = []
    idx = 1
    for bl in blocks_out:
        tc_idx = next((i for i, ln in enumerate(bl) if '-->' in ln), -1)
        if tc_idx == -1:
            continue
        out.extend([str(idx), bl[tc_idx]] + bl[tc_idx + 1:] + [''])
        idx += 1
    return '\n'.join(out)

def render_fix_options(fmt, key_prefix, needed_fix_ids):
    fixes = {}
    required_defs, optional_defs = _get_fix_option_defs(fmt)
    req_show = [d for d in required_defs if d[0] in needed_fix_ids]
    opt_show = [d for d in optional_defs if d[0] in needed_fix_ids]

    if req_show:
        st.markdown(t["val_fix_required_title"])
        for fix_id, label_key, default in req_show:
            fixes[fix_id] = st.checkbox(t[label_key], value=True, key=f"{key_prefix}_fix_{fix_id}")
    if opt_show:
        st.markdown(t["val_fix_optional_title"])
        col1, col2 = st.columns(2)
        for i, (fix_id, label_key, default) in enumerate(opt_show):
            with col1 if i % 2 == 0 else col2:
                fixes[fix_id] = st.checkbox(t[label_key], value=True, key=f"{key_prefix}_fix_{fix_id}")
    return fixes

def _render_finding_row(f):
    tag = t["val_tag_required"] if f["severity"] == "required" else t["val_tag_optional"]
    icon = "🔴" if f["severity"] == "required" else "🔵"
    label = html.escape(_rule_label(f["rule"]))
    head = f'{icon} <b>L{f["line"]}</b> · <b>{html.escape(tag)}</b> · <code>{html.escape(f["rule"])}</code> — {label}'
    body_parts = []
    if f["tc"] != "-":
        body_parts.append(f'<div class="val-tc">{html.escape(f["tc"])}</div>')
    if f["text"]:
        body_parts.append(f'<div class="val-text">{html.escape(f["text"])}</div>')
    body = "".join(body_parts)
    st.markdown(
        f'<div class="val-item"><div class="val-head">{head}</div>{body}</div>',
        unsafe_allow_html=True,
    )

def _val_results_css():
    st.markdown(
        """<style>
        .val-item { margin: 0 0 0.35rem 0; padding: 0; }
        .val-head { font-size: 0.88rem; line-height: 1.35; margin: 0 0 0.2rem 0; }
        .val-tc { margin: 0 0 0.1rem 0.6rem; padding: 0.15rem 0.4rem; font-size: 0.82rem;
            font-family: monospace; background: #f6f6f6; border-radius: 3px; display: inline-block; }
        .val-text { margin: 0 0 0 0.6rem; padding: 0.1rem 0 0.1rem 0.45rem; font-size: 0.88rem;
            border-left: 2px solid #ccc; line-height: 1.3; }
        .val-sec { margin: 0.25rem 0 0.15rem; font-size: 0.9rem; font-weight: 600; }
        </style>""",
        unsafe_allow_html=True,
    )

def _expander_label(lang, findings):
    if not findings:
        return t["val_expander_none"].format(lang=lang)
    req = sum(1 for f in findings if f["severity"] == "required")
    opt = len(findings) - req
    return t["val_expander_count"].format(lang=lang, total=len(findings), req=req, opt=opt)

def render_lint_results(sections, key_prefix="val"):
    if not sections:
        return
    st.markdown(t["val_title"])
    st.caption(t["val_legend"])
    _val_results_css()
    any_required = False
    for i, section in enumerate(sections):
        lang = section[0]
        findings = section[1]
        uid = section[2] if len(section) > 2 else str(i)
        req = [f for f in findings if f["severity"] == "required"]
        if req:
            any_required = True
        with st.expander(_expander_label(lang, findings), expanded=False):
            if not findings:
                continue
            if req:
                st.markdown(f'<p class="val-sec">{t["val_required_header"]} ({len(req)})</p>', unsafe_allow_html=True)
                for f in req:
                    _render_finding_row(f)
            opt = [f for f in findings if f["severity"] == "optional"]
            if opt:
                st.markdown(f'<p class="val-sec">{t["val_optional_header"]} ({len(opt)})</p>', unsafe_allow_html=True)
                for f in opt:
                    _render_finding_row(f)
    if any_required:
        st.warning(t["val_has_required"])

def run_manual_convert_tab(tab_key, upload_label, upload_types, src_fmt, validate_fn, convert_fn, out_name_fn):
    enable_lint = st.checkbox(
        t[f"{tab_key}_chk_lint"], value=True, key=f"{tab_key}_lint"
    )
    uploaded = st.file_uploader(
        upload_label, type=upload_types, accept_multiple_files=True, key=f"{tab_key}_up"
    )
    if not uploaded:
        return

    files = []
    for f in uploaded:
        files.append({
            'name': f.name,
            'lang': detect_lang_from_filename(f.name),
            'content': f.read().decode('utf-8'),
        })

    sections = [(fd['lang'], validate_fn(fd['content']), fd['name']) for fd in files]
    if enable_lint:
        render_lint_results(sections, key_prefix=tab_key)

    needed_fixes = fixes_needed_from_sections(sections, src_fmt)
    fixes = {}
    if needed_fixes:
        st.markdown("---")
        fixes = render_fix_options(src_fmt, tab_key, needed_fixes)

    outputs = []
    for fd in files:
        fixed = apply_subtitle_fixes(fd['content'], src_fmt, fixes)
        outputs.append((out_name_fn(fd['name']), convert_fn(fixed)))

    st.markdown("---")
    if len(outputs) == 1:
        name, data = outputs[0]
        st.download_button(
            t["btn_fix_dl"].format(name=name),
            data=data,
            file_name=name,
            mime="text/plain",
            type="primary",
            key=f"{tab_key}_dl_single",
        )
    else:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for name, data in outputs:
                zf.writestr(name, data)
        st.download_button(
            t["btn_fix_zip"],
            data=zip_buffer.getvalue(),
            file_name=f"{tab_key}_converted.zip",
            mime="application/zip",
            type="primary",
            key=f"{tab_key}_dl_zip",
        )

def render_lint_log(sections):
    render_lint_results(sections)

def validate_vtt(content):
    findings = validate_vtt_file(content)
    required = [f for f in findings if f["severity"] == "required"]
    if required:
        f = required[0]
        return False, f"L{f['line']} [{t['val_tag_required']}] {_rule_label(f['rule'])}"
    return True, ""

def validate_srt(content):
    findings = validate_srt_file(content)
    required = [f for f in findings if f["severity"] == "required"]
    if required:
        f = required[0]
        return False, f"L{f['line']} [{t['val_tag_required']}] {_rule_label(f['rule'])}"
    return True, ""

lint_vtt_to_srt = validate_vtt_file
lint_srt_to_vtt = validate_srt_file
lint_vtt = validate_vtt_file
lint_srt = validate_srt_file

# ==========================================
# 6. Streamlit 웹 UI 구성
# ==========================================
st.title(t["app_title"])

if 'link_count' not in st.session_state:
    st.session_state.link_count = 1

def add_link():
    st.session_state.link_count += 1

tab1, tab2, tab3, tab4, tab5 = st.tabs([t["tab1"], t["tab2"], t["tab3"], t["tab4"], t["tab5"]])

# ----------------- TAB 1: 복수 다운로드 & 테스트 자막 컷팅 -----------------
with tab1:
    st.subheader(t["t1_sub"])
    st.info(t["t1_info"])
    
    st.markdown(t["t1_link_title"])
    links_data =[]
    
    for i in range(st.session_state.link_count):
        col1, col2 = st.columns([2, 1])
        with col1:
            u = st.text_input(t["t1_url_label"].format(num=i+1), key=f"url_{i}", placeholder=t["t1_url_ph"])
        with col2:
            p = st.text_input(t["t1_prefix_label"].format(num=i+1), key=f"prefix_{i}", placeholder=t["t1_prefix_ph"].format(num=i+1))
        links_data.append((u, p))
        
    st.button(t["t1_btn_add"], on_click=add_link)
    
    st.markdown("---")
    st.markdown(t["t1_opt_title"])
    
    enable_cleanup = st.checkbox(t["t1_chk_clean"], value=True)
    
    if enable_cleanup:
        col1, col2 = st.columns(2)
        with col1:
            test_min = st.number_input(t["t1_min_label"], min_value=0.0, value=20.0, step=1.0)
        with col2:
            action_type = st.radio(t["t1_radio_label"], [t["t1_radio_1"], t["t1_radio_2"]])
    else:
        test_min = 0.0
        action_type = t["t1_radio_1"]

    st.markdown("---")
    st.markdown(t["t1_shift_title"])
    enable_shift = st.checkbox(t["t1_chk_shift"], value=False)
    if enable_shift:
        scol1, scol2 = st.columns(2)
        with scol1:
            shift_sign = st.radio(t["shift_sign_lbl"], [t["shift_sign_minus"], t["shift_sign_plus"]], key="t1_shift_sign")
        with scol2:
            shift_offset_str = st.text_input(t["shift_offset_lbl"], value="01:00:00", key="t1_shift_offset")
        sign_char = "-" if shift_sign == t["shift_sign_minus"] else "+"
        t1_offset_ms = parse_offset_to_ms(sign_char, shift_offset_str)
    else:
        t1_offset_ms = 0

    st.markdown("---")
    _init_multiselect_langs("t1_selected_langs_v4", DOWNLOAD_LANGS, DOWNLOAD_LANGS)
    selected_langs = st.multiselect(
        t["t1_lang_label"], DOWNLOAD_LANGS, format_func=_lang_label, key="t1_selected_langs_v4",
    )

    _init_multiselect_langs("t1_team_share_langs_v4", DOWNLOAD_LANGS, DEFAULT_TEAM_SHARE_LANGS)
    team_share_langs = st.multiselect(
        t["t1_team_share_label"], DOWNLOAD_LANGS, format_func=_lang_label, key="t1_team_share_langs_v4",
    )

    if st.button(t["t1_btn_run"], type="primary"):
        valid_links =[(u.strip(), p.strip()) for u, p in links_data if u.strip() and p.strip()]
        
        if not valid_links:
            st.error(t["t1_err_nolink"])
        else:
            zip_buffer = io.BytesIO()
            success_count = 0
            
            with st.spinner(t["t1_sp_loading"]):
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    
                    for url_input, prefix in valid_links:
                        base_url = url_input.rsplit('/', 1)[0]
                        
                        for lang in selected_langs:
                            target_url = f"{base_url}/sub_{lang}.vtt"
                            try:
                                res = requests.get(target_url, timeout=10)
                                res.encoding = 'utf-8' 
                                
                                if res.status_code == 200:
                                    vtt_text = res.text
                                    is_valid, msg = validate_vtt(vtt_text)
                                    
                                    if is_valid:
                                        if enable_cleanup:
                                            vtt_text = process_test_subtitles(vtt_text, test_min, action_type)
                                        if enable_shift and t1_offset_ms != 0:
                                            vtt_text = shift_subtitle_content(vtt_text, t1_offset_ms, 'vtt')

                                        zip_file.writestr(f"original_vtt/{prefix}_{lang}.vtt", vtt_text)
                                        srt_text = vtt_to_srt_str(vtt_text)
                                        zip_file.writestr(f"premiere_srt/{prefix}_{lang}.srt", srt_text)
                                        
                                        if lang in team_share_langs:
                                            folder_name = f"{prefix}_{t['t1_share_folder']}"
                                            zip_file.writestr(f"{folder_name}/{prefix}_{lang}.vtt", vtt_text)
                                        
                                        success_count += 1
                                    else:
                                        st.warning(t["t1_msg_err_fmt"].format(prefix=prefix, lang=lang, msg=msg))
                                else:
                                    st.warning(f"⚠️ [{prefix}] {lang} — HTTP {res.status_code}: {target_url}")
                            except Exception as e:
                                st.error(t["t1_msg_err_sys"].format(prefix=prefix, lang=lang, e=e))

            if success_count > 0:
                st.success(t["t1_success_all"].format(cnt=success_count))
                st.download_button(
                    label=t["t1_btn_download_zip"],
                    data=zip_buffer.getvalue(),
                    file_name="subtitles_processed_package.zip",
                    mime="application/zip",
                    type="primary"
                )
            else:
                st.error("❌ 다운로드된 자막이 없습니다. URL과 서버 경로를 확인해주세요. / No subtitles downloaded. Please check the URL and server path.")

# ----------------- TAB 2: 수동 VTT -> SRT -----------------
with tab2:
    st.subheader(t["t2_sub"])
    run_manual_convert_tab(
        "t2", t["t2_upload"], ['vtt'], 'vtt',
        validate_vtt_file, vtt_to_srt_str,
        lambda name: name.replace('.vtt', '.srt'),
    )

# ----------------- TAB 3: 수동 SRT -> VTT (최종) -----------------
with tab3:
    st.subheader(t["t3_sub"])
    run_manual_convert_tab(
        "t3", t["t3_upload"], ['srt'], 'srt',
        validate_srt_file, srt_to_vtt_str,
        lambda name: name.replace('.srt', '_final.vtt'),
    )

# ----------------- TAB 4: 구간 자막 교체 & 밀어넣기 -----------------
with tab4:
    st.subheader(t["t4_sub"])

    mode = st.radio(t["t4_mode_lbl"], [t["t4_mode_batch"], t["t4_mode_single"]], horizontal=True)

    if mode == t["t4_mode_single"]:
        st.info(t["t4_info"])

        uploaded_edit = st.file_uploader(t["t4_upload"], type=['srt'])

        col1, col2 = st.columns([1, 2])
        with col1:
            start_time_input = st.text_input(t["t4_start_lbl"], value="10:00")
            end_time_input = st.text_input(t["t4_end_lbl"], value="11:00")

        with col2:
            new_subtitles = st.text_area(t["t4_text_lbl"], height=200, placeholder=t["t4_text_ph"])

        if st.button(t["t4_btn_run"], type="primary"):
            if uploaded_edit and start_time_input and end_time_input:
                srt_content = uploaded_edit.read().decode("utf-8")
                success, result = replace_srt_section(srt_content, start_time_input, end_time_input, new_subtitles)

                if success:
                    st.success(t["t4_success"])
                    dl_name = f"edited_{uploaded_edit.name}"
                    st.download_button(
                        label=t["t2_btn_dl"].format(name=dl_name),
                        data=result,
                        file_name=dl_name,
                        mime="text/plain",
                        type="primary"
                    )
                else:
                    st.error(result)
            else:
                st.warning(t["t4_err_input"])
    else:
        st.info(t["t4_batch_info"])

        ref_file = st.file_uploader(t["t4_ref_upload"], type=['srt'], accept_multiple_files=False, key="batch_ref")
        target_files = st.file_uploader(t["t4_target_upload"], type=['srt'], accept_multiple_files=True, key="batch_targets")

        col1, col2 = st.columns([1, 1])
        with col1:
            batch_start = st.text_input(t["t4_start_lbl"], value="10:00", key="batch_start")
        with col2:
            batch_end = st.text_input(t["t4_end_lbl"], value="11:00", key="batch_end")

        all_files = []
        if ref_file is not None:
            all_files.append(("ref", ref_file))
        if target_files:
            seen_names = {ref_file.name} if ref_file is not None else set()
            for tf in target_files:
                if tf.name in seen_names: continue
                seen_names.add(tf.name)
                all_files.append(("target", tf))

        lang_texts = {}
        if all_files:
            st.markdown("---")
            for kind, f in all_files:
                lang = detect_lang_from_filename(f.name)
                key = f"batch_text_{f.name}"
                lang_texts[f.name] = (lang, f, st.text_area(
                    t["t4_lang_text_lbl"].format(lang=lang, filename=f.name),
                    height=140,
                    placeholder=t["t4_text_ph"],
                    key=key,
                ))

        if st.button(t["t4_btn_batch_run"], type="primary", key="batch_run"):
            if not all_files:
                st.warning(t["t4_err_batch_nofile"])
            elif not batch_start or not batch_end:
                st.warning(t["t4_err_input"])
            elif any(not txt.strip() for (_lang, _f, txt) in lang_texts.values()):
                st.warning(t["t4_err_batch_notext"])
            else:
                zip_buffer = io.BytesIO()
                processed = 0
                errors = []
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for fname, (lang, f, txt) in lang_texts.items():
                        try:
                            f.seek(0)
                            content = f.read().decode("utf-8")
                            ok, result = replace_srt_section(content, batch_start, batch_end, txt)
                            if ok:
                                zf.writestr(f"edited_{fname}", result)
                                processed += 1
                            else:
                                errors.append(f"{fname}: {result}")
                        except Exception as e:
                            errors.append(f"{fname}: {e}")

                if errors:
                    for err in errors:
                        st.error(err)
                if processed > 0:
                    st.success(t["t4_batch_success"].format(cnt=processed))
                    st.download_button(
                        label=t["t1_btn_download_zip"],
                        data=zip_buffer.getvalue(),
                        file_name="edited_subtitles.zip",
                        mime="application/zip",
                        type="primary",
                    )

# ----------------- TAB 5: 전체 자막 타임코드 시프트 -----------------
with tab5:
    st.subheader(t["t5_sub"])
    st.info(t["t5_info"])

    shift_files = st.file_uploader(t["t5_upload"], type=['srt', 'vtt'], accept_multiple_files=True, key="shift_files")

    col1, col2 = st.columns([1, 1])
    with col1:
        t5_sign = st.radio(t["shift_sign_lbl"], [t["shift_sign_minus"], t["shift_sign_plus"]], key="t5_shift_sign")
    with col2:
        t5_offset_str = st.text_input(t["shift_offset_lbl"], value="01:00:00", key="t5_shift_offset")

    t5_sign_char = "-" if t5_sign == t["shift_sign_minus"] else "+"

    if st.button(t["t5_btn_run"], type="primary", key="t5_run"):
        offset_ms = parse_offset_to_ms(t5_sign_char, t5_offset_str)
        if not shift_files:
            st.warning(t["t5_err_nofile"])
        elif offset_ms == 0:
            st.warning(t["t5_err_offset"])
        else:
            results =[]  # (출력파일명, 데이터)
            for f in shift_files:
                f.seek(0)
                content = f.read().decode("utf-8")
                fmt = 'vtt' if f.name.lower().endswith('.vtt') else 'srt'
                shifted = shift_subtitle_content(content, offset_ms, fmt)
                results.append((f"shifted_{f.name}", shifted))

            st.success(t["t5_success"].format(cnt=len(results), sign=t5_sign_char, offset=t5_offset_str))

            if len(results) == 1:
                out_name, out_data = results[0]
                st.download_button(
                    label=t["t2_btn_dl"].format(name=out_name),
                    data=out_data,
                    file_name=out_name,
                    mime="text/plain",
                    type="primary",
                )
            else:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    for out_name, out_data in results:
                        zf.writestr(out_name, out_data)
                st.download_button(
                    label=t["t1_btn_download_zip"],
                    data=zip_buffer.getvalue(),
                    file_name="shifted_subtitles.zip",
                    mime="application/zip",
                    type="primary",
                )
