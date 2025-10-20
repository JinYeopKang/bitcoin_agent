import os
from langchain_core.tools import tool
from typing import List, Dict, Any
from serpapi import GoogleSearch # [수정] TavilyClient 대신 SerpAPI의 GoogleSearch 임포트

@tool
def google_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    (SerpAPI 구동) 최신 비트코인 뉴스, 시장 정서(sentiment), 규제 동향, 
    전문가 의견을 웹에서 검색합니다.
    
    Agent는 이 도구를 사용해 기술적 분석 외의 정성적(Qualitative)인
    트렌드 요인을 파악합니다. (예: '비트코인 최신 뉴스', '비트코인 시장 정서')

    Args:
        query (str): 검색할 쿼리. (예: "비트코인 최신 규제 뉴스")
        max_results (int): 가져올 최대 검색 결과 수.

    Returns:
        List[Dict[str, Any]]: 검색 결과 리스트. 
                              각 항목은 {'url': ..., 'content': ..., 'title': ...} 형태입니다.
    """
    try:
        # 1. [수정] .env에서 SERPAPI_API_KEY를 읽어옵니다.
        api_key = os.getenv("SERPAPI_API_KEY")
        if not api_key:
            return [{"error": "SerpAPI API 키가 설정되지 않았습니다. (.env 파일 확인)"}]

        # 2. [수정] SerpAPI 검색 파라미터 설정
        params = {
            "engine": "google",          # 구글 검색 엔진
            "q": query,                  # 검색 쿼리
            "api_key": api_key,
            "num": max_results,          # 반환할 결과 수 (SerpAPI는 10개 단위로도 가능)
            "location": "South Korea",   # 검색 위치 (한국)
            "gl": "kr",                  # 국가 코드
            "hl": "ko",                  # 언어 (한국어)
        }

        # 3. [수정] SerpAPI 클라이언트 실행
        client = GoogleSearch(params)
        results = client.get_dict()

        # 4. [중요] SerpAPI 결과를 Agent가 이해하는 형식(List[Dict])으로 변환
        #    (Agent의 다른 코드를 수정하지 않기 위해 출력 포맷을 통일합니다.)
        
        formatted_results = []
        
        # 'organic_results' (일반 검색 결과) 처리
        if "organic_results" in results:
            for res in results["organic_results"][:max_results]:
                formatted_results.append({
                    "title": res.get("title", "No Title"),
                    "url": res.get("link", "#"),
                    "content": res.get("snippet", "No snippet available.") # 'snippet'이 Tavily의 'content'와 유사
                })
        
        # 'news_results' (뉴스 검색 결과) 처리 (뉴스 쿼리인 경우)
        elif "news_results" in results:
             for res in results["news_results"][:max_results]:
                formatted_results.append({
                    "title": res.get("title", "No Title"),
                    "url": res.get("link", "#"),
                    "content": res.get("snippet", "No snippet available.")
                })

        if not formatted_results:
            return [{"content": f"'{query}'에 대한 검색 결과가 없습니다."}]

        return formatted_results
    
    except Exception as e:
        return [{"error": f"SerpAPI 검색 중 오류 발생: {str(e)}"}]