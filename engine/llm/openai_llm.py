from __future__ import annotations

from engine.llm.base import BaseLLM, LLMConnectionError, LLMResponseError


class OpenAILLM(BaseLLM):
    def __init__(
        self,
        api_key: str,
        timeout: int = 120,
        base_url: str | None = None,
        model: str = "gpt-4o-mini",
    ) -> None:
        try:
            import openai
        except ImportError:
            raise ImportError("openai package required: pip install openai")

        if not api_key:
            raise ValueError("API key is required for OpenAILLM")

        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = openai.OpenAI(**kwargs)
        self._model = model
        self._timeout = timeout

    def complete(self, prompt: str) -> str:
        import openai

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )
        except openai.APIConnectionError as exc:
            raise LLMConnectionError(
                f"Cannot connect to OpenAI API: {exc}"
            ) from exc
        except openai.APIError as exc:
            raise LLMResponseError(
                f"OpenAI API error: {exc}"
            ) from exc

        content = response.choices[0].message.content
        if not content:
            raise LLMResponseError("OpenAI returned an empty message content")
        return content.strip()

    @property
    def provider_name(self) -> str:
        return f"openai/{self._model}"
