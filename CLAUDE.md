# CLAUDE.md — 채팅 내역 요약 프로그램 (Chat History Summarizer)

## 프로젝트 개요

`.txt` 형식의 채팅 내역 파일을 읽어 자동으로 요약해주는 **Windows 데스크탑 앱**이다.

- 배포 파일 크기 **50MB 이하** 필수 (PyInstaller `--onefile` 빌드 기준)
- 인터넷 없이도 **오프라인 요약 가능** (TextRank 알고리즘 기반)
- 인터넷 연결 시 **AI API 요약** 선택 가능 (OpenAI / Claude API)
- 특정 채팅 플랫폼에 종속되지 않는 범용 `.txt` 파싱

---

## 기술 스택

| 구분 | 선택 | 비고 |
|------|------|------|
| 언어 | Python 3.11+ | |
| GUI | Tkinter (표준 라이브러리) | 추가 설치 불필요 |
| 오프라인 요약 | `sumy` + `nltk` | TextRank / LSA 알고리즘 |
| 온라인 요약 | `openai` 또는 `anthropic` SDK | 사용자 API Key 입력 방식 |
| 인코딩 감지 | `chardet` | UTF-8, EUC-KR 자동 감지 |
| 패키징 | `PyInstaller --onefile` | 단일 .exe 배포 목표 ~25MB |

### 의존성 (requirements.txt)
```
sumy==0.11.0
nltk==3.8.1
chardet==5.2.0
openai==1.30.0
anthropic==0.28.0
requests==2.31.0
```

---

## 프로젝트 파일 구조

```
chat_summarizer/
├── CLAUDE.md              ← 이 파일
├── requirements.txt
├── main.py                ← 앱 진입점 (Tkinter 메인 윈도우)
├── ui/
│   ├── __init__.py
│   ├── main_window.py     ← 메인 윈도우 레이아웃
│   ├── settings_dialog.py ← API Key 설정 다이얼로그
│   └── widgets.py         ← 공용 커스텀 위젯
├── core/
│   ├── __init__.py
│   ├── file_loader.py     ← txt 파일 로드 및 인코딩 처리
│   ├── parser.py          ← 채팅 형식 파싱 (발신자/시간/메시지 추출)
│   ├── summarizer.py      ← 요약 엔진 통합 인터페이스
│   ├── offline_summary.py ← TextRank / TF-IDF 추출 요약
│   └── online_summary.py  ← OpenAI / Claude API 생성 요약
├── utils/
│   ├── __init__.py
│   ├── config.py          ← 설정 저장/불러오기 (API Key 암호화)
│   └── network.py         ← 인터넷 연결 상태 감지
└── build/
    └── build.spec         ← PyInstaller 빌드 설정
```

---

## 개발 3단계 로드맵

---

### ✅ Phase 1 — 핵심 기반 구축 (Core Foundation)

**목표**: 파일을 불러와 화면에 표시하고, 오프라인 추출 요약까지 동작하는 MVP 완성

#### 구현 대상

**1. `core/file_loader.py`**
- `load_file(path: str) -> str` 함수 구현
- `chardet`로 인코딩 자동 감지 후 텍스트 반환
- 지원 인코딩: UTF-8, UTF-8-BOM, EUC-KR, CP949
- 50MB 초과 파일 시 `FileTooLargeError` 예외 발생

**2. `core/parser.py`**
- `parse_chat(text: str) -> list[dict]` 구현
- 각 항목: `{"sender": str, "timestamp": str | None, "message": str}`
- 정규식으로 아래 형식 자동 감지 (감지 실패 시 전체 텍스트를 단일 메시지로 처리):
  - `[2024-01-01 12:00] 홍길동 : 메시지` (카카오톡 스타일)
  - `홍길동 (오전 12:00)\n메시지` (라인 스타일)
  - `2024-01-01 12:00:00 - 홍길동: 메시지` (WhatsApp 스타일)
  - 일반 텍스트 (패턴 없음) → 폴백 처리
- `get_participants(messages: list[dict]) -> list[str]` 구현

**3. `core/offline_summary.py`**
- `summarize_offline(text: str, length: str = "medium") -> dict` 구현
- `length` 옵션: `"short"` (3문장) / `"medium"` (5문장) / `"long"` (8문장)
- `sumy`의 `LsaSummarizer` 사용 (한국어 지원을 위해 형태소 분석 없이 문장 단위 처리)
- 반환값:
  ```python
  {
      "summary": str,           # 핵심 요약 문장들
      "keywords": list[str],    # 상위 키워드 5개 (TF-IDF)
      "participants": list[str], # 참여자 목록
      "mode": "offline"
  }
  ```

