import streamlit as st\
import requests\
import re\
import io\
import zipfile\
from urllib.parse import urlparse\
\
# ==========================================\
# 1. \uc0\u53076 \u50612  \u48320 \u54872  \u54632 \u49688  (\u47700 \u47784 \u47532  \u49345 \u50640 \u49436  \u47928 \u51088 \u50676 \u47196  \u52376 \u47532 )\
# ==========================================\
def format_time_for_srt(tc):\
    tc = tc.strip().replace('.', ',')\
    if tc.count(':') == 1:\
        tc = f"00:\{tc\}"\
    return tc\
\
def vtt_to_srt_str(vtt_content):\
    blocks = re.split(r'\\n\\s*\\n', vtt_content.strip())\
    srt_lines = []\
    index = 1\
    for block in blocks:\
        lines = block.split('\\n')\
        if 'WEBVTT' in lines[0] or 'NOTE' in lines[0]: continue\
        \
        tc_idx = next((i for i, line in enumerate(lines) if '-->' in line), -1)\
        if tc_idx == -1: continue\
\
        tc_line = re.sub(r'\\s*align:.*', '', lines[tc_idx])\
        start_time, end_time = tc_line.split('-->')\
        srt_tc = f"\{format_time_for_srt(start_time)\} --> \{format_time_for_srt(end_time)\}"\
        text_lines = lines[tc_idx+1:]\
\
        srt_lines.extend([str(index), srt_tc] + text_lines + [""])\
        index += 1\
    return "\\n".join(srt_lines)\
\
def srt_to_vtt_str(srt_content):\
    blocks = re.split(r'\\n\\s*\\n', srt_content.strip())\
    vtt_lines = ["WEBVTT\\n"]\
    for block in blocks:\
        lines = block.split('\\n')\
        if len(lines) < 3: continue\
        \
        tc_idx = next((i for i, line in enumerate(lines) if '-->' in line), -1)\
        if tc_idx == -1: continue\
\
        tc_line = lines[tc_idx].replace(',', '.')\
        text_lines = lines[tc_idx+1:]\
        vtt_lines.extend([tc_line] + text_lines + [""])\
    return "\\n".join(vtt_lines)\
\
# ==========================================\
# 2. Validation (\uc0\u44160 \u51613 ) \u54632 \u49688 \
# ==========================================\
def validate_vtt(content):\
    if not content.strip().startswith("WEBVTT"):\
        return False, "WEBVTT \uc0\u54756 \u45908 \u44032  \u45572 \u46973 \u46104 \u50632 \u49845 \u45768 \u45796 ."\
    if "-->" not in content:\
        return False, "\uc0\u53440 \u51076 \u53076 \u46300 (-->)\u44032  \u51316 \u51116 \u54616 \u51648  \u50506 \u49845 \u45768 \u45796 ."\
    return True, "\uc0\u51221 \u49345  VTT \u54028 \u51068 \u51077 \u45768 \u45796 ."\
\
def validate_srt(content):\
    if "-->" not in content:\
        return False, "\uc0\u53440 \u51076 \u53076 \u46300 (-->)\u44032  \u51316 \u51116 \u54616 \u51648  \u50506 \u49845 \u45768 \u45796 ."\
    if "." in re.findall(r'\\d\{2\}:\\d\{2\}:\\d\{2\}([.,])\\d\{3\}', content):\
        return False, "SRT \uc0\u48128 \u47532 \u52488  \u44396 \u48516 \u51088 \u45716  \u51216 (.)\u51060  \u50500 \u45772  \u49788 \u54364 (,)\u50668 \u50556  \u54633 \u45768 \u45796 ."\
    return True, "\uc0\u51221 \u49345  SRT \u54028 \u51068 \u51077 \u45768 \u45796 ."\
