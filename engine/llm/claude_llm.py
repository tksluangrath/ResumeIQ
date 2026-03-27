from __future__ import annotations

from engine.llm.base import BaseLLM, LLMConnectionError, LLMResponseError


class ClaudeLLM(BaseLLM):
    def __init__(self, api_key: str, timeout: int = 120) -> None:
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package required: pip install anthropic")

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for ClaudeLLM")

        self._client = anthropic.Anthropic(api_key=api_key)
        self._timeout = timeout

    def complete(self, prompt: str) -> str:
        import anthropic

        try:
            response = self._client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIConnectionError as exc:
            raise LLMConnectionError(
                f"Cannot connect to Claude API: {exc}"
            ) from exc
        except anthropic.APIError as exc:
            raise LLMResponseError(
                f"Claude API error: {exc}"
            ) from exc

        if not response.content:
            raise LLMResponseError("Claude returned an empty content list")
        return response.content[0].text.strip()

    @property
    def provider_name(self) -> str:
        return "claude/claude-3-5-haiku-20241022"
