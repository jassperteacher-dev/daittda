import streamlit as st
import time
import json
import re
import google.generativeai as genai

# --- 1. 페이지 기본 설정 ---
st.set_page_config(page_title="다잇다 시스템", layout="wide", initial_sidebar_state="collapsed")

# --- 2. 상태 관리 (Session State) ---
if 'db' not in st.session_state:
    st.session_state.db =[
        {"id": 1, "target": "초등학생 학부모", "goal": "2026 교육과정 변화를 이해하고 자녀의 학습 방향을 설정"},
        {"id": 2, "target": "중학생 학부모", "goal": "고등학교 입시 준비 전략을 세우고 내신 관리법을 파악"},
        {"id": 3, "target": "고등학생 학부모", "goal": "수시·정시 전략을 비교하고 맞춤 입시 전략을 수립"},
        {"id": 4, "target": "재수생 학부모", "goal": "수능 재도전 전략과 학습 로드맵을 구체적으로 계획"},
        {"id": 5, "target": "교육에 관심 있는 학부모", "goal": "최신 교육 트렌드와 정책 변화를 빠르게 파악"},
    ]
if 'selected_target' not in st.session_state:
    st.session_state.selected_target = None
if 'generated' not in st.session_state:
    st.session_state.generated = False

# --- 3. 커스텀 CSS 디자인 ---
st.markdown("""
    <style>
    .top-header {
        background-color: #1A1A1A; padding: 15px 20px; color: white; border-bottom: 3px solid #F59E0B;
        display: flex; justify-content: space-between; align-items: center; border-radius: 5px; margin-bottom: 20px;
    }
    .logo-text { font-size: 20px; font-weight: bold; }
    .logo-text span { color: #F59E0B; }
    .status-badges span {
        background-color: #333; padding: 5px 10px; border-radius: 15px; font-size: 12px; margin-left: 10px; border: 1px solid #555;
    }
    .status-ai { color: #10B981 !important; border-color: #10B981 !important; background-color: rgba(16, 185, 129, 0.1) !important;}
    .info-box { background-color: white; border: 1px solid #E5E7EB; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    </style>
""", unsafe_allow_html=True)

# --- 4. 구글 Gemini API 호출 함수 ---
def generate_blog_with_gemini(api_key, nlm_text, target, goal):
    genai.configure(api_key=api_key)
    # 구글의 최신 무료/고속 모델 사용
    model = genai.GenerativeModel('gemini-1.5-flash') 
    
    prompt = f"""
    당신은 대한민국 최고의 교육 전문 블로거입니다. 
    제공된 [참고자료]를 바탕으로 [대상]과 [목적]에 맞는 블로그 포스팅 초안을 작성해주세요.
    반드시 아래의 JSON 형식으로만 출력해야 하며, 앞뒤에 설명이나 마크다운(```json) 기호를 넣지 말고 오직 중괄호 {{ 로 시작해서 }} 로 끝나는 JSON만 출력하세요.
    
    [대상] {target}
    [목적] {goal}
    
    [참고자료]
    {nlm_text[:2000]}
    
    [출력 JSON 형식]
    {{
        "title": "매력적인 블로그 제목",
        "subtitle": "클릭을 유도하는 서브 타이틀",
        "intro": "독자의 공감을 이끌어내는 전문적인 도입부 (3~4문장)",
        "sections":[
            {{"title": "본문 소제목 1", "content": "본문 내용 1 (4~5문장)"}},
            {{"title": "본문 소제목 2", "content": "본문 내용 2 (4~5문장)"}},
            {{"title": "본문 소제목 3", "content": "본문 내용 3 (4~5문장)"}}
        ],
        "conclusion": "내용 요약 및 다잇다 카카오톡 채널 추가 유도 (3문장)",
        "hashtags":["다잇다", "입시전략", "태그1", "태그2", "태그3"]
    }}
    """
    response = model.generate_content(prompt)
    return response.text


# --- 5. 화면 UI 구성 ---
st.markdown(f"""
    <div class="top-header">
        <div class="logo-text">다<span>잇</span>다 <span style="font-size:14px; color:#888; font-weight:normal; margin-left:10px;">교육정보 콘텐츠 자동생성 시스템</span></div>
        <div class="status-badges">
            <span class="status-ai">● AI 연결 대기중 (Gemini)</span>
            <span>DB {len(st.session_state.db)}건</span>
        </div>
    </div>
""", unsafe_allow_html=True)

st.markdown("**🟡 1. 정보 입력** &nbsp; → &nbsp; ⚪ 2. 대상·목적 설정 &nbsp; → &nbsp; ⚪ 3. 블로그 생성 &nbsp; → &nbsp; ⚪ 4. 숏츠 완성")
st.divider()

col_left, col_right = st.columns([4, 6], gap="large")

