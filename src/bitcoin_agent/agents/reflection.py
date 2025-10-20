from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from ..state import AgentState

# 비평은 더 고도화된 모델을 사용할 수도 있습니다. (예: gpt-4o)
MODEL_NAME = "gpt-4o" 

def get_reflection_prompt():
    """prompts/reflection.md 파일에서 시스템 프롬프트를 읽어옵니다."""
    try:
        # (경로 관리는 실제 프로젝트 설정에 맞게 조정해야 합니다.)
        with open("prompts/reflection.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("경고: prompts/reflection.md 파일을 찾을 수 없습니다. 기본 프롬프트를 사용합니다.")
        return "당신은 전문 비평가입니다. 주어진 초안을 검토하십시오."

def create_reflection_agent():
    """
    'reflection' Agent (LLM 체인)를 생성합니다.
    이 Agent는 오직 '비평'만 수행합니다.
    """
    
    # 1. LLM 초기화 (도구 바인딩 필요 없음)
    llm = ChatOpenAI(model=MODEL_NAME, temperature=0.1) # 비평의 일관성을 위해 temperature 낮춤
    
    # 2. 프롬프트 템플릿 설정
    system_prompt = get_reflection_prompt()
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt), # 'reflection.md'의 내용
        ("human", "[분석 초안 전문]\n\n{draft_analysis}") # analysis_agent가 작성한 초안
    ])
    
    # 3. LLM 체인(Runnable) 생성
    reflection_chain = prompt | llm
    
    return reflection_chain

# 'reflection' Agent의 인스턴스 생성
reflection_chain = create_reflection_agent()


# [핵심] LangGraph의 노드(Node) 함수
def reflection_agent(state: AgentState) -> dict:
    """
    'reflection' 노드의 메인 실행 함수입니다.
    'draft_analysis'를 입력받아 'reflection' (비평)을 생성합니다.
    """
    
    # 1. 비평할 대상인 'draft_analysis'를 State에서 가져옵니다.
    draft = state.get('draft_analysis')
    
    if not draft:
        # (이론상 'analysis' 노드를 거쳤기 때문에 이 경우는 거의 없지만, 방어 코드)
        return {
            "reflection": "오류: 비평할 분석 초안(draft_analysis)이 없습니다.",
            "messages": [HumanMessage(content="[Reflection Node] 오류: 비평할 초안 없음")]
        }

    # 2. LLM 체인 호출
    #    (LLM은 오직 비평 텍스트만 반환하도록 프롬프트됨)
    response: AIMessage = reflection_chain.invoke({"draft_analysis": draft})
    
    # 3. State 업데이트
    #    LLM이 생성한 비평 텍스트(response.content)를 'reflection' 키에 저장합니다.
    #    이 'reflection'은 'planner_agent'로 전달될 것입니다.
    return {
        "reflection": response.content,
        "messages": [
            HumanMessage(content=f"[Reflection Node] 다음 초안에 대한 비평을 수행했습니다:\n{draft}"),
            response # LLM의 응답 (비평 내용)
        ]
    }