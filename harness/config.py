import os

# Rate limiting — keeps Groq well under 30 req/min
SLEEP_BETWEEN_CALLS = 4.0  # seconds between each API call (~15 req/min, safe headroom)
MAX_RETRIES = 8
BACKOFF_BASE = 2  # exponential backoff multiplier on 429 errors
# On first 429, wait at least 65s so the per-minute window resets
FIRST_429_WAIT = 65.0

# Model IDs
# Evaluator fixed to 8b — 70b free tier has only 100K tokens/day (hits ceiling after ~117 conditions)
TASK_MODEL = "llama-3.1-8b-instant"

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# API keys from environment
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# OpenRouter models use OR base URL; all others use Groq
OPENROUTER_MODELS = {
    "qwen/qwen-2.5-72b-instruct",
    "meta-llama/llama-3.3-70b-instruct",  # M2 via OpenRouter (Groq free tier too limited)
}


def get_client(model_id: str):
    """Return an openai.OpenAI client configured for the correct provider."""
    from openai import OpenAI
    if model_id in OPENROUTER_MODELS:
        return OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    else:
        return OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
