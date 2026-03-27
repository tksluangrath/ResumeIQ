from __future__ import annotations

from typing import Any

from engine.llm.base import BaseLLM


def create_llm(settings: Any) -> BaseLLM:
    provider = settings.LLM_PROVIDER.lower()

    if provider == "ollama":
        from engine.llm.ollama_llm import OllamaLLM

        return OllamaLLM(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    elif provider == "claude":
        from engine.llm.claude_llm import ClaudeLLM

        return ClaudeLLM(
            api_key=settings.ANTHROPIC_API_KEY,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    elif provider == "openai":
        from engine.llm.openai_llm import OpenAILLM

        return OpenAILLM(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    elif provider == "deepseek":
        from engine.llm.openai_llm import OpenAILLM

        return OpenAILLM(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            model=settings.DEEPSEEK_MODEL,
            timeout=settings.LLM_TIMEOUT_SECONDS,
        )
    else:
        raise ValueError(
            f"Unknown LLM_PROVIDER '{provider}'. Valid options: ollama, claude, openai, deepseek"
        )
