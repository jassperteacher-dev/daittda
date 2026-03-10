import streamlit as st
import time

# --- 1. 페이지 기본 설정 ---
st.set_page_config(page_title="다잇다 시스템", layout="wide", initial_sidebar_state="collapsed")

# --- 2. 상태 관리 (Session State) ---
# 데이터베이스(DB) 초기화
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

# --- 3. 커스텀 CSS 디자인 (스크린샷 스타일 반영) ---
st.markdown("""
    <style>
    /* 상단 헤더 스타일 */
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
    
    /* 오른쪽 안내 박스 스타일 */
    .info-box {
        background-color: white; border: 1px solid #E5E7EB; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- 4. 화면 UI 구성 ---

# [상단 헤더]
st.markdown(f"""
    <div class="top-header">
        <div class="logo-text">다<span>잇</span>다 <span style="font-size:14px; color:#888; font-weight:normal; margin-left:10px;">교육정보 콘텐츠 자동생성 시스템</span></div>
        <div class="status-badges">
            <span class="status-ai">● AI 연결됨</span>
            <span>DB {len(st.session_state.db)}건</span>
        </div>
    </div>
""", unsafe_allow_html=True)

# 스텝 표시 (간단히 텍스트로 구현)
st.markdown("**🟡 1. 정보 입력** &nbsp; → &nbsp; ⚪ 2. 대상·목적 설정 &nbsp; → &nbsp; ⚪ 3. 블로그 생성 &nbsp; → &nbsp; ⚪ 4. 숏츠 완성")
st.divider()

# 좌/우 화면 분할 (비율 4 : 6)
col_left, col_right = st.columns([4, 6], gap="large")

# ==========================================
# 왼쪽 패널 (정보 입력 영역)
# ==========================================
with col_left:
    st.markdown("#### 📁 NotebookLM 가공 정보 🔴필수")
    nlm_text = st.text_area(
        "내용을 입력하세요", 
        height=250, 
        placeholder="친구들과 수능 공부를 끌고 나갈 수 있도록...",
        label_visibility="collapsed"
    )
    st.caption(f"{len(nlm_text)}자 입력됨")
    st.write("")

    st.markdown("#### 🎯 대상 & 목적 설정 🔴필수")
    
    # DB 목록 출력 및 선택
    for item in st.session_state.db:
        # 선택된 아이템은 테두리 색상 강조
        is_selected = st.session_state.selected_target == item
        border_color = "#3B82F6" if is_selected else "#E5E7EB"
        bg_color = "#EFF6FF" if is_selected else "white"
        
        with st.container():
            # 카드 디자인 느낌을 주기 위해 HTML/CSS 적용
            st.markdown(f"""
                <div style="border: 2px solid {border_color}; background-color: {bg_color}; border-radius: 8px; padding: 10px; margin-bottom: 10px; cursor: pointer;">
                    <strong style="color: #3B82F6;">{item['target']}</strong><br>
                    <span style="color: #4B5563; font-size: 14px;">{item['goal']}</span>
                </div>
            """, unsafe_allow_html=True)
            
            # 카드 바로 아래에 선택/삭제 버튼 배치 (Streamlit의 한계상 버튼을 외부로 뺌)
            btn_col1, btn_col2 = st.columns([8, 2])
            if btn_col1.button("이 대상 선택", key=f"sel_{item['id']}", use_container_width=True):
                st.session_state.selected_target = item
                st.rerun()
            if btn_col2.button("❌", key=f"del_{item['id']}", help="삭제"):
                st.session_state.db.remove(item)
                if st.session_state.selected_target == item:
                    st.session_state.selected_target = None
                st.rerun()

    # 새 대상/목적 추가 기능
    with st.expander("➕ 새 대상·목적 추가"):
        new_target = st.text_input("대상 (예: 초등학생 학부모)")
        new_goal = st.text_input("목적 (예: 입시 전략 파악)")
        if st.button("추가하기"):
            if new_target and new_goal:
                st.session_state.db.append({"id": int(time.time()), "target": new_target, "goal": new_goal})
                st.success("추가되었습니다!")
                st.rerun()
            else:
                st.warning("대상과 목적을 모두 입력해주세요.")

    # 하단: 선택된 대상 요약 & 생성 버튼
    st.divider()
    if st.session_state.selected_target:
        st.info(f"✅ **선택됨:** {st.session_state.selected_target['target']}\n\n**목적:** {st.session_state.selected_target['goal']}")
        
        # 실제 AI 생성을 트리거하는 버튼
        if st.button("🚀 자동 생성 시작", type="primary", use_container_width=True):
            if len(nlm_text) < 10:
                st.error("NotebookLM 가공 정보를 입력해주세요! (최소 10자)")
            else:
                st.session_state.generated = True
                st.rerun()


# ==========================================
# 오른쪽 패널 (미리보기 및 결과 영역)
# ==========================================
with col_right:
    # 1. 생성 버튼을 누르기 전 (기본 화면)
    if not st.session_state.generated:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; font-size: 60px;'>🦉 🐻 🐿️</h1>", unsafe_allow_html=True)
        st.markdown("<h3 style='text-align: center; color: #4B5563;'>콘텐츠가 여기에 자동으로 생성됩니다</h3>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #9CA3AF;'>NotebookLM 내용을 붙여넣고<br>대상·목적을 선택한 뒤<br><b>'자동 생성 시작'</b>을 누르세요</p>", unsafe_allow_html=True)
        
        st.write("")
        st.markdown("""
        <div class="info-box">
            <h4 style="color: #F59E0B; margin-top: 0;">💡 생성되는 콘텐츠</h4>
            <ul style="color: #4B5563; line-height: 2;">
                <li>📝 <b>블로그 포스팅</b> — 1500자, 단락별 카드 자리 표시</li>
                <li>📖 <b>웹툰</b> — 다올이·다곰이·다람이 캐릭터 대화</li>
                <li>📱 <b>카드뉴스</b> — 슬라이드형 (인스타·네이버)</li>
                <li>🎬 <b>숏츠</b> — 9:16 세로형 (릴스·클립·쇼츠)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
    # 2. 생성 버튼을 누른 후 (결과 화면 표시)
    else:
        with st.spinner("AI가 콘텐츠를 생성하고 있습니다... 잠시만 기다려주세요."):
            # 실제 API 호출이 들어갈 자리 (여기서는 2초 대기 모션만 줍니다)
            time.sleep(2)
            
        st.success("✨ 콘텐츠 생성이 완료되었습니다!")
        
        # 탭을 사용하여 결과물 분류
        tab1, tab2, tab3 = st.tabs(["📝 블로그", "📖 웹툰/카드뉴스", "🎬 숏츠 대본"])
        
        with tab1:
            st.markdown(f"### [블로그 초안] {st.session_state.selected_target['target']}을 위한 완벽 가이드")
            st.write("입력하신 데이터를 바탕으로 AI가 작성한 블로그 내용이 여기에 표시됩니다.")
            st.info(f"적용된 데이터: {nlm_text[:50]}...")
            
        with tab2:
            st.markdown("### 🦉 다올이와 🐻 다곰이의 대화")
            st.write("**다곰이(학부모):** 바뀐 입시 제도 때문에 어떻게 해야 할지 모르겠어요 ㅠㅠ")
            st.write("**다올이(전문가):** 걱정 마세요! 중요한 건 아이의 자기주도적 탐구 능력이에요.")
            st.button("카드뉴스 이미지로 다운로드 (준비중)")
            
        with tab3:
            st.markdown("### 📱 숏츠 기획안")
            st.write("- **Hook(0~3초):** 성적 올리는 완벽한 학교? 사실 정답은 따로 있습니다!")
            st.write("- **Body(3~45초):** 입시 제도의 변화와 면학 분위기의 중요성 설명...")
            st.write("- **CTA(45~60초):** 더 자세한 정보는 다잇다 채널에서 확인하세요!")

        if st.button("돌아가기 (다시 만들기)", use_container_width=True):
            st.session_state.generated = False
            st.rerun()
