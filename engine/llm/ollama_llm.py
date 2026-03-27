from __future__ import annotations

import httpx

from engine.llm.base import BaseLLM, LLMConnectionError, LLMResponseError


class OllamaLLM(BaseLLM):
    def __init__(self, base_url: str, model: str, timeout: int = 120) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    def complete(self, prompt: str) -> str:
        url = f"{self._base_url}/api/generate"
        payload = {"model": self._model, "prompt": prompt, "stream": False}

        try:
            response = httpx.post(url, json=payload, timeout=self._timeout)
        except httpx.ConnectError as exc:
            raise LLMConnectionError(
                f"Cannot connect to Ollama at {self._base_url}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise LLMConnectionError(
                f"Ollama request timed out after {self._timeout}s"
            ) from exc

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise LLMResponseError(
                f"Ollama returned HTTP {response.status_code}: {response.text}"
            ) from exc

        data = response.json()
        text = data.get("response", "")

        if not text:
            raise LLMResponseError("Ollama returned an empty response")

        return text.strip()

    @property
    def provider_name(self) -> str:
        return f"ollama/{self._model}"
