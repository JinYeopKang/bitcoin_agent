import pandas as pd
import pandas_ta as ta
from langchain_core.tools import tool
from typing import Dict, Any
import yfinance as yf

# [삭제] from .market_data import get_ohlcv_data (지난번에 수정됨)

@tool
def calculate_technical_indicators(ticker: str = "BTC-USD", period: str = "1y") -> Dict[str, Any]:
    """
    주요 기술적 분석 지표(RSI, 50/200일 이동평균, MACD)를 계산합니다.
    Agent는 이 도구를 사용해 현재 시장의 과매수/과매도, 추세 등을 파악합니다.

    Args:
        ticker (str): 분석할 티커. (예: 'BTC-USD')
        period (str): 분석에 사용할 데이터 기간. (예: "1y")

    Returns:
        Dict[str, Any]: 
        성공 시: {'rsi': 55.0, 'ma_50': 60000, 'ma_200': 50000, 'macd_signal': ...}
        실패 시: {'error': '...에러 메시지...'}
    """
    try:
        # 1. yfinance 로직
        data = yf.Ticker(ticker)
        hist_df = data.history(period=period, interval="1d")
        
        if hist_df.empty:
            return {"error": f"{ticker}에 대한 데이터를 찾을 수 없습니다. (기간: {period})"}
        
        hist_df = hist_df.reset_index()
        if 'Datetime' in hist_df.columns:
            hist_df['Date'] = hist_df['Datetime'].astype(str)
            hist_df = hist_df.drop(columns=['Datetime'])
        elif 'Date' in hist_df.columns:
            hist_df['Date'] = hist_df['Date'].astype(str)
        
        df = hist_df
        
        # 2. pandas-ta가 요구하는 소문자 컬럼명으로 변경
        df.rename(columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        }, inplace=True, errors='ignore') # 'errors' 플래그 추가

        if 'close' not in df.columns:
            return {"error": "데이터에 'close' (종가) 컬럼이 없습니다."}

        # --- [핵심 수정: 'append=True' 완전 제거] ---
        # 3. pandas-ta를 사용한 기술적 지표 계산 (명시적 할당)
        
        # 'append=True' 대신, 결과를 받아서 df의 새 컬럼으로 직접 할당합니다.
        df['RSI_14'] = df.ta.rsi(length=14)
        df['EMA_50'] = df.ta.ema(length=50)
        df['EMA_200'] = df.ta.ema(length=200)
        
        # .macd()는 여러 컬럼(DataFrame)을 반환합니다.
        # 'append=True' 없이 호출하면 DataFrame이 반환됩니다.
        macd_df = df.ta.macd(fast=12, slow=26, signal=9)
        
        # 반환된 macd_df (예: 'MACD_12_26_9' 컬럼 포함)를 원본 df와 합칩니다.
        df = pd.concat([df, macd_df], axis=1)
        # --- [수정 끝] ---
        
        # 4. 최신 데이터(마지막 행)만 추출
        latest_indicators = df.iloc[-1]
        
        # 5. AgentState에 저장할 깔끔한 dict로 반환
        result = {
            "last_close_price": latest_indicators.get('close'),
            "rsi_14": latest_indicators.get('RSI_14'),
            "ema_50": latest_indicators.get('EMA_50'),
            "ema_200": latest_indicators.get('EMA_200'),
            "macd": latest_indicators.get('MACD_12_26_9'),
            "macd_histogram": latest_indicators.get('MACDh_12_26_9'),
            "macd_signal": latest_indicators.get('MACDs_12_26_9'),
        }
        
        result_cleaned = {k: (None if pd.isna(v) else v) for k, v in result.items()}

        return result_cleaned
        
    except Exception as e:
        return {"error": f"기술적 분석 중 오류 발생: {str(e)}"}