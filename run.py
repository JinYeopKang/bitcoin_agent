import os
from dotenv import load_dotenv
from pprint import pprint

# 1. 환경 변수 로드
#    src/bitcoin_agent/graph.py 등 내부 모듈이 API 키를 사용할 수 있도록
#    가장 먼저 실행되어야 합니다.
load_dotenv()

# 2. API 키 존재 여부 확인 (가독성/안정성)
if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("환경 변수 'OPENAI_API_KEY'가 설정되지 않았습니다. .env 파일을 확인하세요.")
if not os.getenv("TAVILY_API_KEY"):
    raise EnvironmentError("환경 변수 'TAVILY_API_KEY'가 설정되지 않았습니다. .env 파일을 확인하세요.")

# 3. Agent State 및 Graph(app) 임포트
#    (API 키가 로드된 *후에* 임포트해야 안전합니다.)
from src.bitcoin_agent.graph import app
from src.bitcoin_agent.state import AgentState

def main():
    """
    메인 실행 함수
    """
    print("🤖 비트코인 트렌드 분석 Agent에 오신 것을 환영합니다.")
    print("=" * 40)
    
    # 4. 사용자 입력 받기
    query = input("분석을 원하는 내용을 입력하세요 (예: '최근 비트코인 트렌드 분석해줘'): ")
    
    if not query:
        print("입력이 없어 종료합니다.")
        return

    # 5. LangGraph 실행을 위한 초기 상태(Input) 구성
    #    AgentState의 'query'와 'messages'의 초기값을 설정합니다.
    #    'messages'는 빈 리스트로 시작하며, planner_agent가 첫 HumanMessage를 추가할 것입니다.
    initial_input = {
        "query": query,
        "messages": []
    }
    
    print("\n...Agent가 분석을 시작합니다. (실시간 스트리밍)...\n")
    
    # 6. [Req 2, 4] 그래프 스트리밍 실행 (Streaming)
    #    app.stream()은 Agent가 각 노드를 거칠 때마다 발생하는 
    #    '상태 업데이트(update)'를 실시간으로 반환합니다.
    
    final_state = None # 마지막 상태를 저장할 변수
    
    # stream_mode="updates" : 각 단계(노드)에서 '변경된' 부분만 보여줌
    for event in app.stream(initial_input, stream_mode="updates"):
        # event는 {'node_name': {'state_key': updated_value}} 형태입니다.
        node_name = list(event.keys())[0]
        state_update = event[node_name]
        
        print(f"--- [Node: {node_name}] ---")
        
        # 'messages'가 업데이트될 경우, 어떤 메시지가 추가되었는지 보여줌
        if "messages" in state_update:
            new_message = state_update["messages"][-1] # 마지막에 추가된 메시지
            print(f"Message: {new_message.pretty_print()}") # LangChain 메시지 형식으로 예쁘게 출력
        else:
            # 'draft_analysis', 'reflection' 등의 업데이트
            pprint(state_update)
            
        print("-" * (len(node_name) + 12))
        
        # 마지막 상태는 "__end__" 노드에서 나옵니다.
        if node_name == "__end__":
            final_state = state_update

    # 7. 최종 결과 출력
    print("\n" + "=" * 40)
    print("✅ 분석이 완료되었습니다!")
    print("=" * 40 + "\n")
    
    if final_state and final_state.get("final_report"):
        print("[최종 분석 보고서]")
        print(final_state["final_report"])
    else:
        print("오류: 최종 분석 보고서를 생성하지 못했습니다.")
        print("\n[마지막 Agent 상태]")
        pprint(final_state) # 디버깅을 위해 마지막 상태 출력

if __name__ == "__main__":
    # 필요한 라이브러리 설치 (예시)
    # pip install python-dotenv langchain langchain-openai langchain-community tavily-python yfinance pandas-ta
    main()