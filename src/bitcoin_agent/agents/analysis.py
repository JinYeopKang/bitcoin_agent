from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
import json

from ..state import AgentState

# planner와 동일한 모델을 사용하거나, 분석/작문에 더 특화된 모델(예: gpt-4-turbo)을 사용할 수 있습니다.
MODEL_NAME = "gpt-4o" 

def get_analysis_prompt():
    """prompts/analysis.md 파일에서 시스템 프롬프트를 읽어옵니다."""
    try:
        # (경로 관리는 실제 프로젝트 설정에 맞게 조정해야 합니다.)
        with open("prompts/analysis.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("경고: prompts/analysis.md 파일을 찾을 수 없습니다. 기본 프롬프트를 사용합니다.")
        return "당신은 전문 애널리스트입니다. 주어진 데이터를 분석하십시오."

def create_analysis_agent():
    """
    'analysis' Agent (LLM 체인)를 생성합니다.
    이 Agent는 도구(Tool)를 사용하지 않고, 오직 '분석'과 '작성'만 수행합니다.
    """
    
    # 1. LLM 초기화 (도구 바인딩이 필요 없음)
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.2) # 일관된 분석을 위해 temperature 낮춤
    
    # 2. 프롬프트 템플릿 설정
    system_prompt = get_analysis_prompt()
    
    # 이 Agent는 'messages' 히스토리를 전부 참조하기보다,
    # 'input_data'로 정제된 데이터만 받아서 작업하는 것이 더 효율적입니다.
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt), # 'analysis.md'의 내용
        ("human", "{input_data}")  # Python 코드에서 동적으로 생성할 입력 데이터
    ])
    
    # 3. LLM 체인(Runnable) 생성
    analysis_chain = prompt | llm
    
    return analysis_chain

# 'analysis' Agent의 인스턴스 생성
analysis_chain = create_analysis_agent()


def format_data_for_llm(state: AgentState) -> str:
    """
    LLM이 분석하기 좋도록 AgentState의 데이터를 문자열로 포맷팅합니다.
    (Req 1: 코드 가독성, Req 4: 상세 설명)
    """
    input_parts = []
    
    # 1. 기술적 분석 데이터
    tech_data = state.get('technical_analysis')
    if tech_data:
        input_parts.append("[기술적 분석 데이터]\n" + json.dumps(tech_data, indent=2, ensure_ascii=False))
    else:
        # --- [핵심 수정] ---
        # 기술적 분석이 실패했어도, 원본 시장 데이터가 있으면 대신 사용
        market_data = state.get('market_data')
        if market_data:
            input_parts.append("[기술적 분석 데이터]\n(계산 실패. 원본 시장 데이터(일부)로 대체)")
            # 데이터가 너무 길 수 있으므로 최신 5개만 요약
            recent_data = market_data.get('data', [])[-5:]
            input_parts.append(json.dumps(recent_data, indent=2, ensure_ascii=False))
        else:
            input_parts.append("[기술적 분석 데이터]\n데이터 없음")
        # --- [수정 끝] ---
        
    # 2. 시장 정서 및 뉴스 데이터
    sentiment_data = state.get('sentiment_analysis')
    if sentiment_data:
        # (sentiment_analysis가 복잡한 dict/list일 경우를 대비해 json.dumps 사용)
        input_parts.append("\n[시장 정서 및 뉴스 데이터]\n" + json.dumps(sentiment_data, indent=2, ensure_ascii=False))
    else:
        input_parts.append("\n[시장 정서 및 뉴스 데이터]\n데이터 없음")

    # 3. 비평(Reflection) 데이터 (수정 작업 시)
    reflection = state.get('reflection')
    if reflection:
        draft = state.get('draft_analysis', '이전 초안 없음')
        input_parts.append(f"\n\n--- [기존 초안] ---\n{draft}")
        input_parts.append(f"\n\n--- [수정 지시] ---\n{reflection}")
        input_parts.append("\n\n[지시] 위 [수정 지시]를 반영하여 [기존 초안]을 개선한 새로운 초안을 작성하십시오.")
    else:
        # 첫 작성 작업 시
        input_parts.append("\n\n[지시] 위 데이터를 바탕으로 비트코인 트렌드 분석 초안을 작성하십시오.")
        
    return "\n".join(input_parts)


# [핵심] LangGraph의 노드(Node) 함수
def analysis_agent(state: AgentState) -> dict:
    """
    'analysis' 노드의 메인 실행 함수입니다.
    현재 State의 데이터를 바탕으로 분석 초안(draft_analysis)을 생성하거나 수정합니다.
    """
    
    # 1. LLM에게 전달할 입력 데이터 포맷팅
    input_data = format_data_for_llm(state)
    
    # 2. LLM 체인 호출
    #    (이 LLM은 오직 분석 텍스트만 반환하도록 프롬프트됨)
    response: AIMessage = analysis_chain.invoke({"input_data": input_data})
    
    # 3. State 업데이트
    #    LLM이 생성한 텍스트(response.content)를 'draft_analysis' 키에 저장합니다.
    #    이 'draft_analysis'는 'reflection_node'로 전달될 것입니다.
    #    'messages'에도 이력을 추가합니다.
    return {
        "draft_analysis": response.content,
        "messages": [
            HumanMessage(content=f"[Analysis Node] 다음 데이터를 기반으로 분석을 수행합니다:\n{input_data}"), # (디버깅/로깅용)
            response # LLM의 응답 (분석 초안)
        ]
    }