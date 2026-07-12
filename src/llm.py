"""Provider-agnostic chat model factory.

Every agent gets its LLM client from get_llm() instead of importing a
provider SDK directly, so swapping providers is a one-line .env change
(LLM_PROVIDER + AGENT_MODEL + the matching API key) rather than a code
change anywhere in src/agents/.

Backed by LangChain's init_chat_model, which supports Anthropic, OpenAI,
Google Gemini, Groq, Mistral, xAI, Ollama, Fireworks, Together, Cohere,
Bedrock, Vertex AI, and more. See README.md for the full provider table,
including which pip package to install for each one.
"""
from langchain.chat_models import init_chat_model
from src.config import LLM_PROVIDER, AGENT_MODEL, LLM_API_KEY


def get_llm(temperature: float = 0.2):
    """Build a chat model client for the configured provider/model.

    `temperature` is per-call so each agent can pick its own value (e.g. the
    Reviewer wants 0.0 for consistency, the Tester wants a bit more for
    adversarial creativity) without needing its own factory function.
    """
    kwargs = {"temperature": temperature}
    if LLM_API_KEY:
        kwargs["api_key"] = LLM_API_KEY
    return init_chat_model(AGENT_MODEL, model_provider=LLM_PROVIDER, **kwargs)
