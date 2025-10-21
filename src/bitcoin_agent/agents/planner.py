from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# [삭제] 아래 convert_to_openai_function 임포트 라인을 삭제합니다.
# from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
import json

from ..state import AgentState
from .. import settings
from ..tools.market_data import get_ohlcv_data
from ..tools.technical_analysis import calculate_technical_indicators
from ..tools.search import google_search

MODEL_NAME = settings.PLANNER_MODEL

def get_planner_prompt():
    """prompts/planner.md 파일에서 시스템 프롬프트를 읽어옵니다."""
    try:
        with open(settings.PLANNER_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print(f"경고: {settings.PLANNER_PROMPT_PATH} 파일을 찾을 수 없습니다.")
        return "당신은 유능한 AI 어시스턴트입니다."

# --- [추가] 헬퍼 함수 ---
def generate_state_summary(state: AgentState) -> str:
    """
    LLM이 현재 상태를 쉽게 파악할 수 있도록 요약본을 생성합니다.
    """
    summary = []
    summary.append(f"- 사용자 질문: {state.get('query')}")
    
    # 데이터 수집 상태
    tech_status = "수집 완료" if state.get('technical_analysis') else "대기 중"
    sentiment_status = "수집 완료" if state.get('sentiment_analysis') else "대기 중"
    summary.append(f"- 기술적 분석: {tech_status}")
    summary.append(f"- 뉴스/정서: {sentiment_status}")
        
    # 상세 데이터 (너무 길지 않게)
    if state.get('technical_analysis'):
         summary.append(f"  (최신 RSI: {state['technical_analysis'].get('rsi_14')})")

    # 분석/비평 단계
    if state.get('draft_analysis') and not state.get('reflection'):
        summary.append("\n--- [최신 분석 초안] --- (비평 대기 중)")
    if state.get('reflection'):
        summary.append(f"\n--- [최신 비평/피드백] ---\n{state['reflection']}")
        
    return "\n".join(summary)
# --- [추가 끝] ---


def create_planner_agent():
    """
    'planner' Agent (LLM 체인)를 생성합니다.
    이 Agent는 도구(Tools)를 사용할 수 있도록 바인딩됩니다.
    """
    
    # 1. 사용할 도구 정의
    tools = [get_ohlcv_data, calculate_technical_indicators, google_search]
    # [삭제] 'functions' 변환 라인을 삭제합니다. .bind_tools()는 'tools' 리스트를 직접 받습니다.
    # functions = [convert_to_openai_function(t) for t in tools] 
    
    # 2. LLM 초기화
    # [수정] .bind_functions(functions) 대신 .bind_tools(tools)를 사용합니다.
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0).bind_tools(tools)
    
    # 3. 프롬프트 템플릿 설정
    system_prompt = get_planner_prompt()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt), 
        MessagesPlaceholder(variable_name="messages"),
    ])
    
    planner_chain = prompt | llm
    
    return planner_chain

planner_chain = create_planner_agent()


# [핵심] LangGraph의 노드(Node) 함수
def planner_agent(state: AgentState) -> dict:
    """
    'planner' 노드의 메인 실행 함수입니다.
    ToolMessage를 파싱하여 State를 업데이트하고, LLM을 호출합니다.
    """
    
    # --- [ToolMessage 파싱 로직] ---
    updates_to_state = {}
    if state['messages'] and isinstance(state['messages'][-1], ToolMessage):
        for msg in reversed(state['messages']):
            if not isinstance(msg, ToolMessage):
                break 
            
            tool_name = msg.name
            tool_content = msg.content
            
            # --- [핵심 수정: JSON 파싱 안정성 추가] ---
            # ToolMessage의 content가 가끔 JSON '문자열'로 반환될 때가 있습니다.
            if isinstance(tool_content, str):
                try:
                    tool_content = json.loads(tool_content)
                except json.JSONDecodeError:
                    # 유효한 JSON이 아니면 (오류 메시지 등) 그대로 둡니다.
                    pass
            # --- [수정 끝] ---
            
            if tool_name == "calculate_technical_indicators":
                if isinstance(tool_content, dict) and "error" not in tool_content:
                    updates_to_state["technical_analysis"] = tool_content
            elif tool_name == "google_search":
                if isinstance(tool_content, list) and tool_content and not (isinstance(tool_content[0], dict) and "error" in tool_content[0]):
                    updates_to_state["sentiment_analysis"] = tool_content
            
            # --- [핵심 수정: 이 로직 추가] ---
            elif tool_name == "get_ohlcv_data":
                if isinstance(tool_content, dict) and "error" not in tool_content:
                    updates_to_state["market_data"] = tool_content
            # --- [수정 끝] ---
    # --- [파싱 로직 끝] ---

    
    messages = list(state['messages'])
    
    if state.get('reflection'):
        reflection_message = HumanMessage(
            content=f"--- [비평/피드백 수신] ---\n{state['reflection']}\n\n"
                    "수석 애널리스트님, 이 비평을 검토하고 다음 단계를 지시해주십시오."
                    "추가 도구가 필요하면 호출하고, 아니라면 도구 없이 응답하십시오."
                    "만약 최종 보고서를 작성할 단계라면, `final_report`를 생성하십시오."
        )
        messages.append(reflection_message)
    elif not state['messages']: 
        messages.append(HumanMessage(content=f"분석을 시작합니다. 사용자 질문: {state['query']}"))

    
    # --- [LLM 호출 부분] ---
    # 1. 현재 상태 요약본 생성
    current_state_summary = generate_state_summary(state)

    # 2. LLM 호출 시 'messages'와 'state_summary'를 모두 전달
    response: AIMessage = planner_chain.invoke({
        "messages": messages,
        "state_summary": current_state_summary 
    })
    # --- [호출 끝] ---
    
    
    # 3. 반환값에 'messages'와 'state 업데이트'를 모두 포함
    return_value = {"messages": [response]}
    return_value.update(updates_to_state) 

    # 4. 'final_report' 생성 로직
    if not response.tool_calls and state.get('reflection'):
        return_value["final_report"] = response.content
        return return_value

    return return_value