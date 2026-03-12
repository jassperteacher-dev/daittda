import streamlit as st
import anthropic
import requests
import json
import re
import io
import zipfile
import tempfile
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# --- 설정값 불러오기 ---
try:
    # 스트림릿 클라우드의 Secrets에서 설정값을 가져옵니다.
    API_KEY = st.secrets["ANTHROPIC_API_KEY"]
    NOTION_TOKEN = st.secrets["NOTION_TOKEN"]
    NOTION_DB_ID = st.secrets["NOTION_DB_ID"]
except Exception as e:
    st.error("⚠️ 설정 파일(Secrets)이 로드되지 않았습니다. 스트림릿 클라우드 설정의 Secrets를 확인해주세요.")
    st.stop() # 설정이 안 되면 앱을 멈춥니다.
    
# ─── 페이지 설정 ───
st.set_page_config(page_title="다잇다 콘텐츠 자동생성", page_icon="✨", layout="wide")

# ─── 커스텀 CSS ───
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700;900&display=swap');
* { font-family: 'Noto Sans KR', sans-serif; }
.main-header {
    background: #111; color: #fff; padding: 16px 24px; border-radius: 12px;
    border-bottom: 4px solid #F59E0B; margin-bottom: 20px;
    display: flex; align-items: center; gap: 12px;
}
.main-header h1 { margin: 0; font-size: 28px; letter-spacing: -1px; }
.main-header .accent { color: #F59E0B; }
.blog-card {
    background: #fff; border: 1px solid #e5e7eb; border-radius: 12px;
    padding: 20px; margin-bottom: 12px;
}
.blog-intro {
    background: #F8FAFC; border-left: 4px solid #2563EB; border-radius: 8px;
    padding: 14px 18px; margin: 12px 0; line-height: 1.8; font-size: 15px;
}
.blog-conclusion {
    background: #ECFDF5; border-left: 4px solid #059669; border-radius: 8px;
    padding: 14px 18px; margin: 12px 0; line-height: 1.8; font-size: 15px;
}
.hashtag {
    display: inline-block; background: #EFF4FF; color: #2563EB;
    padding: 4px 12px; border-radius: 20px; font-size: 13px;
    font-weight: 600; margin: 2px 4px;
}
.webtoon-header {
    background: #1A1A1A; color: #fff; padding: 14px 20px; text-align: center;
    border-radius: 12px 12px 0 0;
}
.webtoon-header .title { color: #F59E0B; font-size: 12px; font-weight: 700; }
.webtoon-header h3 { color: #fff; margin: 4px 0 0; }
.panel-dialog {
    padding: 12px 16px; border-bottom: 1px solid #f1f5f9;
    display: flex; align-items: flex-start; gap: 10px;
}
.panel-info {
    background: #F8FAFC; padding: 14px 18px; border-bottom: 1px solid #e5e7eb;
}
.char-circle {
    width: 40px; height: 40px; border-radius: 50%; display: flex;
    align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0;
}
.bubble {
    border-radius: 12px; padding: 8px 14px; font-size: 14px;
    line-height: 1.7; max-width: 80%;
}
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] {
    height: 45px; font-weight: 700; font-size: 14px;
    border-radius: 10px 10px 0 0;
}
</style>
""", unsafe_allow_html=True)

# ─── 데이터 ───
TARGETS = [
    {"target": "초등학생 학부모", "goal": "2026 교육과정 변화 이해 및 학습 방향 설정"},
    {"target": "중학생 학부모", "goal": "고입 준비 전략 및 내신 관리법 파악"},
    {"target": "고등학생 학부모", "goal": "수시·정시 전략 비교 및 맞춤 입시 전략 수립"},
    {"target": "재수생 학부모", "goal": "수능 재도전 전략과 학습 로드맵 계획"},
    {"target": "교육에 관심 있는 학부모", "goal": "최신 교육 트렌드와 정책 변화 파악"},
]

CHARACTERS = {
    "owl": {"emoji": "🦉", "name": "다올이", "color": "#2563EB", "bg": "#EFF4FF", "role": "입시전문가"},
    "bear": {"emoji": "🐻", "name": "다곰이", "color": "#D97706", "bg": "#FFFBEB", "role": "학부모대변"},
    "squirrel": {"emoji": "🐿️", "name": "다람이", "color": "#059669", "bg": "#ECFDF5", "role": "학생시점"},
}

TONES = ["전문적·친절", "따뜻·공감", "쉽고 간결"]

# ─── 노션 데이터 연동 함수 ───
def fetch_notion_db(token, db_id):
    url = f"https://api.notion.com/v1/databases/{db_id}/query"
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json"
    }
    response = requests.post(url, headers=headers)
    if response.status_code != 200:
        st.error(f"노션 연결 실패: {response.text}")
        return []
    data = response.json()
    results = []
    for row in data.get('results', []):
        try:
            title = row['properties']['이름']['title'][0]['plain_text']
            content = row['properties']['내용']['rich_text'][0]['plain_text']
            results.append({"title": title, "content": content})
        except: continue
    return results
    
# ─── 유틸 함수 ───
def parse_json(raw):
    """Claude 응답에서 JSON 추출 및 파싱"""
    cleaned = re.sub(r'```json\s*|```', '', raw).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if not match:
            raise ValueError("JSON을 찾을 수 없습니다")
        j = re.sub(r',\s*([\]}])', r'\1', match.group())
        try:
            return json.loads(j)
        except json.JSONDecodeError:
            # 잘린 JSON 복구
            f = j
            if f.count('"') % 2 != 0:
                f += '"'
            opens = f.count('[') - f.count(']')
            f += ']' * max(0, opens)
            opens = f.count('{') - f.count('}')
            f += '}' * max(0, opens)
            f = re.sub(r',\s*([\]}])', r'\1', f)
            return json.loads(f)


def call_claude(API_KEY, prompt, max_tokens=3000):
    """Claude API 호출"""
    client = anthropic.Anthropic(API_KEY=API_KEY)
    msg = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text


def get_font(size=40, bold=False):
    """시스템 폰트 로드 (한글 지원)"""
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansKR-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansKR-Regular.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                continue
    try:
        return ImageFont.truetype("NotoSansKR-Bold.ttf" if bold else "NotoSansKR-Regular.ttf", size)
    except Exception:
        return ImageFont.load_default()


def draw_text_center(draw, text, x, y, font, fill, max_width=900):
    """중앙 정렬 텍스트 (줄바꿈 포함)"""
    lines = []
    line = ""
    for ch in text:
        test = line + ch
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_width and line:
            lines.append(line)
            line = ch
        else:
            line = test
    if line:
        lines.append(line)

    total_h = len(lines) * (font.size + 16)
    start_y = y - total_h // 2
    for i, ln in enumerate(lines):
        bbox = draw.textbbox((0, 0), ln, font=font)
        tw = bbox[2] - bbox[0]
        draw.text((x - tw // 2, start_y + i * (font.size + 16)), ln, fill=fill, font=font)
    return start_y + total_h


def hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# ─── 카드뉴스 이미지 생성 ───
def create_card_title(title, subtitle):
    W, H = 1080, 1080
    img = Image.new('RGB', (W, H), '#0F0F23')
    draw = ImageDraw.Draw(img)
    # 상단 바
    draw.rectangle([0, 0, W, 10], fill='#F59E0B')
    # 로고
    f_logo = get_font(36, True)
    draw_text_center(draw, "다잇다", W//2, 200, f_logo, '#F59E0B', W-100)
    f_sub = get_font(24)
    draw_text_center(draw, "다양한 교육정보를 잇다", W//2, 260, f_sub, '#6B7280', W-100)
    # 타이틀
    f_title = get_font(48, True)
    draw_text_center(draw, title, W//2, 480, f_title, '#FFFFFF', W-160)
    # 서브타이틀
    f_st = get_font(28)
    draw_text_center(draw, subtitle, W//2, 640, f_st, '#9CA3AF', W-160)
    # 하단 바
    draw.rectangle([0, H-10, W, H], fill='#2563EB')
    return img


def create_card_content(slide, idx):
    W, H = 1080, 1080
    img = Image.new('RGB', (W, H), '#16213E')
    draw = ImageDraw.Draw(img)
    # 헤더
    draw.rectangle([0, 0, W, 140], fill='#F59E0B')
    f_brand = get_font(24, True)
    draw.text((50, 20), "다잇다", fill='#111', font=f_brand)
    f_title = get_font(38, True)
    draw.text((50, 70), slide.get('title', ''), fill='#111', font=f_title)
    f_num = get_font(24, True)
    draw.text((W-80, 20), str(idx+1), fill='#00000050', font=f_num)

    y = 200
    f_icon = get_font(40)
    f_label = get_font(24)
    f_value = get_font(32, True)
    f_text = get_font(28)

    stype = slide.get('type', '')
    if stype == 'stats':
        for item in slide.get('items', []):
            draw.rounded_rectangle([50, y, W-50, y+100], radius=12, fill='#FFFFFF10')
            draw.text((80, y+25), item.get('icon', '📊'), fill='#fff', font=f_icon)
            draw.text((160, y+20), item.get('label', ''), fill='#94A3B8', font=f_label)
            draw.text((160, y+55), item.get('value', ''), fill='#fff', font=f_value)
            y += 120
    elif stype == 'dialog':
        for d in slide.get('dialogs', []):
            ch = CHARACTERS.get(d.get('character', 'owl'), CHARACTERS['owl'])
            draw.text((70, y+10), ch['emoji'], fill='#fff', font=f_icon)
            draw.text((130, y+5), ch['name'], fill=ch['color'], font=get_font(20, True))
            draw_text_center(draw, d.get('text', ''), W//2, y+60, f_text, '#E2E8F0', W-200)
            y += 120
    elif stype == 'tip':
        f_tip_title = get_font(36, True)
        draw_text_center(draw, "핵심 포인트", W//2, y+30, f_tip_title, '#F59E0B', W-100)
        y += 80
        for item in slide.get('items', []):
            draw_text_center(draw, f"• {item}", W//2, y+20, f_text, '#E2E8F0', W-160)
            y += 50
    return img


def create_card_ending(comment):
    W, H = 1080, 1080
    img = Image.new('RGB', (W, H), '#0F0F23')
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 10], fill='#F59E0B')
    f_logo = get_font(52, True)
    draw_text_center(draw, "다잇다", W//2, 300, f_logo, '#F59E0B', W-100)
    f_comment = get_font(30)
    draw_text_center(draw, comment, W//2, 440, f_comment, '#E2E8F0', W-160)
    # CTA 버튼
    draw.rounded_rectangle([W//2-220, 540, W//2+220, 620], radius=40, fill='#F59E0B')
    f_cta = get_font(30, True)
    draw_text_center(draw, "카카오톡 채널 추가하기", W//2, 580, f_cta, '#111', 400)
    f_sub = get_font(24)
    draw_text_center(draw, "카카오톡에서 '다잇다' 검색", W//2, 720, f_sub, '#9CA3AF', W-100)
    draw.rectangle([0, H-10, W, H], fill='#2563EB')
    return img


# ─── 숏츠 영상 프레임 생성 ───
def create_shorts_frame_intro(W, H, blog_title, progress):
    """인트로 프레임"""
    img = Image.new('RGB', (W, H), '#0F0F23')
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 10], fill='#F59E0B')
    draw.rectangle([0, H-10, W, H], fill='#2563EB')
    alpha = min(1.0, progress * 2.5)
    c = int(245 * alpha)
    f_logo = get_font(80, True)
    draw_text_center(draw, "다잇다", W//2, H//2-220, f_logo, (c, int(158*alpha), int(11*alpha)), W-100)
    f_sub = get_font(36)
    g = int(156 * alpha)
    draw_text_center(draw, "다양한 교육정보를 잇다", W//2, H//2-120, f_sub, (g, g, g), W-100)
    if progress > 0.3:
        f_title = get_font(52, True)
        ta = min(1.0, (progress - 0.3) * 3)
        tw = int(255 * ta)
        draw_text_center(draw, blog_title, W//2, H//2+60, f_title, (tw, tw, tw), W-140)
    return img


def create_shorts_frame_panel(W, H, panel, progress):
    """대사 장면 프레임"""
    img = Image.new('RGB', (W, H), '#0F0F23')
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 10], fill='#F59E0B')
    draw.rectangle([0, H-10, W, H], fill='#2563EB')
    ch = CHARACTERS.get(panel.get('character', 'owl'), CHARACTERS['owl'])
    text = panel.get('text', '')

    # 로고
    f_logo = get_font(38, True)
    draw_text_center(draw, "다잇다", W//2, 60, f_logo, '#F59E0B', W-100)

    # 캐릭터 (큰 원)
    cY = 360
    r = 170
    if progress > 0.05:
        scale = min(1.0, (progress - 0.05) * 8)
        cr = int(r * scale)
        bg_rgb = hex_to_rgb(ch['bg'])
        c_rgb = hex_to_rgb(ch['color'])
        draw.ellipse([W//2-cr, cY-cr, W//2+cr, cY+cr], fill=bg_rgb, outline=c_rgb, width=6)
        if scale > 0.5:
            f_emoji = get_font(140)
            draw_text_center(draw, ch['emoji'], W//2, cY, f_emoji, '#FFFFFF', 300)

    # 이름
    if progress > 0.15:
        f_name = get_font(56, True)
        draw_text_center(draw, ch['name'], W//2, cY+r+60, f_name, ch['color'], W-100)
        f_role = get_font(34)
        draw_text_center(draw, ch['role'], W//2, cY+r+120, f_role, '#9CA3AF', W-100)

    # 말풍선
    bx, by, bw = 40, cY+r+170, W-80
    bh = H - by - 120
    if progress > 0.18:
        draw.rounded_rectangle([bx, by, bx+bw, by+bh], radius=30, fill='#FFFFFF0D', outline='#FFFFFF10', width=2)

    # 타이핑
    if progress > 0.22:
        tp = (progress - 0.22) / 0.65
        shown = min(len(text), int(len(text) * tp))
        vis = text[:shown]
        f_text = get_font(50, True)
        draw_text_center(draw, vis, W//2, by + bh//2, f_text, '#FFFFFF', bw-80)

    # 하단 CTA
    if progress > 0.85:
        f_cta = get_font(26, True)
        draw_text_center(draw, "카카오톡에서 '다잇다' 검색", W//2, H-55, f_cta, '#F59E0B', W-120)

    return img


def create_shorts_frame_outro(W, H, progress):
    """아웃로 프레임"""
    img = Image.new('RGB', (W, H), '#0F0F23')
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 10], fill='#F59E0B')
    draw.rectangle([0, H-10, W, H], fill='#2563EB')

    # 로고
    if progress > 0:
        a = min(1.0, progress * 4)
        c = int(245 * a)
        f_logo = get_font(84, True)
        draw_text_center(draw, "다잇다", W//2, 480, f_logo, (c, int(158*a), int(11*a)), W-100)
        f_sub = get_font(34)
        g = int(156 * a)
        draw_text_center(draw, "다양한 교육정보를 잇다", W//2, 560, f_sub, (g, g, g), W-100)

    # 멘트
    if progress > 0.2:
        a2 = min(1.0, (progress-0.2)*4)
        w = int(255*a2)
        f_q = get_font(52, True)
        draw_text_center(draw, "더 많은 교육정보가", W//2, 720, f_q, (w,w,w), W-100)
        draw_text_center(draw, "궁금하시다면?", W//2, 790, f_q, (w,w,w), W-100)

    # 검색바
    if progress > 0.4:
        draw.rounded_rectangle([W//2-280, 960, W//2+280, 1060], radius=50, fill='#F59E0B')
        f_btn = get_font(40, True)
        draw_text_center(draw, "다잇다  검색", W//2, 1010, f_btn, '#111111', 500)

    # 카카오톡 안내
    if progress > 0.55:
        f_info = get_font(36)
        draw_text_center(draw, "카카오톡 채널에서", W//2, 1180, f_info, '#E2E8F0', W-100)
        f_brand = get_font(46, True)
        draw_text_center(draw, "'다잇다'", W//2, 1250, f_brand, '#F59E0B', W-100)
        draw_text_center(draw, "를 검색해주세요!", W//2, 1320, f_info, '#E2E8F0', W-100)

    # 하단
    if progress > 0.7:
        f_btm = get_font(26)
        draw_text_center(draw, "맞춤 교육정보 · 입시 전략 · 학습 로드맵", W//2, 1470, f_btm, '#6B7280', W-100)
        draw_text_center(draw, "다잇다가 함께합니다", W//2, 1520, f_btm, '#6B7280', W-100)

    return img


def generate_shorts_video(panels, blog_title):
    """숏츠 영상 생성 (PIL 프레임 → moviepy MP4)"""
    try:
        from moviepy.editor import ImageSequenceClip
    except ImportError:
        st.error("moviepy 설치가 필요합니다: pip install moviepy")
        return None

    W, H = 1080, 1920
    FPS = 15  # 파일 크기 최적화
    SEC_PANEL = 7
    SEC_INTRO = 4
    SEC_OUTRO = 5
    dialogs = [p for p in panels if p.get('type') == 'dialog'][:8]

    frames = []
    progress_bar = st.progress(0, text="숏츠 영상 생성 중...")

    # 인트로
    for f in range(SEC_INTRO * FPS):
        p = f / (SEC_INTRO * FPS)
        img = create_shorts_frame_intro(W, H, blog_title, p)
        frames.append(np.array(img))
        if f % 10 == 0:
            total = (SEC_INTRO + len(dialogs)*SEC_PANEL + SEC_OUTRO) * FPS
            progress_bar.progress(f/total, text="인트로 생성 중...")

    # 대사 장면들
    for di, panel in enumerate(dialogs):
        for f in range(SEC_PANEL * FPS):
            p = f / (SEC_PANEL * FPS)
            img = create_shorts_frame_panel(W, H, panel, p)
            frames.append(np.array(img))
            if f % 10 == 0:
                done = (SEC_INTRO + di*SEC_PANEL)*FPS + f
                total = (SEC_INTRO + len(dialogs)*SEC_PANEL + SEC_OUTRO)*FPS
                progress_bar.progress(min(done/total, 0.95), text=f"장면 {di+1}/{len(dialogs)} 생성 중...")

    # 아웃로
    for f in range(SEC_OUTRO * FPS):
        p = f / (SEC_OUTRO * FPS)
        img = create_shorts_frame_outro(W, H, p)
        frames.append(np.array(img))

    progress_bar.progress(0.97, text="영상 인코딩 중...")

    # MP4 생성
    clip = ImageSequenceClip(frames, fps=FPS)
    tmp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    clip.write_videofile(tmp.name, codec='libx264', audio=False, logger=None,
                         ffmpeg_params=['-pix_fmt', 'yuv420p', '-crf', '23'])
    clip.close()

    with open(tmp.name, 'rb') as f:
        data = f.read()
    os.unlink(tmp.name)
    progress_bar.progress(1.0, text="완성!")
    return data


# ─── 헤더 ───
st.markdown('<div class="main-header"><h1>다<span class="accent">잇</span>다</h1><span style="color:#888;font-size:14px;">교육정보 콘텐츠 자동생성</span></div>', unsafe_allow_html=True)

# ─── 세션 상태 초기화 ───
if 'blog' not in st.session_state: st.session_state.blog = None
if 'webtoon' not in st.session_state: st.session_state.webtoon = None
if 'notion_list' not in st.session_state: st.session_state.notion_list = []
if 'nlm_text' not in st.session_state: st.session_state.nlm_text = ""

# ─── 사이드바 (입력) ───
with st.sidebar:
    st.markdown("### 입력")
    # 노션 연동 로직
    if st.button("🔄 노션 데이터베이스 불러오기", use_container_width=True):
        st.session_state.notion_list = fetch_notion_db(NOTION_TOKEN, NOTION_DB_ID)
    
    if st.session_state.notion_list:
        titles = ["자료를 선택하세요"] + [item['title'] for item in st.session_state.notion_list]
        selected_title = st.selectbox("📝 활용할 노트북LM 자료 선택", titles)
        if selected_title != "자료를 선택하세요":
            for item in st.session_state.notion_list:
                if item['title'] == selected_title:
                    st.session_state.nlm_text = item['content']
                    break

    st.markdown("#### 📁 가공 정보 (직접 수정 가능)")
    nlm_text = st.text_area("내용 확인/수정", value=st.session_state.nlm_text, height=200, label_visibility="collapsed")
    
    # 여기서 nlm_text 업데이트
    st.session_state.nlm_text = nlm_text

    target_names = [f"{t['target']} - {t['goal']}" for t in TARGETS]
    target_idx = st.selectbox("대상 선택 (필수)", range(len(TARGETS)), format_func=lambda i: target_names[i])
    sel = TARGETS[target_idx]
    tone = st.radio("글 톤", TONES, horizontal=True)

    st.markdown("---")
    generate_btn = st.button("🚀 자동 생성 시작", type="primary", use_container_width=True)

# ─── 생성 로직 (버튼 클릭 시 실행) ───
if generate_btn:
    if len(st.session_state.nlm_text) < 10:
        st.error("내용을 10자 이상 입력해주세요")
    else:
        with st.spinner("콘텐츠 생성 중..."):
            # 1. 블로그
            blog_prompt = f"대상:{sel['target']} 목표:{sel['goal']} 톤:{tone}\n[자료]\n{st.session_state.nlm_text[:1200]}\n\n..."
            blog_raw = call_claude(API_KEY, blog_prompt)
            st.session_state.blog = parse_json(blog_raw)
            
            # 2. 웹툰
            wt_prompt = f"주제:{st.session_state.blog['title']} 대상:{sel['target']}\n..."
            wt_raw = call_claude(API_KEY, wt_prompt)
            st.session_state.webtoon = parse_json(wt_raw)
            st.rerun()

# ─── 결과 표시 ───
blog = st.session_state.blog
webtoon = st.session_state.webtoon

if not blog and not webtoon:
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;color:#9CA3AF;">
        <div style="font-size:48px;margin-bottom:16px;">🦉🐻🐿️</div>
        <div style="font-size:18px;font-weight:700;color:#374151;margin-bottom:8px;">여기에 콘텐츠가 생성됩니다</div>
        <div style="font-size:14px;line-height:1.8;">사이드바에서 API 키와 내용을 입력 후<br/>자동 생성 시작 클릭!</div>
    </div>
    """, unsafe_allow_html=True)
else:
    tab1, tab2, tab3, tab4 = st.tabs(["블로그", "웹툰", "카드뉴스", "숏츠 영상"])

    # ── 블로그 ──
    with tab1:
        if blog:
            st.markdown(f"### {blog.get('title', '')}")
            st.caption(blog.get('subtitle', ''))
            st.markdown(f'<div class="blog-intro">{blog.get("intro", "")}</div>', unsafe_allow_html=True)

            for i, sec in enumerate(blog.get('sections', [])):
                st.markdown(f"**■ {sec.get('title', '')}**")
                st.markdown(sec.get('content', ''))
                st.markdown("")

            st.markdown(f'<div class="blog-conclusion">{blog.get("conclusion", "")}</div>', unsafe_allow_html=True)

            # 해시태그
            tags_html = " ".join([f'<span class="hashtag">#{h}</span>' for h in blog.get('hashtags', [])])
            st.markdown(tags_html, unsafe_allow_html=True)

            # 복사용 텍스트
            copy_text = "\n".join([
                blog.get('title', ''), blog.get('subtitle', ''), '',
                blog.get('intro', ''), '',
                *[f"■ {s.get('title','')}\n{s.get('content','')}\n" for s in blog.get('sections', [])],
                blog.get('conclusion', ''), '',
                " ".join([f"#{h}" for h in blog.get('hashtags', [])])
            ])
            st.download_button("블로그 텍스트 다운로드", copy_text, "daida_blog.txt", "text/plain", use_container_width=True)

    # ── 웹툰 ──
    with tab2:
        if webtoon:
            st.markdown(f"""
            <div class="webtoon-header">
                <div class="title">다잇다 웹툰</div>
                <h3>{webtoon.get('title', '')}</h3>
            </div>
            """, unsafe_allow_html=True)

            for p in webtoon.get('panels', []):
                if p.get('type') == 'info':
                    st.markdown(f'<div class="panel-info"><strong>{p.get("label","")}</strong></div>', unsafe_allow_html=True)
                    for item in p.get('items', []):
                        st.markdown(f"&nbsp;&nbsp;• {item}")
                else:
                    ch = CHARACTERS.get(p.get('character', 'owl'), CHARACTERS['owl'])
                    is_right = p.get('character') == 'squirrel'
                    col1, col2 = st.columns([1, 8] if not is_right else [8, 1])
                    with (col1 if not is_right else col2):
                        st.markdown(f"<div style='font-size:28px;text-align:center;'>{ch['emoji']}</div>", unsafe_allow_html=True)
                    with (col2 if not is_right else col1):
                        st.markdown(f"<small style='color:{ch['color']};font-weight:700;'>{ch['name']} · {ch['role']}</small>", unsafe_allow_html=True)
                        st.markdown(f"<div style='background:{ch['bg']};border:1px solid {ch['color']}30;border-radius:12px;padding:8px 14px;font-size:14px;line-height:1.7;'>{p.get('text','')}</div>", unsafe_allow_html=True)

            if webtoon.get('tip'):
                st.info(f"TIP: {webtoon['tip']}")

    # ── 카드뉴스 ──
    with tab3:
        if webtoon:
            slides = webtoon.get('cardSlides', [])
            total_cards = len(slides) + 2
            st.markdown(f"**총 {total_cards}장** (타이틀 + 본문 {len(slides)}장 + 엔딩)")

            # 미리보기
            cols = st.columns(min(4, total_cards))
            with cols[0]:
                st.caption("타이틀")
                title_img = create_card_title(blog.get('title', '') if blog else webtoon.get('title', ''),
                                               blog.get('subtitle', '') if blog else '')
                st.image(title_img, use_container_width=True)

            for i, slide in enumerate(slides):
                col_idx = (i + 1) % len(cols)
                with cols[col_idx]:
                    st.caption(f"본문 {i+1}")
                    card_img = create_card_content(slide, i)
                    st.image(card_img, use_container_width=True)

            # 전체 다운로드 (ZIP)
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, 'w') as zf:
                # 타이틀
                img_buf = io.BytesIO()
                title_img.save(img_buf, format='PNG')
                zf.writestr("01_title.png", img_buf.getvalue())
                # 본문
                for i, slide in enumerate(slides):
                    img_buf = io.BytesIO()
                    create_card_content(slide, i).save(img_buf, format='PNG')
                    zf.writestr(f"{i+2:02d}_card.png", img_buf.getvalue())
                # 엔딩
                img_buf = io.BytesIO()
                ending = create_card_ending(webtoon.get('endingComment', '더 많은 교육정보는 다잇다에서!'))
                ending.save(img_buf, format='PNG')
                zf.writestr(f"{len(slides)+2:02d}_ending.png", img_buf.getvalue())

            st.download_button(
                f"카드뉴스 전체 다운로드 ({total_cards}장, ZIP)",
                buf.getvalue(), "daida_cardnews.zip", "application/zip",
                use_container_width=True
            )

    # ── 숏츠 영상 ──
    with tab4:
        if webtoon:
            dialogs = [p for p in webtoon.get('panels', []) if p.get('type') == 'dialog'][:8]
            st.markdown(f"""
            **숏츠 영상 (1080×1920)**
            - 인트로(4초) → 대사 {len(dialogs)}장면(각 7초) → 아웃로(5초)
            - 타이핑 효과 + 캐릭터 등장 애니메이션
            - 마지막에 '다잇다' 채널 검색 유도
            """)

            # 장면 미리보기
            cols = st.columns(min(4, len(dialogs)))
            for i, p in enumerate(dialogs):
                ch = CHARACTERS.get(p.get('character', 'owl'), CHARACTERS['owl'])
                with cols[i % len(cols)]:
                    st.markdown(f"""
                    <div style="background:#1A1A1A;border-radius:8px;padding:8px;text-align:center;margin-bottom:4px;">
                        <div style="font-size:8px;color:#F59E0B;font-weight:700;">장면 {i+1}</div>
                        <div style="font-size:24px;">{ch['emoji']}</div>
                        <div style="font-size:10px;color:{ch['color']};font-weight:700;">{ch['name']}</div>
                        <div style="font-size:9px;color:#9CA3AF;line-height:1.3;">{p.get('text','')[:25]}...</div>
                    </div>
                    """, unsafe_allow_html=True)

            if st.button("숏츠 영상 생성 및 다운로드", type="primary", use_container_width=True):
                video_data = generate_shorts_video(
                    webtoon.get('panels', []),
                    blog.get('title', '') if blog else webtoon.get('title', '')
                )
                if video_data:
                    st.download_button(
                        "MP4 파일 다운로드",
                        video_data, "daida_shorts.mp4", "video/mp4",
                        use_container_width=True
                    )
                    st.success("숏츠 영상 생성 완료!")
