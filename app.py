import streamlit as st
import requests
import re
import io
import zipfile
from urllib.parse import urlparse

# ==========================================
# 1. 코어 변환 함수 (메모리 상에서 문자열로 처리)
# ==========================================
def format_time_for_srt(tc):
    tc = tc.strip().replace('.', ',')
    if tc.count(':') == 1:
        tc = f"00:{tc}"
    return tc

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
# 2. Validation (검증) 함수
# ==========================================
def validate_vtt(content):
    if not content.strip().startswith("WEBVTT"):
        return False, "WEBVTT 헤더가 누락되었습니다."
    if "-->" not in content:
        return False, "타임코드(-->)가 존재하지 않습니다."
    return True, "정상 VTT 파일입니다."

def validate_srt(content):
    if "-->" not in content:
        return False, "타임코드(-->)가 존재하지 않습니다."
    if "." in re.findall(r'\d{2}:\d{2}:\d{2}([.,])\d{3}', content):
        return False, "SRT 밀리초 구분자는 점(.)이 아닌 쉼표(,)여야 합니다."
    return True, "정상 SRT 파일입니다."

# ==========================================
# 3. Streamlit 웹 UI
# ==========================================
st.set_page_config(page_title="자막 자동 변환기", layout="wide")
st.title("🎬 VOD 자막 자동 다운로드 & 변환기")
st.markdown("VTT 자동 다운로드, 프리미어용 SRT 변환, 검수 후 VTT 복구를 웹에서 처리합니다.")

# 탭 생성
tab1, tab2, tab3 = st.tabs(["🌐 URL 다운로드 & SRT 변환", "📁 수동 VTT -> SRT", "🔙 최종 SRT -> VTT (VOD용)"])

# ----------------- TAB 1: URL 다운로드 -----------------
with tab1:
    st.subheader("1. MP4 주소로 다국어 자막 일괄 다운로드")
    url_input = st.text_input("MP4 URL 입력:", placeholder="https://.../orig.mix-stream1.mp4")
    
    # 기본 언어 리스트
    default_langs =['en', 'ja', 'zh-cn', 'zh-tw', 'th', 'id', 'vi', 'es', 'fr', 'pt', 'fil', 'ko']
    selected_langs = st.multiselect("다운로드할 언어 선택", default_langs, default=default_langs)

    if st.button("🚀 자막 다운로드 및 SRT 변환 실행"):
        if not url_input:
            st.error("URL을 입력해주세요.")
        else:
            base_url = url_input.rsplit('/', 1)[0]
            
            # ZIP 파일 생성을 위한 메모리 버퍼
            zip_buffer = io.BytesIO()
            success_count = 0
            
            with st.spinner("서버에서 자막을 찾고 다운로드 중입니다..."):
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for lang in selected_langs:
                        target_url = f"{base_url}/sub_{lang}.vtt"
                        try:
                            res = requests.get(target_url, timeout=10)
                            if res.status_code == 200:
                                vtt_text = res.text
                                is_valid, msg = validate_vtt(vtt_text)
                                
                                if is_valid:
                                    # 원본 VTT 저장
                                    zip_file.writestr(f"original_vtt/sub_{lang}.vtt", vtt_text)
                                    # 프리미어용 SRT로 변환하여 저장
                                    srt_text = vtt_to_srt_str(vtt_text)
                                    zip_file.writestr(f"premiere_srt/sub_{lang}.srt", srt_text)
                                    success_count += 1
                                    st.success(f"✅ {lang} 자막 다운로드 및 변환 성공")
                                else:
                                    st.warning(f"⚠️ {lang} 파일 형식 오류: {msg}")
                            else:
                                st.info(f"⏭️ {lang} 자막 없음 (HTTP {res.status_code})")
                        except Exception as e:
                            st.error(f"❌ {lang} 처리 중 에러: {e}")

            if success_count > 0:
                st.write("### 🎉 변환 완료!")
                st.download_button(
                    label="📦 변환된 모든 파일 다운로드 (.zip)",
                    data=zip_buffer.getvalue(),
                    file_name="subtitles_converted.zip",
                    mime="application/zip",
                    type="primary"
                )

# ----------------- TAB 2: 수동 VTT -> SRT -----------------
with tab2:
    st.subheader("VTT 파일을 프리미어용 SRT로 변환")
    uploaded_vtt = st.file_uploader("VTT 파일 업로드", type=['vtt'], accept_multiple_files=True)
    
    if uploaded_vtt:
        for file in uploaded_vtt:
            content = file.read().decode("utf-8")
            is_valid, msg = validate_vtt(content)
            
            if is_valid:
                srt_result = vtt_to_srt_str(content)
                new_name = file.name.replace('.vtt', '.srt')
                st.download_button(f"⬇️ {new_name} 다운로드", data=srt_result, file_name=new_name, mime="text/plain")
            else:
                st.error(f"{file.name} 검증 실패: {msg}")

# ----------------- TAB 3: 수동 SRT -> VTT (최종) -----------------
with tab3:
    st.subheader("프리미어 검수 완료된 SRT를 다시 VOD용 VTT로 변환")
    st.info("이곳에 수정 완료된 SRT 파일을 업로드하면 최종 VOD 업로드용 VTT로 변환됩니다.")
    uploaded_srt = st.file_uploader("SRT 파일 업로드", type=['srt'], accept_multiple_files=True)
    
    if uploaded_srt:
        for file in uploaded_srt:
            content = file.read().decode("utf-8")
            is_valid, msg = validate_srt(content)
            
            if is_valid:
                vtt_result = srt_to_vtt_str(content)
                new_name = file.name.replace('.srt', '_final.vtt')
                st.download_button(f"⬇️ {new_name} 다운로드", data=vtt_result, file_name=new_name, mime="text/plain", type="primary")
            else:
                st.error(f"{file.name} 검증 실패: {msg}")
