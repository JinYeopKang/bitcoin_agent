# bitcoin_agent
[SKALA 2nd] Bitcoin Trend Analysis Developed

# Tree Structure
    bitcoin_agent/
    │
    ├── .gitignore              # Git이 무시할 파일 목록 (e.g., .env, __pycache__, .DS_Store)
    ├── .env.example            # [수정] 필요한 환경 변수 예시 (SERPAPI_API_KEY 포함)
    ├── .env                    # [수정] 실제 API 키 저장 (SERPAPI_API_KEY) (Git 무시됨)
    │
    ├── pyproject.toml          # [수정] 프로젝트 의존성 관리 (google-search-results 라이브러리 명시)
    ├── README.md               # 프로젝트 개요, 설치 방법 (poetry install), 실행 방법 (python run.py)
    │
    ├── src/
    │   └── bitcoin_agent/      # 메인 소스 코드 패키지
    │       │
    │       ├── __init__.py     # 이 디렉터리를 Python 패키지로 인식
    │       ├── state.py        # [핵심] AgentState (TypedDict) 중앙 정의
    │       ├── settings.py     # LLM 모델명, 프롬프트 경로 등 전역 설정값
    │       │
    │       ├── tools/          # [Req 3] Agent가 사용할 도구(손발) 모음
    │       │   ├── __init__.py
    │       │   ├── market_data.py  # 1. get_ohlcv_data (yfinance)
    │       │   ├── technical_analysis.py # 2. calculate_technical_indicators (pandas-ta)
    │       │   └── search.py       # [수정] 3. google_search (SerpAPI로 구현)
    │       │
    │       ├── agents/         # [핵심] 각 노드의 비즈니스 로직(뇌)
    │       │   ├── __init__.py
    │       │   ├── planner.py      # 1. planner_agent (지휘자: 도구 결정, 최종 승인)
    │       │   ├── analysis.py     # 2. analysis_agent (작성자: 초안 작성/수정)
    │       │   └── reflection.py   # 3. reflection_agent (비평가: 초안 검토)
    │       │
    │       └── graph.py        # [핵심] LangGraph 조립 (State, Node, Edge 연결)
    │
    ├── prompts/                # [Req 2] LLM 프롬프트를 코드가 아닌 파일로 분리 (유지보수 용이)
    │   ├── planner.md
    │   ├── analysis.md
    │   └── reflection.md
    │
    ├── tests/                  # 테스트 코드
    │   ├── test_tools.py       # (필수) market_data, technical_analysis, search 도구 유닛 테스트
    │   └── test_graph.py       # (권장) AgentState 흐름 통합 테스트
    │
    ├── docs/                   # [Req 4] Notion 정리를 위한 핵심 산출물
    │   ├── 01_architecture.md  # 아키텍처 다이어그램 및 컴포넌트 설명
    │   ├── 02_state_flow.md    # AgentState가 순환하며 변화하는 과정 설명
    │   └── 03_prompt_guide.md  # 각 Agent 프롬프트의 역할과 엔지니어링 의도
    │
    └── run.py                  # Agent를 실행하는 메인 스크립트 (app.stream() 호출)
---
# 실행 방법
`pyproject.toml`을 사용했으므로, **Poetry를 사용하는 방법(권장)**과 **`pip`을 사용하는 방법(대안)** 두 가지를 모두 알려드리겠습니다.

---

## 방법 1: Poetry 사용 (가장 권장되는 방법)

`pyproject.toml`의 모든 이점을 누릴 수 있는 표준 방식입니다.

### 1. Poetry 설치 (PC에 한 번만 설치)

Poetry가 설치되어 있지 않다면 먼저 설치합니다.
```
Bash
```
```
# macOS / Linux / WSL
curl -sSL https://install.python-poetry.org | python3 -

# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```
(또는 간단하게 `pip install poetry`)

### 2. 가상 환경 생성 및 의존성 설치

프로젝트 루트 디렉터리(`pyproject.toml`이 있는 곳)에서 다음 명령어를 실행합니다.

```
Bash
```
```
# 이 명령어 하나로 pyproject.toml을 읽어
# 1. 가상 환경(.venv)을 생성하고,
# 2. 모든 의존성(langgraph, pandas-ta 등)을 정확한 버전에 맞춰 설치합니다.
poetry install
```

---

## 방법 2: `pip` + 가상 환경 사용 (대안)

Poetry를 사용하고 싶지 않다면, `pip`으로도 동일하게 환경을 구성할 수 있습니다.

### 1. 가상 환경 생성

```
Bash
```
```
# .venv 라는 이름의 가상 환경 폴더를 생성합니다.
# (이 이름은 .gitignore에 이미 등록되어 있습니다.)
python -m venv .venv
```
### 2. 가상 환경 활성화

```
Bash
```
```
# Windows (cmd.exe 또는 PowerShell)
.\.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate`
```
(터미널 프롬프트 앞에 `(.venv)`가 보이면 성공입니다.)

### 3. `pip`으로 의존성 설치

`pyproject.toml`에 명시된 모든 라이브러리를 `pip`으로 직접 설치합니다.

```Bash

# 필수 라이브러리 일괄 설치
pip install langchain langgraph langchain-openai python-dotenv google-search-results yfinance pandas pandas-ta
```
---

## 🚀 검증 및 실행 프로세스 (순차 명령어)

위 **방법 1 또는 2**를 통해 의존성 설치를 완료했다면, 이제 다음 순서대로 Agent 실행을 검증합니다.

### 1단계: `.env` 파일 준비 (필수!)

가장 먼저 API 키를 준비해야 합니다. `.env.example` 파일을 복사해서 `.env` 파일을 만듭니다.

```
Bash
```
```
# (macOS / Linux)
cp .env.example .env

# (Windows)
copy .env.example .env
```
그런 다음, `nano .env` 또는 VSCode 편집기를 열어 `.env` 파일 안에 실제 `OPENAI_API_KEY`와 `SERPAPI_API_KEY` 값을 채워 넣고 저장합니다.

### 2단계: 가상 환경 활성화 (필수!)

`pip` 방식을 썼다면 이미 활성화되어 있을 수 있습니다. Poetry 방식이었다면 다음 명령어를 입력합니다.

```
Bash
```
```
# Poetry 사용자
poetry shell

# pip 사용자 (아직 안 했다면)
# source .venv/bin/activate  (또는 .\.venv\Scripts\activate)`
```
### 3단계: 설치된 패키지 목록 확인 (검증)

가상 환경이 올바르게 활성화되었는지, 패키지들이 잘 설치되었는지 확인합니다.
```
Bash
```
```
# 현재 활성화된 가상 환경에 설치된 패키지 목록을 보여줍니다.
pip list
```
출력된 목록에서 `langgraph`, `google-search-results`, `yfinance` 등이 보이는지 눈으로 확인합니다.

### 4단계: 패키지 호환성 검사 (권장 검증)

설치된 패키지들 간에 버전 충돌이 없는지 `pip`이 스스로 검사하도록 합니다.

```
Bash
```
```
pip check
```
"No broken requirements found." (또는 유사한 메시지)가 출력되면 완벽합니다.

### 5단계: Agent 실행 (최종 테스트)

모든 준비가 끝났습니다. `run.py` 스크립트를 실행합니다.

```
Bash
```
```
python run.py
```
Agent가 실행되고 `🤖 비트코인 트렌드 분석 Agent에 오신 것을 환영합니다.` 메시지와 함께 `분석을 원하는 내용을 입력하세요:` 라는 프롬프트가 나타나면 **모든 설정이 성공적으로 완료된 것입니다!**