from typing import List, TypedDict, Optional, Dict, Any, Sequence
from typing_extensions import Annotated
from langchain_core.messages import BaseMessage
import operator

# 참고: BaseMessage는 LangChain의 모든 메시지 타입(AIMessage, HumanMessage, ToolMessage 등)의 부모 클래스입니다.

class AgentState(TypedDict):
    """
    비트코인 트렌드 분석 Agent의 전체 상태(memory)를 정의합니다.
    LangGraph의 각 노드(node)는 이 상태 객체를 인자로 받고,
    업데이트된 상태 객체를 반환하며 작업을 이어갑니다.
    """
    
    # --- 1. 입력 및 계획 ---
    
    query: str
    """사용자의 원본 질문 (예: '최근 비트코인 트렌드 어때?')"""
    
    plan: Optional[List[str]]
    """planner_agent가 수립한 단계별 분석 계획 리스트"""
    
    
    # --- 2. 데이터 수집 단계 ---
    
    market_data: Optional[Dict[str, Any]]
    """`get_ohlcv_data` Tool이 가져온 원본 시장 데이터 (가격, 거래량 등)"""
    
    technical_analysis: Optional[Dict[str, Any]]
    """`calculate_technical_indicators` Tool이 계산한 기술적 지표 (RSI, MA, MACD 등)"""
    
    sentiment_analysis: Optional[Dict[str, Any]]
    """`Google Search` Tool이 수집한 뉴스/소셜 데이터 및 정서 분석 요약"""
    

    # --- 3. 분석 및 검토 단계 (Reflection Cycle) ---
    
    draft_analysis: Optional[str]
    """`analysis_node`가 모든 데이터를 종합해 작성한 1차 분석 초안"""
    
    reflection: Optional[str]
    """`reflection_node`가 1차 초안을 비평한 내용 (수정 지시사항)"""
    
    
    # --- 4. 최종 결과 ---
    
    final_report: Optional[str]
    """모든 비평이 반영된 최종 분석 보고서"""
    
    
    # --- 5. Agent 실행 이력 (LangGraph의 핵심 기능) ---
    
    # [Req 2: 신기술 적용]
    # 'messages'는 Agent와 Tool 간의 모든 상호작용(대화)을 기록하는 로그입니다.
    # Annotated[Sequence[BaseMessage], operator.add]는 LangGraph에게 
    # 이 'messages' 리스트에 새로운 메시지가 생길 때마다 기존 리스트에 '덮어쓰는' 것이 아니라 
    # '추가(add)'하라고 알려주는 특별한 문법입니다.
    # 이를 통해 Agent의 전체 작업 히스토리를 추적할 수 있습니다. (Req 4)
    messages: Annotated[Sequence[BaseMessage], operator.add]