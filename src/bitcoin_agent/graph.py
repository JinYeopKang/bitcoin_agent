from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from typing import Literal

# 1. Agent의 상태(State)와 도구(Tools)들을 가져옵니다.
from .state import AgentState
from .tools.market_data import get_ohlcv_data
from .tools.technical_analysis import calculate_technical_indicators
from .tools.search import google_search

# 2. Agent의 "뇌" 역할을 하는 노드(Node)들을 가져옵니다.
# (아직 파일은 없지만, 곧 생성할 것이므로 import 구문을 미리 작성합니다.)
from .agents.planner import planner_agent
from .agents.analysis import analysis_agent
from .agents.reflection import reflection_agent


# 3. 도구 리스트 및 ToolNode 정의 (Req 3)
# Agent가 사용할 수 있는 도구들을 리스트로 묶습니다.
tools = [get_ohlcv_data, calculate_technical_indicators, google_search]

# [Req 1: LangGraph 활용]
# ToolNode는 LangGraph에서 제공하는 미리 빌드된 노드입니다.
# Agent가 도구 호출을 결정하면, 이 노드가 자동으로 해당 도구들을 실행하고
# 그 결과를 'messages' 상태에 ToolMessage로 추가해줍니다.
tool_node = ToolNode(tools)


# 4. 조건부 라우터(Router) 함수 정의
# [Req 1, 2] 아키텍처의 핵심 분기점입니다.
def conditional_router(state: AgentState) -> Literal["tool_executor", "analysis", "__end__"]:
    """
    'planner_agent' 노드 실행 후에 호출되는 조건부 엣지입니다.
    Agent의 마지막 메시지와 현재 상태를 기반으로 다음 단계를 결정합니다.

    - (A) 도구 호출이 필요하면 -> 'tool_executor'로 보냅니다.
    - (B) 도구 호출이 없고, 최종 보고서가 완성되었으면 -> 'END'로 보냅니다.
    - (C) 도구 호출이 없고, 아직 분석/수정이 필요하면 -> 'analysis'로 보냅니다.
    """
    
    # 1. 최종 보고서가 생성되었는지 먼저 체크
    if state.get("final_report"):
        return "__end__"

    # 2. (보고서가 없다면) 도구 호출이 있는지 체크
    last_message = state['messages'][-1]
    if last_message.tool_calls:
        return "tool_executor"

    # 3. (보고서도 없고, 도구 호출도 없다면) 분석/수정 단계
    return "analysis"


# 5. 그래프(Graph) 생성 및 조립
def create_graph():
    """
    LangGraph의 StateGraph를 생성하고 노드와 엣지를 조립합니다.
    """
    
    # AgentState를 기반으로 상태 그래프를 초기화합니다.
    graph_builder = StateGraph(AgentState)
    
    # --- 5.1. 노드(Node) 정의 ---
    # 각 노드는 "이름"(str)과 "실행할 함수/객체"(callable)를 가집니다.
    
    # 1. 플래너 노드: 계획 수립, 도구 호출 결정, 최종 보고서 작성
    graph_builder.add_node("planner", planner_agent)
    
    # 2. 도구 실행 노드: 'planner'가 요청한 도구를 실제로 실행
    graph_builder.add_node("tool_executor", tool_node)
    
    # 3. 분석 노드: 수집된 데이터를 바탕으로 분석 초안 작성
    graph_builder.add_node("analysis", analysis_agent)
    
    # 4. 비평 노드: 'analysis'의 초안을 검토하고 피드백 (Req 2)
    graph_builder.add_node("reflection", reflection_agent)
    
    
    # --- 5.2. 엣지(Edge) 정의 ---
    # 노드와 노드 간의 흐름(제어)을 정의합니다.
    
    # 1. 시작점(Entry Point) 설정
    #    사용자 요청이 들어오면 가장 먼저 'planner' 노드를 실행합니다.
    graph_builder.set_entry_point("planner")
    
    # 2. 일반 엣지 (A -> B로 항상 이동)
    
    # 'tool_executor' (도구 실행) -> 'planner' (결과 보고 및 다음 계획)
    graph_builder.add_edge("tool_executor", "planner")
    
    # 'analysis' (초안 작성) -> 'reflection' (초안 비평)
    graph_builder.add_edge("analysis", "reflection")
    
    # 'reflection' (비평) -> 'planner' (비평 내용 검토 및 다음 계획)
    graph_builder.add_edge("reflection", "planner")

    # 3. 조건부 엣지 (Conditional Edge) (A -> B 또는 C 또는 D)
    #    [Req 1, 4] 이 부분이 LangGraph의 핵심입니다.
    #    'planner' 노드 실행 후에는, 'conditional_router' 함수를 호출하여
    #    그 반환값(str)에 따라 다음 노드로 분기합니다.
    graph_builder.add_conditional_edges(
        "planner", # 시작 노드
        conditional_router, # 라우팅 함수
        {
            # key: 라우터 반환값, value: 이동할 노드 이름
            "tool_executor": "tool_executor",
            "analysis": "analysis",
            "__end__": END # "__end__"는 그래프 종료를 의미하는 특수 키워드
        }
    )
    
    # --- 5.3. 그래프 컴파일 ---
    # 정의된 노드와 엣지를 바탕으로 실행 가능한 그래프 객체(app)를 생성합니다.
    app = graph_builder.compile()
    
    return app

# 메인 그래프 객체 생성
# 이 'app' 객체를 run.py 등에서 import하여 사용하게 됩니다.
app = create_graph()