# ==========================================
# 왼쪽 패널 (정보 입력 영역)
# ==========================================
with col_left:
    st.markdown("#### 🔑 구글 API 키 입력")
    api_key = st.text_input("Google AI Studio에서 발급받은 API 키를 넣으세요", type="password", placeholder="AIzaSy...")
    st.write("")

    st.markdown("#### 📁 NotebookLM 가공 정보 🔴필수")
    nlm_text = st.text_area("내용을 입력하세요", height=200, placeholder="여기에 교육 관련 정보를 붙여넣으세요...", label_visibility="collapsed")
    
    st.markdown("#### 🎯 대상 & 목적 설정 🔴필수")
    for item in st.session_state.db:
        is_selected = st.session_state.selected_target == item
        border_color = "#3B82F6" if is_selected else "#E5E7EB"
        bg_color = "#EFF6FF" if is_selected else "white"
        
        with st.container():
            st.markdown(f"""
                <div style="border: 2px solid {border_color}; background-color: {bg_color}; border-radius: 8px; padding: 10px; margin-bottom: 10px;">
                    <strong style="color: #3B82F6;">{item['target']}</strong><br>
                    <span style="color: #4B5563; font-size: 14px;">{item['goal']}</span>
                </div>
            """, unsafe_allow_html=True)
            
            btn_col1, btn_col2 = st.columns([8, 2])
            if btn_col1.button("이 대상 선택", key=f"sel_{item['id']}", use_container_width=True):
                st.session_state.selected_target = item
                st.rerun()
            if btn_col2.button("❌", key=f"del_{item['id']}"):
                st.session_state.db.remove(item)
                if st.session_state.selected_target == item:
                    st.session_state.selected_target = None
                st.rerun()

    st.divider()
    if st.session_state.selected_target:
        st.info(f"✅ **선택됨:** {st.session_state.selected_target['target']}")
        
        if st.button("🚀 자동 생성 시작", type="primary", use_container_width=True):
            if not api_key:
                st.error("구글 API 키를 먼저 입력해주세요!")
            elif len(nlm_text) < 10:
                st.error("NotebookLM 가공 정보를 충분히 입력해주세요! (최소 10자)")
            else:
                st.session_state.generated = True
                st.rerun()

# ==========================================
# 오른쪽 패널 (미리보기 및 결과 영역)
# ==========================================
with col_right:
    if not st.session_state.generated:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; font-size: 60px;'>🦉 🐻 🐿️</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: #4B5563;'>콘텐츠가 여기에 자동으로 생성됩니다</h3>", unsafe_allow_html=True)
        
    else:
        # 생성 버튼을 누른 후 (실제 구글 API 작동 부분)
        with st.spinner("✨ 구글 Gemini AI가 블로그 포스팅을 열심히 작성하고 있습니다... (약 5~10초 소요)"):
            target = st.session_state.selected_target['target']
            goal = st.session_state.selected_target['goal']
            
            try:
                # 1. API 호출
                raw_result = generate_blog_with_gemini(api_key, nlm_text, target, goal)
                
                # 2. 결과물에서 불필요한 마크다운(```json) 찌꺼기 제거
                clean_json_str = re.sub(r"```json\n?", "", raw_result)
                clean_json_str = re.sub(r"```\n?", "", clean_json_str).strip()
                
                # 3. JSON 변환
                blog_data = json.loads(clean_json_str)
                
                st.success("🎉 블로그 콘텐츠 생성이 완료되었습니다!")
                
                # 4. 화면에 예쁘게 출력
                tab1, tab2, tab3 = st.tabs(["📝 블로그 결과물", "📖 웹툰/카드뉴스", "🎬 숏츠 대본"])
                
                with tab1:
                    st.markdown(f"## {blog_data.get('title', '제목 없음')}")
                    st.markdown(f"**{blog_data.get('subtitle', '')}**")
                    st.write("---")
                    
                    st.info(blog_data.get('intro', ''))
                    st.write("")
                    
                    for idx, section in enumerate(blog_data.get('sections',[])):
                        st.markdown(f"### 📍 {section.get('title', '')}")
                        st.write(section.get('content', ''))
                        # 카드뉴스 들어갈 자리 표시
                        st.markdown(f"> *🖼️ (여기에 {idx+1}번째 카드뉴스 이미지가 들어갑니다)*")
                        st.write("")
                    
                    st.success(blog_data.get('conclusion', ''))
                    
                    # 해시태그 출력
                    tags = " ".join([f"#{tag}" for tag in blog_data.get('hashtags', [])])
                    st.markdown(f"<span style='color:#3B82F6; font-weight:bold;'>{tags}</span>", unsafe_allow_html=True)

                with tab2:
                    st.write("웹툰 및 카드뉴스 자동 생성 기능은 준비 중입니다.")
                with tab3:
                    st.write("숏츠 대본 자동 생성 기능은 준비 중입니다.")

            except json.JSONDecodeError:
                st.error("AI가 형식에 맞지 않는 글을 작성했습니다. '다시 만들기'를 눌러주세요.")
                st.expander("AI 원본 응답 보기").write(raw_result)
            except Exception as e:
                st.error(f"API 호출 중 에러가 발생했습니다: {e}")

        st.write("---")
        if st.button("🔄 돌아가기 (다시 만들기)", use_container_width=True):
            st.session_state.generated = False
            st.rerun()
