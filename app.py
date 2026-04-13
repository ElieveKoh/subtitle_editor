import streamlit as st
import requests
import re
import io
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
        "t1_btn_run": "🚀 일괄 다운로드 및 변환 실행",
        
        "t1_err_nolink": "최소 1개 이상의 URL과 파일명을 정확히 입력해주세요.",
        "t1_sp_loading": "서버에서 자막을 받고 폴더별로 자동 분류 중입니다...",
        "t1_msg_success": "✅ [{prefix}] {lang} 처리 완료",
        "t1_msg_err_fmt": "⚠️ [{prefix}] {lang} 형식 오류: {msg}",
        "t1_msg_err_sys": "❌ [{prefix}] {lang} 처리 중 에러: {e}",
        "t1_success_all": "🎉 총 {cnt}개의 파일이 성공적으로 처리되었습니다!",
        "t1_btn_download_zip": "📦 완성된 전체 패키지 다운로드 (.zip)",
        "t1_share_folder": "자막팀공유",
        
        # 탭 2 & 3 (수동 변환)
        "t2_sub": "📁 로컬 VTT 파일을 SRT로 수동 변환",
        "t2_upload": "VTT 파일 업로드",
        "t2_btn_dl": "⬇️ {name} 다운로드",
        
        "t3_sub": "🔙 프리미어 검수 완료된 SRT를 VOD 업로드용 VTT로 변환",
        "t3_upload": "수정 완료된 SRT 업로드",
        "t3_btn_dl": "⬇️ {name} 다운로드",
        
        # 탭 4 (에디터)
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
        
        # 검증 에러 메시지
        "err_vtt_header": "WEBVTT 헤더 누락",
        "err_tc": "타임코드(-->) 없음"
    },
    "English": {
        "app_title": "🎬 VOD Subtitle Batch Processor & Editor",
        "tab1": "🌐 1. Batch Download & Pre-process",
        "tab2": "📁 2. Manual VTT -> SRT",
        "tab3": "🔙 3. Final SRT -> VTT",
        "tab4": "✂️ 4. Override Subtitle Section",
        
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
        "t1_btn_run": "🚀 Run Batch Download & Convert",
        
        "t1_err_nolink": "Please enter at least one valid URL and filename prefix.",
        "t1_sp_loading": "Downloading subtitles and organizing folders...",
        "t1_msg_success": "✅ [{prefix}] {lang} processed",
        "t1_msg_err_fmt": "⚠️ [{prefix}] {lang} Format Error: {msg}",
        "t1_msg_err_sys": "❌ [{prefix}] {lang} System Error: {e}",
        "t1_success_all": "🎉 A total of {cnt} files processed successfully!",
        "t1_btn_download_zip": "📦 Download Complete Package (.zip)",
        "t1_share_folder": "Team_Share",
        
        # Tab 2 & 3 (Manual Convert)
        "t2_sub": "📁 Manually convert local VTT to SRT",
        "t2_upload": "Upload VTT file(s)",
        "t2_btn_dl": "⬇️ Download {name}",
        
        "t3_sub": "🔙 Convert reviewed SRT back to VOD VTT",
        "t3_upload": "Upload modified SRT file(s)",
        "t3_btn_dl": "⬇️ Download {name}",
        
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
        
        # Validation Errors
        "err_vtt_header": "Missing WEBVTT header",
        "err_tc": "Missing timecode (-->)"
    }
}

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
# 5. Validation 함수
# ==========================================
def validate_vtt(content):
    if not content.strip().startswith("WEBVTT"): return False, t["err_vtt_header"]
    if "-->" not in content: return False, t["err_tc"]
    return True, ""

def validate_srt(content):
    if "-->" not in content: return False, t["err_tc"]
    return True, ""

# ==========================================
# 6. Streamlit 웹 UI 구성
# ==========================================
st.title(t["app_title"])

if 'link_count' not in st.session_state:
    st.session_state.link_count = 1

def add_link():
    st.session_state.link_count += 1

tab1, tab2, tab3, tab4 = st.tabs([t["tab1"], t["tab2"], t["tab3"], t["tab4"]])

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
    default_langs =['en', 'ja', 'zh-CN', 'zh-TW', 'th', 'id', 'vi', 'es', 'fr', 'pt', 'fil', 'ko']
    selected_langs = st.multiselect(t["t1_lang_label"], default_langs, default=default_langs)
    
    team_share_langs =['en', 'ja', 'zh-CN', 'ko']

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
                                    pass
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

# ----------------- TAB 2: 수동 VTT -> SRT -----------------
with tab2:
    st.subheader(t["t2_sub"])
    uploaded_vtt = st.file_uploader(t["t2_upload"], type=['vtt'], accept_multiple_files=True)
    if uploaded_vtt:
        for file in uploaded_vtt:
            content = file.read().decode("utf-8")
            btn_txt = t["t2_btn_dl"].format(name=file.name.replace('.vtt', '.srt'))
            st.download_button(btn_txt, data=vtt_to_srt_str(content), file_name=file.name.replace('.vtt', '.srt'))

# ----------------- TAB 3: 수동 SRT -> VTT (최종) -----------------
with tab3:
    st.subheader(t["t3_sub"])
    uploaded_srt = st.file_uploader(t["t3_upload"], type=['srt'], accept_multiple_files=True)
    if uploaded_srt:
        for file in uploaded_srt:
            content = file.read().decode("utf-8")
            new_name = file.name.replace('.srt', '_final.vtt')
            btn_txt = t["t3_btn_dl"].format(name=new_name)
            st.download_button(btn_txt, data=srt_to_vtt_str(content), file_name=new_name, type="primary")

# ----------------- TAB 4: 구간 자막 교체 & 밀어넣기 -----------------
with tab4:
    st.subheader(t["t4_sub"])
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
