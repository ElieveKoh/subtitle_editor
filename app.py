import streamlit as st
import requests
import re
import io
import zipfile

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
            if action_type == "완전 삭제 (기본값)":
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
        return False, "시간 형식을 다시 확인해주세요. (예: 10:00 또는 00:10:00,000)"
        
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
    if not content.strip().startswith("WEBVTT"): return False, "WEBVTT 헤더 누락"
    if "-->" not in content: return False, "타임코드(-->) 없음"
    return True, ""

def validate_srt(content):
    if "-->" not in content: return False, "타임코드(-->) 없음"
    return True, ""

# ==========================================
# 6. Streamlit 웹 UI 구성
# ==========================================
st.set_page_config(page_title="자막 자동 변환기", layout="wide")
st.title("🎬 VOD 자막 다국어 일괄 처리 & 에디터")

# 복수 URL 입력창을 위한 Session State 초기화
if 'link_count' not in st.session_state:
    st.session_state.link_count = 1

def add_link():
    st.session_state.link_count += 1

tab1, tab2, tab3, tab4 = st.tabs([
    "🌐 1. 일괄 다운로드 & 전처리", 
    "📁 2. 수동 VTT -> SRT", 
    "🔙 3. 최종 SRT -> VTT",
    "✂️ 4. 구간 자막 덮어쓰기"
])

# ----------------- TAB 1: 복수 다운로드 & 테스트 자막 컷팅 -----------------
with tab1:
    st.subheader("MP4 주소로 다국어 자막 복수 다운로드")
    st.info("➕ 버튼을 눌러 작업을 원하는 만큼 추가하세요. 언어별 자막을 설정한 파일명 규칙으로 한 번에 묶어줍니다.")
    
    st.markdown("##### 🔗 다운로드 링크 및 파일명 설정")
    links_data =[]
    
    # 동적 URL & Prefix 입력창 생성
    for i in range(st.session_state.link_count):
        col1, col2 = st.columns([2, 1])
        with col1:
            u = st.text_input(f"MP4 URL #{i+1}", key=f"url_{i}", placeholder="https://.../orig.mix-stream1.mp4")
        with col2:
            p = st.text_input(f"파일명 구조 #{i+1}", key=f"prefix_{i}", placeholder=f"예: 20260413_BTS_day{i+1}")
        links_data.append((u, p))
        
    st.button("➕ 링크 입력칸 추가", on_click=add_link)
    
    st.markdown("---")
    st.markdown("##### 🧹 옵션: 테스트 자막 정리 (다운로드 시 자동 적용)")
    
    enable_cleanup = st.checkbox("초반 자막 지우기 기능 사용", value=True)
    
    if enable_cleanup:
        col1, col2 = st.columns(2)
        with col1:
            test_min = st.number_input("기준 시간 (분 단위):", min_value=0.0, value=20.0, step=1.0)
        with col2:
            action_type = st.radio("처리 방식 선택:",["완전 삭제 (기본값)", "점(.)으로 남기기 (0.1초 노출)"])
    else:
        test_min = 0.0
        action_type = "완전 삭제 (기본값)"
    
    st.markdown("---")
    default_langs =['en', 'ja', 'zh-CN', 'zh-TW', 'th', 'id', 'vi', 'es', 'fr', 'pt', 'fil', 'ko']
    selected_langs = st.multiselect("다운로드할 언어 선택", default_langs, default=default_langs)
    
    # 자막팀 공유용으로 특별 분리할 언어 리스트
    team_share_langs =['en', 'ja', 'zh-CN', 'ko']

    if st.button("🚀 일괄 다운로드 및 변환 실행", type="primary"):
        # 비어있지 않은 유효한 링크 세트만 걸러냄
        valid_links =[(u.strip(), p.strip()) for u, p in links_data if u.strip() and p.strip()]
        
        if not valid_links:
            st.error("최소 1개 이상의 URL과 파일명을 정확히 입력해주세요.")
        else:
            zip_buffer = io.BytesIO()
            success_count = 0
            
            with st.spinner("서버에서 자막을 받고 폴더별로 자동 분류 중입니다..."):
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    
                    for url_input, prefix in valid_links:
                        base_url = url_input.rsplit('/', 1)[0]
                        
                        for lang in selected_langs:
                            target_url = f"{base_url}/sub_{lang}.vtt"
                            try:
                                res = requests.get(target_url, timeout=10)
                                res.encoding = 'utf-8'  # 한/중/일어 깨짐 방지
                                
                                if res.status_code == 200:
                                    vtt_text = res.text
                                    is_valid, msg = validate_vtt(vtt_text)
                                    
                                    if is_valid:
                                        # 1. 초반 테스트 자막 컷팅
                                        if enable_cleanup:
                                            vtt_text = process_test_subtitles(vtt_text, test_min, action_type)
                                        
                                        # 2. original_vtt 폴더에 저장
                                        zip_file.writestr(f"original_vtt/{prefix}_{lang}.vtt", vtt_text)
                                        
                                        # 3. premiere_srt 폴더에 저장
                                        srt_text = vtt_to_srt_str(vtt_text)
                                        zip_file.writestr(f"premiere_srt/{prefix}_{lang}.srt", srt_text)
                                        
                                        # 4. [특수기능] 자막팀 공유 폴더 분리 (en, ja, zh-CN, ko 만)
                                        if lang in team_share_langs:
                                            zip_file.writestr(f"{prefix}_자막팀공유/{prefix}_{lang}.vtt", vtt_text)
                                        
                                        success_count += 1
                                    else:
                                        st.warning(f"⚠️[{prefix}] {lang} 형식 오류: {msg}")
                                else:
                                    # 해당 언어 자막이 없는 경우(ex. ko가 없을 때) 조용히 스킵 (에러 띄우지 않음)
                                    pass
                            except Exception as e:
                                st.error(f"❌ [{prefix}] {lang} 처리 중 에러: {e}")

            if success_count > 0:
                st.success(f"🎉 총 {success_count}개의 파일이 성공적으로 처리되었습니다!")
                st.download_button(
                    label="📦 완성된 전체 패키지 다운로드 (.zip)",
                    data=zip_buffer.getvalue(),
                    file_name="subtitles_processed_package.zip",
                    mime="application/zip",
                    type="primary"
                )

