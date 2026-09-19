from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    extra_body: Optional[dict[str, Any]] = None
