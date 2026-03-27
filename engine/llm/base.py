from __future__ import annotations

from abc import ABC, abstractmethod


class BaseLLM(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> str: ...

    @property
    @abstractmethod
    def provider_name(self) -> str: ...


class LLMConnectionError(RuntimeError): ...


class LLMResponseError(RuntimeError): ...
