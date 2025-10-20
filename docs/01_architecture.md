# 1. `docs/01_architecture` 비트코인 Agent 아키텍처

본 문서는 `bitcoin_agent`의 핵심 아키텍처를 설명합니다.

## 1.1. 핵심 사상: ReAct + Reflection

본 Agent는 두 가지 핵심 사이클을 기반으로 작동합니다.

1.  **ReAct (Reason + Act) 사이클:**
    * **Reason (추론):** `planner` Agent가 현재 상태를 보고 다음에 할 일(Tool 사용 등)을 결정합니다.
    * **Act (행동):** `tool_executor`가 실제로 도구를 실행하여 데이터를 가져옵니다.
    * **Flow:** `planner` -> `tool_executor` -> `planner` ...

2.  **Reflection (자가 수정) 사이클:**
    * Agent가 생성한 초안(`draft_analysis`)을 스스로 비평(`reflection`)하고 수정합니다.
    * **Flow:** `planner` -> `analysis` (초안 작성) -> `reflection` (비평) -> `planner` (검토 및 수정 지시)

## 1.2. 아키텍처 다이어그램

```text
          [START]
             |
             v
    +------------------+
    |  planner_agent   |  <---- (Tool 결과 / 비평 피드백) -----+
    | (계획, 도구 결정) |                                      |
    +------------------+                                      |
             |                                                |
             v                                                |
   +-------------------------+                                |
   |  conditional_router     |                                |
   +-------------------------+                                |
        |                |                                    |
(도구 호출 필요)  (분석/수정 필요)                          (수정 필요)
        |                |                                    |
        v                v                                    |
+-----------------+  +------------------+                     |
|  tool_executor  |  |  analysis_node   |                     |
|  (도구 실행)     |  | (초안 작성/수정)  |                     |
+-----------------+  +------------------+                     |
       |                   |                                  |
       +-------------------> (비평 필요)                       |
                           |                                  |
                           v                                  |
                   +------------------+                       |
                   | reflection_node  |-----------------------+
                   |   (초안 비평)     |
                   +------------------+
                            |
                            |
                        (최종 완료)
                            |
                            v
                          [END]
```

## 1.3. 핵심 컴포넌트

### 1. Agent State (`state.py`)
* `TypedDict`로 정의된 Agent의 중앙 메모리입니다.
* `query`, `market_data`, `technical_analysis`, `sentiment_analysis`, `draft_analysis`, `reflection`, `final_report`, `messages` 등의 모든 작업 상태가 이곳에 저장되고 업데이트됩니다.

### 2. Tools (`tools/`)
* Agent의 "손발" 역할을 수행합니다.
* `get_ohlcv_data`: (yfinance) 원본 시장 데이터 수집
* `calculate_technical_indicators`: (pandas-ta) 기술적 지표 계산
* `Google Search`: (Tavily) 최신 뉴스 및 정서 검색

### 3. Agents (Nodes) (`agents/`)
* Agent의 "뇌" 역할을 수행하며, LLM 호출을 담당합니다.
* **`planner_agent`**: (지휘자) 전체 흐름을 제어합니다. 도구 사용을 결정하고, `reflection`을 검토하며, `final_report`를 최종 승인합니다.
* **`analysis_agent`**: (작성자) 데이터를 받아 `draft_analysis`를 작성하거나 수정합니다.
* **`reflection_agent`**: (비평가) `draft_analysis`를 검토하여 `reflection` 피드백을 생성합니다.

### 4. Graph (`graph.py`)
* `StateGraph(AgentState)`를 기반으로 위 컴포넌트들을 "조립"합니다.
* **`conditional_router`**: `planner` 노드 실행 후, `final_report` 존재 여부, `tool_calls` 존재 여부를 순차적으로 검사하여 다음 노드(`tool_executor`, `analysis`, `__end__`)로 분기합니다.
