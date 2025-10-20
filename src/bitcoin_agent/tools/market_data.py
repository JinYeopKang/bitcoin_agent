import yfinance as yf
import pandas as pd
from langchain_core.tools import tool
from typing import Dict, Any, List

@tool
def get_ohlcv_data(ticker: str = "BTC-USD", period: str = "30d", interval: str = "1d") -> Dict[str, Any]:
    """
    지정된 티커(ticker), 기간(period), 간격(interval)에 대한 
    OHLCV(시가, 고가, 저가, 종가, 거래량) 시장 데이터를 가져옵니다.
    
    Agent는 이 도구를 사용해 원본 가격 데이터를 확보합니다.

    Args:
        ticker (str): 가져올 암호화폐/주식 티커. 비트코인은 'BTC-USD'입니다.
        period (str): 가져올 데이터 기간. (예: "30d", "1mo", "3mo", "1y")
        interval (str): 데이터 간격. (예: "1d", "1wk", "1mo")

    Returns:
        Dict[str, Any]: 
        성공 시: {'ticker': 'BTC-USD', 'period': '30d', 'data': [...OHLCV list...]}
        실패 시: {'error': '...에러 메시지...'}
    """
    try:
        data = yf.Ticker(ticker)
        hist_df = data.history(period=period, interval=interval)
        
        if hist_df.empty:
            return {"error": f"{ticker}에 대한 데이터를 찾을 수 없습니다. (기간: {period})"}

        # DataFrame의 인덱스(Date)를 컬럼으로 변환
        hist_df = hist_df.reset_index()

        # JSON 직렬화를 위해 날짜/시간 객체를 문자열로 변환
        # yfinance는 타임존 정보를 포함한 Datetime을 반환할 수 있음
        if 'Datetime' in hist_df.columns:
            hist_df['Date'] = hist_df['Datetime'].astype(str)
            hist_df = hist_df.drop(columns=['Datetime'])
        elif 'Date' in hist_df.columns:
            hist_df['Date'] = hist_df['Date'].astype(str)
        
        # 불필요한 컬럼 제거
        hist_df = hist_df.drop(columns=['Dividends', 'Stock Splits'], errors='ignore')
        
        # AgentState에 저장하기 용이한 dict 리스트로 변환
        data_list = hist_df.to_dict('records')
        
        return {
            "ticker": ticker,
            "period": period,
            "interval": interval,
            "data": data_list
        }

    except Exception as e:
        return {"error": f"데이터 수집 중 오류 발생: {str(e)}"}