\
# ==========================================\
# 3. Streamlit \uc0\u50937  UI\
# ==========================================\
st.set_page_config(page_title="\uc0\u51088 \u47561  \u51088 \u46041  \u48320 \u54872 \u44592 ", layout="wide")\
st.title("\uc0\u55356 \u57260  VOD \u51088 \u47561  \u51088 \u46041  \u45796 \u50868 \u47196 \u46300  & \u48320 \u54872 \u44592 ")\
st.markdown("VTT \uc0\u51088 \u46041  \u45796 \u50868 \u47196 \u46300 , \u54532 \u47532 \u48120 \u50612 \u50857  SRT \u48320 \u54872 , \u44160 \u49688  \u54980  VTT \u48373 \u44396 \u47484  \u50937 \u50640 \u49436  \u52376 \u47532 \u54633 \u45768 \u45796 .")\
\
# \uc0\u53485  \u49373 \u49457 \
tab1, tab2, tab3 = st.tabs(["\uc0\u55356 \u57104  URL \u45796 \u50868 \u47196 \u46300  & SRT \u48320 \u54872 ", "\u55357 \u56513  \u49688 \u46041  VTT -> SRT", "\u55357 \u56601  \u52572 \u51333  SRT -> VTT (VOD\u50857 )"])\
\
# ----------------- TAB 1: URL \uc0\u45796 \u50868 \u47196 \u46300  -----------------\
with tab1:\
    st.subheader("1. MP4 \uc0\u51452 \u49548 \u47196  \u45796 \u44397 \u50612  \u51088 \u47561  \u51068 \u44292  \u45796 \u50868 \u47196 \u46300 ")\
    url_input = st.text_input("MP4 URL \uc0\u51077 \u47141 :", placeholder="https://.../orig.mix-stream1.mp4")\
    \
    # \uc0\u44592 \u48376  \u50616 \u50612  \u47532 \u49828 \u53944 \
    default_langs = ['en', 'ja', 'zh-cn', 'zh-tw', 'th', 'id', 'vi', 'es', 'fr', 'pt', 'fil', 'ko']\
    selected_langs = st.multiselect("\uc0\u45796 \u50868 \u47196 \u46300 \u54624  \u50616 \u50612  \u49440 \u53469 ", default_langs, default=default_langs)\
\
    if st.button("\uc0\u55357 \u56960  \u51088 \u47561  \u45796 \u50868 \u47196 \u46300  \u48143  SRT \u48320 \u54872  \u49892 \u54665 "):\
        if not url_input:\
            st.error("URL\uc0\u51012  \u51077 \u47141 \u54644 \u51452 \u49464 \u50836 .")\
        else:\
            base_url = url_input.rsplit('/', 1)[0]\
            \
            # ZIP \uc0\u54028 \u51068  \u49373 \u49457 \u51012  \u50948 \u54620  \u47700 \u47784 \u47532  \u48260 \u54140 \
            zip_buffer = io.BytesIO()\
            success_count = 0\
            \
            with st.spinner("\uc0\u49436 \u48260 \u50640 \u49436  \u51088 \u47561 \u51012  \u52286 \u44256  \u45796 \u50868 \u47196 \u46300  \u51473 \u51077 \u45768 \u45796 ..."):\
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:\
                    for lang in selected_langs:\
                        target_url = f"\{base_url\}/sub_\{lang\}.vtt"\
                        try:\
                            res = requests.get(target_url, timeout=10)\
                            if res.status_code == 200:\
                                vtt_text = res.text\
                                is_valid, msg = validate_vtt(vtt_text)\
                                \
                                if is_valid:\
                                    # \uc0\u50896 \u48376  VTT \u51200 \u51109 \
                                    zip_file.writestr(f"original_vtt/sub_\{lang\}.vtt", vtt_text)\
                                    # \uc0\u54532 \u47532 \u48120 \u50612 \u50857  SRT\u47196  \u48320 \u54872 \u54616 \u50668  \u51200 \u51109 \
                                    srt_text = vtt_to_srt_str(vtt_text)\
                                    zip_file.writestr(f"premiere_srt/sub_\{lang\}.srt", srt_text)\
                                    success_count += 1\
                                    st.success(f"\uc0\u9989  \{lang\} \u51088 \u47561  \u45796 \u50868 \u47196 \u46300  \u48143  \u48320 \u54872  \u49457 \u44277 ")\
                                else:\
                                    st.warning(f"\uc0\u9888 \u65039  \{lang\} \u54028 \u51068  \u54805 \u49885  \u50724 \u47448 : \{msg\}")\
                            else:\
                                st.info(f"\uc0\u9197 \u65039  \{lang\} \u51088 \u47561  \u50630 \u51020  (HTTP \{res.status_code\})")\
                        except Exception as e:\
                            st.error(f"\uc0\u10060  \{lang\} \u52376 \u47532  \u51473  \u50640 \u47084 : \{e\}")\