**4. `ui/main_window.py` (기본 레이아웃)**
- 2패널 구조 (좌: 원문 미리보기 / 우: 요약 결과)
- 상단: [파일 열기] 버튼, 파일 경로 표시
- 우측 상단: 요약 길이 라디오버튼 (짧게/보통/자세히), [요약 시작] 버튼
- 우측 하단: 요약 결과 텍스트박스
- 하단 상태 바: 파일 정보 (줄 수, 인코딩, 참여자 수) 표시

**5. `main.py`**
- Tkinter 앱 초기화 및 실행
- 드래그&드롭 파일 로드 지원 (`tkinterdnd2` 사용 또는 네이티브 방식)

#### Phase 1 완료 기준
- [ ] txt 파일 열기 → 원문 미리보기 표시
- [ ] [요약 시작] 클릭 → 오프라인 요약 결과 표시
- [ ] 파싱 실패해도 앱이 크래시되지 않음 (폴백 처리 확인)
- [ ] 한글 파일(EUC-KR) 정상 로드 확인

---

### 🔄 Phase 2 — AI 요약 및 옵션 기능 (AI Integration & Options)

**목표**: 온라인 AI 요약 모드 추가, 필터/설정 기능 구현

#### 구현 대상

**1. `core/online_summary.py`**
- `summarize_online(text: str, provider: str, api_key: str, length: str) -> dict` 구현
- `provider` 옵션: `"openai"` 또는 `"anthropic"`
- OpenAI: `gpt-4o-mini` 모델 사용 (비용 최소화)
- Anthropic: `claude-haiku-3-5` 모델 사용
- 시스템 프롬프트 예시:
  ```
  당신은 채팅 내역 요약 전문가입니다.
  주어진 채팅 내역을 분석하여 다음을 제공하세요:
  1. 핵심 내용 요약 ({length} 길이)
  2. 주요 키워드 5개
  3. 핵심 결정사항 또는 Action Item (있는 경우)
  한국어로 답변하세요.
  ```
- 반환값: offline_summary와 동일한 구조 + `"action_items": list[str]`
- API 오류 시 오프라인 모드로 자동 폴백

**2. `utils/network.py`**
- `check_internet(timeout: float = 3.0) -> bool` 구현
- `8.8.8.8:53` 소켓 연결로 빠르게 감지

**3. `utils/config.py`**
- `save_config(key: str, value: str)` / `load_config(key: str) -> str` 구현
- 저장 위치: `%APPDATA%/ChatSummarizer/config.json`
- API Key는 `base64` 인코딩으로 기본 난독화 저장 (v1.0 기준, 추후 강화 가능)

**4. `ui/settings_dialog.py`**
- API Key 입력 필드 (OpenAI / Anthropic 탭)
- 요약 제공자 선택 (OpenAI / Anthropic / 오프라인 전용)
- [연결 테스트] 버튼으로 API Key 유효성 확인

**5. `ui/main_window.py` 업데이트**
- 상단에 연결 상태 표시: `● 오프라인 모드` / `● AI 모드 (OpenAI)` 인디케이터
- 필터 옵션 추가:
  - 날짜 범위 입력 (시작일 ~ 종료일, 파싱된 경우만 활성화)
  - 참여자 체크박스 필터 (파싱 성공 시 자동 목록 생성)
- 요약 결과 하단에 [복사] 버튼 추가
- 요약 처리 중 프로그레스 바 표시 (별도 스레드로 처리, UI 블로킹 방지)

#### Phase 2 완료 기준
- [ ] API Key 설정 → 저장 → 앱 재시작 후 유지 확인
- [ ] AI 모드로 요약 시 오프라인 결과 대비 품질 향상 확인
- [ ] API 오류 시 오프라인으로 자동 폴백 확인
- [ ] 요약 중 UI 블로킹 없음 (스레드 처리 확인)
- [ ] 참여자 필터 적용 후 요약 결과 변화 확인

---

### 🚀 Phase 3 — 완성도 및 배포 (Polish & Packaging)

**목표**: 저장 기능, UX 개선, 빌드 및 배포 준비

#### 구현 대상

**1. 저장 기능**
- `ui/main_window.py`에 [저장] 버튼 추가
- 저장 형식 선택 다이얼로그: `.txt` / `.md`
- 마크다운 저장 시 구조화된 형식으로 출력:
  ```markdown
  # 채팅 요약
  **파일**: 원본파일명.txt
  **요약 일시**: 2026-03-18 15:30
  **요약 모드**: AI (claude-haiku) / 오프라인 (TextRank)

  ## 핵심 요약
  ...

  ## 키워드
  ...

  ## Action Items
  ...
  ```

