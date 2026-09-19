from __future__ import annotations

from openai import AsyncOpenAI

from .config import LLMConfig


def new_openai_client(config: LLMConfig) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)