\
            if success_count > 0:\
                st.write("### \uc0\u55356 \u57225  \u48320 \u54872  \u50756 \u47308 !")\
                st.download_button(\
                    label="\uc0\u55357 \u56550  \u48320 \u54872 \u46108  \u47784 \u46304  \u54028 \u51068  \u45796 \u50868 \u47196 \u46300  (.zip)",\
                    data=zip_buffer.getvalue(),\
                    file_name="subtitles_converted.zip",\
                    mime="application/zip",\
                    type="primary"\
                )\
\
# ----------------- TAB 2: \uc0\u49688 \u46041  VTT -> SRT -----------------\
with tab2:\
    st.subheader("VTT \uc0\u54028 \u51068 \u51012  \u54532 \u47532 \u48120 \u50612 \u50857  SRT\u47196  \u48320 \u54872 ")\
    uploaded_vtt = st.file_uploader("VTT \uc0\u54028 \u51068  \u50629 \u47196 \u46300 ", type=['vtt'], accept_multiple_files=True)\
    \
    if uploaded_vtt:\
        for file in uploaded_vtt:\
            content = file.read().decode("utf-8")\
            is_valid, msg = validate_vtt(content)\
            \
            if is_valid:\
                srt_result = vtt_to_srt_str(content)\
                new_name = file.name.replace('.vtt', '.srt')\
                st.download_button(f"\uc0\u11015 \u65039  \{new_name\} \u45796 \u50868 \u47196 \u46300 ", data=srt_result, file_name=new_name, mime="text/plain")\
            else:\
                st.error(f"\{file.name\} \uc0\u44160 \u51613  \u49892 \u54056 : \{msg\}")\
\
# ----------------- TAB 3: \uc0\u49688 \u46041  SRT -> VTT (\u52572 \u51333 ) -----------------\
with tab3:\
    st.subheader("\uc0\u54532 \u47532 \u48120 \u50612  \u44160 \u49688  \u50756 \u47308 \u46108  SRT\u47484  \u45796 \u49884  VOD\u50857  VTT\u47196  \u48320 \u54872 ")\
    st.info("\uc0\u51060 \u44275 \u50640  \u49688 \u51221  \u50756 \u47308 \u46108  SRT \u54028 \u51068 \u51012  \u50629 \u47196 \u46300 \u54616 \u47732  \u52572 \u51333  VOD \u50629 \u47196 \u46300 \u50857  VTT\u47196  \u48320 \u54872 \u46121 \u45768 \u45796 .")\
    uploaded_srt = st.file_uploader("SRT \uc0\u54028 \u51068  \u50629 \u47196 \u46300 ", type=['srt'], accept_multiple_files=True)\
    \
    if uploaded_srt:\
        for file in uploaded_srt:\
            content = file.read().decode("utf-8")\
            is_valid, msg = validate_srt(content)\
            \
            if is_valid:\
                vtt_result = srt_to_vtt_str(content)\
                new_name = file.name.replace('.srt', '_final.vtt')\
                st.download_button(f"\uc0\u11015 \u65039  \{new_name\} \u45796 \u50868 \u47196 \u46300 ", data=vtt_result, file_name=new_name, mime="text/plain", type="primary")\
            else:\
                st.error(f"\{file.name\} \uc0\u44160 \u51613  \u49892 \u54056 : \{msg\}")}