**2. UX 개선**
- 앱 창 크기 기억 (종료 시 저장, 재시작 시 복원)
- 최근 파일 목록 (최대 5개, 메뉴바 또는 드롭다운)
- 요약 결과 폰트 크기 조절 (+/-  버튼)
- 에러 메시지를 사용자 친화적 언어로 통일:
  - 파일 없음: "파일을 찾을 수 없습니다. 파일이 이동되었거나 삭제되었을 수 있습니다."
  - API 오류: "AI 요약에 실패했습니다. 오프라인 모드로 전환합니다."
  - 인코딩 오류: "파일 인코딩을 인식할 수 없습니다. 인코딩을 직접 선택해 주세요."

**3. 인코딩 수동 선택**
- 자동 감지 실패 시 인코딩 선택 팝업 표시
- 선택 목록: UTF-8, EUC-KR, CP949, UTF-16

**4. `build/build.spec` — PyInstaller 설정**
```python
# build.spec 핵심 설정 방향
# - --onefile: 단일 exe 생성
# - UPX 압축 적용 (upx-dir 지정)
# - 불필요한 패키지 exclude 처리:
#   excludes = ['matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'cv2']
# - nltk_data 중 punkt만 포함 (tokenize용)
# - 목표: 최종 .exe 크기 50MB 이하
```

- `build.bat` 스크립트 작성:
  ```bat
  @echo off
  pip install pyinstaller upx
  pyinstaller --onefile --windowed --name ChatSummarizer build/build.spec
  echo Build complete. Check dist/ChatSummarizer.exe
  ```

**5. 빌드 크기 최적화 체크리스트**
- `pip install pyinstaller` 후 `--exclude-module` 으로 불필요 패키지 제거
- `nltk_data`는 `punkt_tab` 토크나이저 데이터만 포함
- UPX 압축 적용 시 약 20~30% 추가 절감 가능
- 빌드 후 `dir dist\ChatSummarizer.exe` 로 크기 확인 → **50MB 초과 시** excludes 목록 재검토

#### Phase 3 완료 기준
- [ ] 요약 결과를 `.txt` / `.md` 파일로 저장 확인
- [ ] 최근 파일 목록에서 파일 재오픈 확인
- [ ] `PyInstaller --onefile` 빌드 성공
- [ ] **빌드된 `.exe` 크기 50MB 이하** 확인 ✅
- [ ] Windows 10 / 11 환경에서 실행 파일 동작 확인

---

## 공통 개발 원칙

### 코드 스타일
- 타입 힌트 사용 필수 (`def load_file(path: str) -> str:`)
- 모든 공개 함수에 docstring 작성
- 예외 처리는 구체적인 예외 클래스 사용 (`except FileNotFoundError` 등)

### UI 원칙
- 메인 윈도우 기본 크기: `900x600`
- 폰트: `맑은 고딕` (Windows 기본 한글 폰트) 우선, 없으면 `sans-serif`
- 버튼 색상: 기본 시스템 테마 사용 (커스텀 색상 최소화 → 호환성)
- 모든 장시간 작업(파일 로드, 요약)은 `threading.Thread`로 처리하여 UI 블로킹 방지

### 오류 처리 원칙
- 사용자에게 보여주는 모든 에러 메시지는 한국어로 작성
- 스택 트레이스는 로그 파일(`%APPDATA%/ChatSummarizer/app.log`)에만 기록
- 크래시 없이 안전하게 폴백 처리 우선

### 50MB 제약 준수
- 새 의존성 추가 시 반드시 패키지 크기 확인 후 추가
- `pip show <패키지명>` 또는 `pip install <패키지명> --dry-run`으로 사전 확인
- 대안이 있다면 표준 라이브러리 우선 사용 (`json`, `re`, `os`, `threading` 등)

---

## 각 Phase 시작 전 확인사항

```
Phase 1 시작 전:
  □ Python 3.11+ 설치 확인
  □ pip install -r requirements.txt 완료
  □ 테스트용 샘플 txt 파일 준비 (카카오톡, 일반 텍스트 각 1개)

Phase 2 시작 전:
  □ Phase 1 완료 기준 모두 통과
  □ OpenAI 또는 Anthropic API Key 준비 (테스트용)

Phase 3 시작 전:
  □ Phase 2 완료 기준 모두 통과
  □ PyInstaller 설치: pip install pyinstaller
  □ UPX 설치 (선택): https://upx.github.io 에서 다운로드
```

---

*이 파일은 Claude Code가 개발 컨텍스트를 유지하기 위한 프로젝트 가이드입니다.*
*각 Phase 시작 시 이 파일을 먼저 읽고 현재 단계를 파악한 후 작업을 진행하세요.*
