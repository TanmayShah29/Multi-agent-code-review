"""Unit tests for src.config — configuration and API key resolution."""

import os
from unittest.mock import patch

from src.config import _resolve_api_key, EXECUTION_TIMEOUT, MAX_ITERATIONS


class TestResolveApiKey:
    def test_returns_llm_api_key_override(self):
        with patch.dict(os.environ, {"LLM_API_KEY": "test-key-123"}):
            assert _resolve_api_key("openai") == "test-key-123"

    def test_returns_none_when_no_key(self):
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("LLM_API_KEY", None)
            os.environ.pop("OPENAI_API_KEY", None)
            os.environ.pop("GEMINI_API_KEY", None)
            os.environ.pop("GOOGLE_API_KEY", None)
            result = _resolve_api_key("openai")
            assert result is None

    def test_resolves_google_key(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "gemini-key"}):
            assert _resolve_api_key("google_genai") == "gemini-key"

    def test_resolves_anthropic_key(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "anthropic-key"}):
            assert _resolve_api_key("anthropic") == "anthropic-key"


class TestConfigConstants:
    def test_execution_timeout_positive(self):
        assert EXECUTION_TIMEOUT > 0

    def test_max_iterations_positive(self):
        assert MAX_ITERATIONS > 0
