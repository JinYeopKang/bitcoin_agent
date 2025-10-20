# 2. `docs/02_state_flow` Agent State 흐름 (State Flow)

이 문서는 `bitcoin_agent`가 작업을 수행할 때, 중심 메모리인 `AgentState`가 각 노드(단계)를 거치며 어떻게 변화하는지 그 흐름을 설명합니다. (Req 4)

---

## 2.1. AgentState 정의 (참고)

먼저, `src/bitcoin_agent/state.py`에 정의된 `AgentState`의 구조는 다음과 같습니다.

```python
from typing import List, TypedDict, Optional, Dict, Any, Sequence
from typing_extensions import Annotated
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    # 1. 입력
    query: str
    
    # 2. 데이터 수집
    market_data: Optional[Dict[str, Any]]
    technical_analysis: Optional[Dict[str, Any]]
    sentiment_analysis: Optional[Dict[str, Any]] # (planner가 ToolMessage를 파싱하여 채움)
    
    # 3. 분석 및 검토 (Reflection Cycle)
    draft_analysis: Optional[str]
    reflection: Optional[str]
    
    # 4. 최종 결과
    final_report: Optional[str]
    
    # 5. 작업 이력 (메시지 누적)
    messages: Annotated[Sequence[BaseMessage], operator.add]`
```
---

## 2.2. 상태 흐름 예시 (ReAct + Reflection Cycle)

사용자가 "최근 비트코인 트렌드 분석해줘"라고 입력했을 때의 `AgentState` 변화 예시입니다.

### ➡️ 1단계: 시작 (run.py -> planner)

`run.py`가 `app.stream()`을 호출하며 초기값을 주입합니다.

- **`AgentState` 상태:**
    - `query`: "최근 비트코인 트렌드 분석해줘"
    - `messages`: []
    - (나머지 키는 모두 `None`)
- **실행 노드:** `planner` (진입점)
- **`planner`의 판단:**
    - "사용자 `query`가 있고 데이터가 아무것도 없네. 데이터 수집을 위한 Tool을 호출해야겠다."
    - `calculate_technical_indicators`와 `Google Search` 도구를 호출하는 `AIMessage`를 반환합니다.
- **`AgentState` 변화:**
    - `messages`: `[AIMessage(tool_calls=[...])]` (Tool 호출 메시지 추가)

---

### ➡️ 2단계: ReAct (Tool 실행)

`conditional_router`가 `tool_calls`를 감지하고 `tool_executor` 노드로 보냅니다.

- **실행 노드:** `tool_executor`
- **`tool_executor`의 작업:**
    - `calculate_technical_indicators()` 실행 -> 결과 (JSON) 반환
    - `Google Search()` 실행 -> 결과 (JSON) 반환
    - 이 결과들을 `ToolMessage`로 만들어 `messages`에 추가합니다.
- **`AgentState` 변화:**
    - `messages`: `[..., ToolMessage(content='{rsi:...}'), ToolMessage(content='[{news...}]')]`

---

### ➡️ 3단계: ReAct (데이터 파싱 및 위임)

흐름이 다시 `planner` 노드로 돌아옵니다.

- **실행 노드:** `planner`
- **`planner`의 판단:**
    - "최신 메시지가 `ToolMessage`네. 데이터 수집이 완료되었다."
    - (중요) **`planner`는 이 `ToolMessage`의 내용을 *파싱*하여 `AgentState`의 데이터 키에 저장**해야 합니다.
    - "이제 `analysis_agent`가 분석을 시작할 차례다." (도구 호출 없이 응답)
- **`AgentState` 변화:**
    - `technical_analysis`: `{'rsi_14': 55.2, 'ema_50': ...}` (채워짐)
    - `sentiment_analysis`: `[{'url': ..., 'content': ...}]` (채워짐)
    - `messages`: `[..., AIMessage(content="데이터 수집 완료. 분석 시작.")]`

---

### ➡️ 4단계: 분석 (초안 작성)

`conditional_router`가 `tool_calls`가 없고 `final_report`도 없으므로 `analysis` 노드로 보냅니다.

- **실행 노드:** `analysis`
- **`analysis`의 작업:**
    - `state.get('technical_analysis')`와 `state.get('sentiment_analysis')` 데이터를 읽습니다.
    - `prompts/analysis.md`의 지시에 따라 두 데이터를 종합하여 분석 초안을 작성합니다.
- **`AgentState` 변화:**
    - `draft_analysis`: "비트코인 현재 트렌드 분석 초안... RSI는 55.2로 중립... (중략)" (채워짐)

---

### ➡️ 5단계: Reflection (비평)

흐름이 `reflection` 노드로 이동합니다.

- **실행 노드:** `reflection`
- **`reflection`의 작업:**
    - `state.get('draft_analysis')`를 읽습니다.
    - `prompts/reflection.md`의 비평 기준에 따라 초안을 검토합니다.
- **`AgentState` 변화:**
    - `reflection`: "분석은 좋으나, 최근 반감기 이슈가 뉴스에 비해 약하게 반영됨. 이 부분을 보강할 것." (채워짐)

---

### ➡️ 6단계: Reflection (검토 및 수정 지시)

흐름이 다시 `planner` 노드로 돌아옵니다.

- **실행 노드:** `planner`
- **`planner`의 판단:**
    - "`draft_analysis`와 `reflection`이 모두 존재하네. 비평 내용을 검토하자."
    - "`반감기 이슈 보강`... 타당한 지적이다. **추가 데이터(Tool)는 필요 없으니** `analysis` 노드에 수정을 맡기자." (도구 호출 없이 응답)
- **`AgentState` 변화:**
    - `messages`: `[..., AIMessage(content="비평 검토 완료. 초안 수정을 지시합니다.")]`

---

### ➡️ 7단계: Reflection (수정)

`conditional_router`가 다시 `analysis` 노드로 보냅니다.

- **실행 노드:** `analysis`
- **`analysis`의 작업:**
    - `state.get('technical_analysis')` (데이터)
    - `state.get('draft_analysis')` (기존 초안)
    - `state.get('reflection')` (수정 지시)
    - ... 이 3가지 정보를 모두 입력받아 초안을 *수정*합니다.
- **`AgentState` 변화:**
    - `draft_analysis`: "(수정본) 비트코인 트렌드 분석... **특히 반감기 이슈를 고려할 때**... (중략)" (덮어쓰기)

---

### ➡️ 8~9단계: Reflection (재비평 및 최종 승인)

흐름이 `reflection` -> `planner`로 다시 한번 순환합니다.

- **실행 노드:** `reflection`
    - **`reflection`의 작업:** 수정된 `draft_analysis`를 검토합니다.
    - **`AgentState` 변화:** `reflection`: "매우 훌륭함. 이대로 최종 보고서로 승인해도 좋음." (덮어쓰기)
- **실행 노드:** `planner`
    - **`planner`의 판단:** "`reflection`이 '승인' 사인을 보냈다. 최종 보고서를 작성하고 작업을 종료하자."
    - **`AgentState` 변화:**
        - `final_report`: "최종 비트코인 트렌드 분석 보고서입니다... (중략)" (채워짐)
        - `messages`: `[..., AIMessage(content="최종 보고서 발행.")]`

---

### ➡️ 10단계: 종료

`conditional_router`가 `planner` 노드 실행 직후 `state.get("final_report")`가 채워진 것을 **최우선으로** 확인하고, `__end__`로 흐름을 보냅니다.

- **실행 노드:** `__end__`
- Agent 작업이 종료되고, `run.py`는 `final_report`를 사용자에게 출력합니다.