"""Central config for the multi-agent workflow. Reads from environment / .env.

Provider-agnostic by design: works with any chat model LangChain's
init_chat_model() supports (Anthropic, OpenAI, Google Gemini, Groq, Mistral,
xAI, Ollama, Fireworks, Together, Cohere, Bedrock, Vertex AI, ...). See
README.md for the full provider table and example models.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Which LangChain provider to use — must match a provider string accepted by
# langchain.chat_models.init_chat_model, e.g.:
#   anthropic | openai | google_genai | groq | mistralai | xai | ollama |
#   fireworks | together | cohere | bedrock | google_vertexai
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google_genai")

# Model name/id for the chosen provider, e.g. "claude-sonnet-4-6", "gpt-5",
# "gemini-2.5-flash", "llama-3.3-70b-versatile", "mistral-large-latest".
AGENT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash")

MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "4"))
EXECUTION_TIMEOUT = int(os.getenv("EXECUTION_TIMEOUT", "10"))
SANDBOX_BACKEND = os.getenv("SANDBOX_BACKEND", "subprocess")

# Env var name(s) checked for each provider's API key, in priority order.
# LLM_API_KEY always wins if set, regardless of provider — a universal
# override for anyone who doesn't want to remember provider-specific names.
_PROVIDER_KEY_ENV_VARS = {
    "anthropic": ["ANTHROPIC_API_KEY"],
    "openai": ["OPENAI_API_KEY"],
    "google_genai": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
    "google_vertexai": ["GOOGLE_API_KEY"],
    "groq": ["GROQ_API_KEY"],
    "mistralai": ["MISTRAL_API_KEY"],
    "xai": ["XAI_API_KEY"],
    "fireworks": ["FIREWORKS_API_KEY"],
    "together": ["TOGETHER_API_KEY"],
    "cohere": ["COHERE_API_KEY"],
    "deepseek": ["DEEPSEEK_API_KEY"],
    "ollama": [],  # local model server, no API key needed
    "bedrock": [],  # uses AWS credentials, not a single API key
}


def _resolve_api_key(provider: str) -> str | None:
    override = os.getenv("LLM_API_KEY")
    if override:
        return override
    for var in _PROVIDER_KEY_ENV_VARS.get(provider, []):
        value = os.getenv(var)
        if value:
            return value
    return None


LLM_API_KEY = _resolve_api_key(LLM_PROVIDER)

_KEYLESS_PROVIDERS = {"ollama", "bedrock"}

if LLM_PROVIDER not in _KEYLESS_PROVIDERS and not LLM_API_KEY:
    expected_vars = _PROVIDER_KEY_ENV_VARS.get(LLM_PROVIDER) or ["LLM_API_KEY"]
    raise RuntimeError(
        f"No API key found for LLM_PROVIDER={LLM_PROVIDER!r}. Set one of "
        f"{expected_vars} in your .env (or the universal LLM_API_KEY). "
        f"Copy .env.example for a template, or see README.md for the full "
        f"provider table."
    )
