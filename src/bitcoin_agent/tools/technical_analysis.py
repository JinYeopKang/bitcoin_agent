import pandas as pd
import pandas_ta as ta  # [Req 2: 부가 기능] pandas-ta 라이브러리 활용
from langchain_core.tools import tool
from typing import Dict, Any

# [Req 1: 코드 가독성]
# 이 도구는 market_data.py의 도구와 의도적으로 분리되었습니다.
# Agent가 "원천 데이터"만 볼지, "가공된 지표"를 볼지 선택할 수 있게 하기 위함입니다.
# 
# 이 도구는 자체적으로 yfinance를 호출합니다. (데이터 중복 호출)
# 장점: 도구의 독립성 보장 (Agent가 이 도구 하나만 호출해도 작동함)
# 대안: AgentState에서 market_data를 읽어오도록 그래프 로직을 짤 수도 있으나,
#      'Tool'로서의 명확성을 위해 독립적으로 작동하게 설계합니다.

from .market_data import get_ohlcv_data # 동일한 로직으로 데이터를 가져오기 위해 import

@tool
def calculate_technical_indicators(ticker: str = "BTC-USD", period: str = "30d") -> Dict[str, Any]:
    """
    주요 기술적 분석 지표(RSI, 50/200일 이동평균, MACD)를 계산합니다.
    Agent는 이 도구를 사용해 현재 시장의 과매수/과매도, 추세 등을 파악합니다.

    Args:
        ticker (str): 분석할 티커. (예: 'BTC-USD')
        period (str): 분석에 사용할 데이터 기간. (예: "90d", "6mo")
                      이평선을 위해 최소 200일 이상("250d" 또는 "1y")을 권장합니다.

    Returns:
        Dict[str, Any]: 
        성공 시: {'rsi': 55.0, 'ma_50': 60000, 'ma_200': 50000, 'macd_signal': ...}
        실패 시: {'error': '...에러 메시지...'}
    """
    try:
        # 1. 데이터 가져오기 (이평선 계산을 위해 충분한 기간 필요)
        # 이 도구는 최소 200일 이평선이 필요하므로 period를 "1y" (1년)로 고정
        raw_data = get_ohlcv_data(ticker=ticker, period="1y", interval="1d")
        
        if raw_data.get("error"):
            return raw_data # 에러 메시지를 그대로 반환

        df = pd.DataFrame(raw_data["data"])
        
        if 'Close' not in df.columns:
            return {"error": "데이터에 'Close' (종가) 컬럼이 없습니다."}

        # 2. pandas-ta를 사용한 기술적 지표 계산
        df.ta.rsi(length=14, append=True)       # RSI (14일)
        df.ta.ema(length=50, append=True)       # EMA (50일)
        df.ta.ema(length=200, append=True)      # EMA (200일)
        df.ta.macd(fast=12, slow=26, signal=9, append=True) # MACD
        
        # 3. 최신 데이터(마지막 행)만 추출
        latest_indicators = df.iloc[-1]
        
        # 4. AgentState에 저장할 깔끔한 dict로 반환
        result = {
            "last_close_price": latest_indicators.get('Close'),
            "rsi_14": latest_indicators.get('RSI_14'),
            "ema_50": latest_indicators.get('EMA_50'),
            "ema_200": latest_indicators.get('EMA_200'),
            "macd": latest_indicators.get('MACD_12_26_9'),
            "macd_histogram": latest_indicators.get('MACDh_12_26_9'),
            "macd_signal": latest_indicators.get('MACDs_12_26_9'),
        }
        
        # NaN (Not a Number) 값이 있으면 None으로 변환 (JSON 호환)
        result_cleaned = {k: (None if pd.isna(v) else v) for k, v in result.items()}

        return result_cleaned
        
    except Exception as e:
        return {"error": f"기술적 분석 중 오류 발생: {str(e)}"}