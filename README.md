# 다잇다 교육정보 콘텐츠 자동생성기

다양한 교육정보를 잇는 **다잇다** 플랫폼의 콘텐츠 자동생성 도구입니다.

## 기능

- **블로그**: 1500자 내외 전문 교육 블로그 (다잇다 브랜딩 포함)
- **웹툰**: 캐릭터 대화형 교육 웹툰 (다올이/다곰이/다람이)
- **카드뉴스**: 6장 + 타이틀/엔딩 (1080×1080, ZIP 다운로드)
- **숏츠 영상**: 타이핑 효과 + 캐릭터 애니메이션 (1080×1920 MP4)

## 로컬 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Cloud 배포

1. GitHub에 이 폴더를 push
2. [share.streamlit.io](https://share.streamlit.io) 접속
3. GitHub 레포 연결 → `app.py` 선택 → 배포

### Streamlit Cloud에서 한글 폰트 + ffmpeg 설정

`packages.txt` 파일을 루트에 생성:
```
fonts-noto-cjk
ffmpeg
```

## 환경변수 (선택)

Streamlit Cloud의 Secrets에서 API 키를 설정할 수 있습니다:
```toml
# .streamlit/secrets.toml
ANTHROPIC_API_KEY = "sk-ant-api03-..."
```

## 파일 구조

```
daida-streamlit/
├── app.py                    # 메인 앱
├── requirements.txt          # Python 패키지
├── packages.txt              # 시스템 패키지 (Streamlit Cloud용)
├── .streamlit/
│   └── config.toml           # 테마 설정
└── README.md
```

## 사용법

1. 사이드바에서 Anthropic API 키 입력
2. NotebookLM 정리 내용 붙여넣기
3. 대상/톤 선택
4. "자동 생성 시작" 클릭
5. 블로그/웹툰/카드뉴스/숏츠 탭에서 결과 확인 및 다운로드
