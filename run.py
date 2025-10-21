import os
from dotenv import load_dotenv
from pprint import pprint

# 1. 환경 변수 로드
load_dotenv()

# 2. API 키 존재 여부 확인 (가독성/안정성)
if not os.getenv("OPENAI_API_KEY"):
    raise EnvironmentError("환경 변수 'OPENAI_API_KEY'가 설정되지 않았습니다. .env 파일을 확인하세요.")
# [수정]
# Tavily에서 SerpAPI로 변경했으므로, .env 파일의 'SERPAPI_API_KEY'를 확인해야 합니다.
if not os.getenv("SERPAPI_API_KEY"):
    raise EnvironmentError("환경 변수 'SERPAPI_API_KEY'가 설정되지 않았습니다. .env 파일을 확인하세요.")

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
    
    # [수정] 'final_state' 대신, 모든 업데이트를 누적할 딕셔너리를 생성합니다.
    final_state_accumulator = {} 
    
    # stream_mode="updates" : 각 단계(노드)에서 '변경된' 부분만 보여줌
    for event in app.stream(initial_input, stream_mode="updates"):
        # event는 {'node_name': {'state_key': updated_value}} 형태입니다.
        node_name = list(event.keys())[0]
        state_update = event[node_name]
        
        # [수정] state_update가 None이 아닐 경우, 모든 변경 사항을 누적
        if state_update:
            final_state_accumulator.update(state_update)

        print(f"--- [Node: {node_name}] ---")
        
        # 'messages'가 업데이트될 경우, 어떤 메시지가 추가되었는지 보여줌
        if "messages" in state_update:
            # messages는 Annotated(add) 이므로, 누적된 전체가 state_update에 담겨 옴
            new_message = state_update["messages"][-1] 
            print(f"Message: {new_message.pretty_print()}")
        else:
            # 'draft_analysis', 'reflection' 등은 부분 업데이트이므로 pprint
            pprint(state_update)
            
        print("-" * (len(node_name) + 12))
        
        # [수정] __end__ 노드를 만나면 루프를 중단합니다.
        if node_name == "__end__":
            break

    # 7. 최종 결과 출력
    print("\n" + "=" * 40)
    print("✅ 분석이 완료되었습니다!")
    print("=" * 40 + "\n")
    
    # [수정] 'final_state' 대신 'final_state_accumulator'를 확인합니다.
    if final_state_accumulator.get("final_report"):
        print("[최종 분석 보고서]")
        print(final_state_accumulator["final_report"])
    else:
        print("오류: 최종 분석 보고서를 생성하지 못했습니다.")
        print("\n[마지막 Agent 상태]")
        # [수정] 마지막으로 누적된 'final_state_accumulator'를 출력
        pprint(final_state_accumulator) 

if __name__ == "__main__":
    # [수정] 주석에 있는 설치 예시도 최신화합니다. (Tavily -> google-search-results)
    # pip install python-dotenv langchain langgraph langchain-openai google-search-results yfinance pandas pandas-ta
    main()