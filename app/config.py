"""Settings, read once from the repo-root .env."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Local model via Ollama (`ollama serve`): every LLM call, from the setup chat to the agents' turns.
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

# The founder's side of Band: the web app posts to this room as the founder and mirrors it in the activity panel.
BAND_API_KEY = os.getenv("BAND_API_KEY", "")
BAND_ROOM_ID = os.getenv("BAND_ROOM_ID", "")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")  # web search: Scout's discovery, Researcher's evidence

HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")  # Researcher's contact lookup and email check

DEMO_MODE = os.getenv("DEMO_MODE", "live")  # live | cache (replay only, no network)
CACHE_DIR = ROOT / "app" / "data" / "cache"
