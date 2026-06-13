import os
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "tinyllama")

GROQ_MODELS = {
    "best": "llama-3.3-70b-versatile",
    "fast": "llama-3.1-8b-instant",
    "code": "llama-3.3-70b-versatile",
}

GEMINI_MODEL = "gemini-1.5-flash"

REVIEW_MODES = ["full", "quick", "security", "performance", "roast"]
