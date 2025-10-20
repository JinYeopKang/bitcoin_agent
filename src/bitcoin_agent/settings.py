import os
from pathlib import Path
from dotenv import load_dotenv

# .env 파일이 프로젝트 루트에 있다고 가정
# (run.py가 이미 로드했겠지만, 개별 파일 테스트를 위해 여기서도 로드 가능)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

# --- 1. API 키 (환경 변수에서 직접 로드) ---
# (이 파일 자체에 키를 하드코딩하지 않습니다-매우 중요함.)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")

# --- 2. LLM 모델 설정 ---
# (모델을 쉽게 교체할 수 있도록 중앙 관리)
PLANNER_MODEL = "gpt-4o"
ANALYSIS_MODEL = "gpt-4o"
REFLECTION_MODEL = "gpt-4o-mini" # (예시: 비평은 더 빠르고 저렴한 모델 사용)

# --- 3. 프롬프트 경로 ---
# (경로 기준: 이 파일(settings.py)이 있는 src/bitcoin_agent/ 기준)
PROMPTS_DIR = BASE_DIR / "prompts"

PLANNER_PROMPT_PATH = PROMPTS_DIR / "planner.md"
ANALYSIS_PROMPT_PATH = PROMPTS_DIR / "analysis.md"
REFLECTION_PROMPT_PATH = PROMPTS_DIR / "reflection.md"

# --- 4. 기타 설정 ---
DEFAULT_TICKER = "BTC-USD"
DEFAULT_MARKET_DATA_PERIOD = "1y" # TA 계산을 위해 충분한 기간
DEFAULT_SEARCH_PERIOD = "1mo" # 뉴스는 최근 1달간