# ----------------- TAB 2: 수동 VTT -> SRT -----------------
with tab2:
    st.subheader("📁 로컬 VTT 파일을 SRT로 수동 변환")
    uploaded_vtt = st.file_uploader("VTT 파일 업로드", type=['vtt'], accept_multiple_files=True)
    if uploaded_vtt:
        for file in uploaded_vtt:
            content = file.read().decode("utf-8")
            st.download_button(f"⬇️ {file.name.replace('.vtt', '.srt')} 다운로드", data=vtt_to_srt_str(content), file_name=file.name.replace('.vtt', '.srt'))

# ----------------- TAB 3: 수동 SRT -> VTT (최종) -----------------
with tab3:
    st.subheader("🔙 프리미어 검수 완료된 SRT를 VOD 업로드용 VTT로 변환")
    uploaded_srt = st.file_uploader("수정 완료된 SRT 업로드", type=['srt'], accept_multiple_files=True)
    if uploaded_srt:
        for file in uploaded_srt:
            content = file.read().decode("utf-8")
            new_name = file.name.replace('.srt', '_final.vtt')
            st.download_button(f"⬇️ {new_name} 다운로드", data=srt_to_vtt_str(content), file_name=new_name, type="primary")

# ----------------- TAB 4: 구간 자막 교체 & 밀어넣기 -----------------
with tab4:
    st.subheader("✂️ SRT 특정 구간 밀어내기 & 새 자막 삽입")
    st.info("지정한 시간 사이에 있는 자막을 비우고, 새로 입력한 텍스트들을 엔터(줄바꿈) 기준으로 자동 분배하여 넣습니다. (나머지 뒤쪽 자막들의 번호와 시간은 밀리지 않고 유지됩니다)")
    
    uploaded_edit = st.file_uploader("수정할 원본 SRT 파일 업로드", type=['srt'])
    
    col1, col2 = st.columns([1, 2])
    with col1:
        start_time_input = st.text_input("교체 시작 시간 (예: 10:00 또는 00:10:00)", value="10:00")
        end_time_input = st.text_input("교체 종료 시간 (예: 11:00 또는 00:11:00)", value="11:00")
        
    with col2:
        new_subtitles = st.text_area("새로 넣을 자막 텍스트 입력 (엔터키를 기준으로 분할됩니다)", height=200, 
                                     placeholder="안녕하세요.\n반갑습니다.\n이 줄바꿈 그대로 자막이 나뉩니다.")
        
    if st.button("✨ 구간 교체 적용하고 다운로드"):
        if uploaded_edit and start_time_input and end_time_input:
            srt_content = uploaded_edit.read().decode("utf-8")
            success, result = replace_srt_section(srt_content, start_time_input, end_time_input, new_subtitles)
            
            if success:
                st.success("✅ 자막 교체 및 인덱스 정렬 완료!")
                st.download_button(
                    label=f"⬇️ 수정된 {uploaded_edit.name} 다운로드",
                    data=result,
                    file_name=f"edited_{uploaded_edit.name}",
                    mime="text/plain",
                    type="primary"
                )
            else:
                st.error(result)
        else:
            st.warning("원본 SRT 파일, 시작/종료 시간, 추가할 자막을 모두 입력해주세요.")
