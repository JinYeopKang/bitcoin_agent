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
