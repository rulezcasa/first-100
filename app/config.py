"""Settings, read once from the repo-root .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Local model via Ollama (`ollama serve`): every LLM call, from the setup chat to the agents' turns.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
# Notional USD per million tokens for the dashboard's cost (the local model itself is free).
LLM_COST_PER_1M_INPUT = float(os.getenv("LLM_COST_PER_1M_INPUT", "0.15"))
LLM_COST_PER_1M_OUTPUT = float(os.getenv("LLM_COST_PER_1M_OUTPUT", "0.60"))

# The founder's side of Band: the web app posts to this room as the founder and mirrors it in the activity panel.
BAND_API_KEY = os.getenv("BAND_API_KEY", "")
BAND_ROOM_ID = os.getenv("BAND_ROOM_ID", "")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")  # web search: Scout's discovery, Researcher's evidence

HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")  # Researcher's contact lookup and email check

# Metering (PLAN.md §7): AI cost and confirmed revenue are sent here and read back by the Dashboard.
FLEXPRICE_API_KEY = os.getenv("FLEXPRICE_API_KEY", "")
# Flexprice can't delete events: a new customer id starts the metering over (resend with synced = 0).
FLEXPRICE_CUSTOMER = os.getenv("FLEXPRICE_CUSTOMER", "founder-1")
FLEXPRICE_API_URL = os.getenv("FLEXPRICE_API_URL", "https://us.api.flexprice.io/v1")  # India: https://api.cloud.flexprice.io/v1

DEMO_MODE = os.getenv("DEMO_MODE", "live")  # live | cache (replay only, no network)
CACHE_DIR = ROOT / "app" / "data" / "cache"
