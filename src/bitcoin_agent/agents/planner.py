from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from ..state import AgentState
from .. import settings # [수정] settings.py 임포트
from ..tools.market_data import get_ohlcv_data
from ..tools.technical_analysis import calculate_technical_indicators
from ..tools.search import google_search

# [Req 2: 신기술] 
# 코드의 유연성을 위해 LLM 모델 이름과 API 키는 settings.py나 .env에서 관리하는 것이 좋습니다.
# 여기서는 예시를 위해 gpt-4o를 사용합니다. (OPENAI_API_KEY 환경 변수 필요)
MODEL_NAME = settings.PLANNER_MODEL 

def get_planner_prompt():
    """prompts/planner.md 파일에서 시스템 프롬프트를 읽어옵니다."""
    try:
        # [수정] settings에서 경로 사용
        with open(settings.PLANNER_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("경고: prompts/planner.md 파일을 찾을 수 없습니다. 기본 프롬프트를 사용합니다.")
        return "당신은 유능한 AI 어시스턴트입니다."

def create_planner_agent():
    """
    'planner' Agent (LLM 체인)를 생성합니다.
    이 Agent는 도구(Tools)를 사용할 수 있도록 바인딩됩니다.
    """
    
    # 1. 사용할 도구 정의
    tools = [get_ohlcv_data, calculate_technical_indicators, google_search]
    # LLM이 Function Calling을 할 수 있도록 OpenAI 함수 형식으로 변환
    functions = [convert_to_openai_function(t) for t in tools]
    
    # 2. LLM 초기화 (Tool-calling/Function-calling이 가능한 모델)
    # [수정] LLM 초기화 시 settings 사용
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0).bind_functions(functions)
    
    # 3. 프롬프트 템플릿 설정
    system_prompt = get_planner_prompt()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt), # 'planner.md'의 내용
        MessagesPlaceholder(variable_name="messages"), # Agent의 작업 이력
    ])
    
    # 4. LLM 체인(Runnable) 생성
    planner_chain = prompt | llm
    
    return planner_chain

# 'planner' Agent의 인스턴스 생성
planner_chain = create_planner_agent()


def generate_state_summary(state: AgentState) -> str:
    """
    LLM이 현재 상태를 쉽게 파악할 수 있도록 요약본을 생성합니다.
    (Req 1: 코드 가독성, Req 4: 상세 설명)
    """
    summary = []
    summary.append(f"- 사용자 질문: {state.get('query')}")
    
    if state.get('market_data'):
        summary.append("- 시장 데이터: 수집 완료")
    if state.get('technical_analysis'):
        summary.append(f"- 기술적 분석: 수집 완료 (최신 RSI: {state['technical_analysis'].get('rsi_14')})")
    if state.get('sentiment_analysis'):
        summary.append("- 뉴스/정서: 수집 완료")
        
    if state.get('draft_analysis'):
        summary.append("\n--- [최신 분석 초안] ---\n" + state['draft_analysis'])
    if state.get('reflection'):
        summary.append("\n--- [최신 비평/피드백] ---\n" + state['reflection'])
        
    return "\n".join(summary)


# [핵심] LangGraph의 노드(Node) 함수
def planner_agent(state: AgentState) -> dict:
    """
    'planner' 노드의 메인 실행 함수입니다.
    AgentState를 입력받아, LLM을 호출하고, 
    그 결과를 바탕으로 State를 업데이트할 딕셔너리를 반환합니다.
    """
    
    # 1. LLM에게 전달할 'messages' 리스트 준비
    #    (AgentState의 'messages'는 모든 히스토리지만, 
    #     LLM에게는 현재 상태 요약을 포함한 새 메시지 리스트를 전달)
    
    messages = list(state['messages']) # 기존 히스토리 복사
    
    # 2. 현재 상태 요약본을 시스템 메시지(또는 HumanMessage)로 추가 (Req 2)
    #    프롬프트의 {state_summary} 변수를 동적으로 채웁니다.
    #    (이 방식 대신, 프롬프트 템플릿 자체에 state를 주입할 수도 있습니다.)
    #    여기서는 프롬프트를 'planner.md'에 고정했으므로, 
    #    마지막 HumanMessage에 상태 요약을 덧붙이는 방식을 사용합니다.
    
    # [수정] 프롬프트 템플릿 방식이 더 LangChain 스럽습니다.
    # state_summary = generate_state_summary(state)
    # (create_planner_agent의 prompt를 수정하여 state_summary를 변수로 받도록 하는 것이
    #  더 정석적인 방법이나, 여기서는 간단하게 구현합니다.)
    
    # [단순화된 접근]
    # 'planner.md'의 {state_summary}는 f-string으로 처리하지 않고,
    # LLM이 'messages'의 마지막 내용을 보고 판단하도록 유도합니다.
    # 대신, reflection이 있다면 명시적으로 메시지에 추가해줍니다.
    
    if state.get('reflection'):
        reflection_message = HumanMessage(
            content=f"--- [비평/피드백 수신] ---\n{state['reflection']}\n\n"
                    "수석 애널리스트님, 이 비평을 검토하고 다음 단계를 지시해주십시오."
                    "추가 도구가 필요하면 호출하고, 아니라면 도구 없이 응답하십시오."
                    "만약 최종 보고서를 작성할 단계라면, `final_report`를 생성하십시오."
        )
        messages.append(reflection_message)
    elif not state['messages']: # 첫 번째 실행인 경우
        messages.append(HumanMessage(content=f"분석을 시작합니다. 사용자 질문: {state['query']}"))

    
    # 3. LLM 호출
    #    state['messages']를 입력으로 전달
    response: AIMessage = planner_chain.invoke({"messages": messages})
    
    # 4. LLM 응답(AIMessage)을 AgentState에 추가
    #    AIMessage 자체를 반환하면 LangGraph가 자동으로 'messages'에 추가(Annotated)
    #    (tool_calls 포함 가능)
    
    # [수정] 
    # `final_report`를 LLM이 직접 생성하도록 유도하기가 까다롭습니다.
    # LLM이 특정 *텍스트*를 반환하면 그걸 'final_report'로 인식하게 해야 합니다.
    #
    # [전략 변경] (Req 2: 신기술 - LLM의 Tool Calling 활용 극대화)
    # 'final_report' 작성을 위한 별도의 Tool을 LLM에게 제공합니다.
    
    # ---> `planner.py`의 `create_planner_agent` 수정 필요
    # (아래 `planner_agent` 함수 로직은 이 수정이 되었다고 가정하고 진행)
    
    # ---> [가정] `planner_agent`의 LLM에는 `submit_final_report`라는 Tool이
    #           추가로 바인딩되어 있다고 가정합니다.
    
    # [전략 변경 2] (더 간단한 방법)
    # `planner`는 도구 호출 또는 *일반 텍스트* 응답만 합니다.
    # 만약 `planner`가 도구 호출 없이 *일반 텍스트*로 응답하고, 
    # `reflection`이 존재했다면, 
    # 이 텍스트를 `final_report`로 간주합니다.
    
    if not response.tool_calls and state.get('reflection'):
        # 비평을 받은 후, 도구 호출 없이 텍스트로만 응답했다면
        # = "최종 보고서"를 작성한 것으로 간주
        return {
            "messages": [response],
            "final_report": response.content 
        }

    # 도구 호출이 있거나, 아직 비평 단계가 아니라면
    # AIMessage만 반환하여 'messages'에 추가
    return {"messages": [response]}