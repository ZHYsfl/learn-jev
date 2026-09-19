"""循环周边的无状态纯函数。"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DIGEST_KEYS = ("command", "path", "message", "content", "old_string", "input_token")


def digest_args(raw: str) -> str:
    """把工具参数压成一截短摘要：取优先级最高的第一个字符串参数的前 24 个字符。

    长参数不刷屏；Python 字符串本身就是码点序列，切片天然不在多字节字符中间劈开。
    """
    if not raw:
        return ""
    try:
        args = json.loads(raw)
    except json.JSONDecodeError:
        return ""
    if not isinstance(args, dict):
        return ""
    for key in _DIGEST_KEYS:
        value = args.get(key)
        if isinstance(value, str) and value:
            value = " ".join(value.split())
            if len(value) > 24:
                value = value[:24] + "…"
            return f"({value})"
    return ""


def log_round(start: float, round_no: int, response: Any) -> None:
    """记一轮 LLM 调用的账：耗时、prompt/completion token 数、结束原因、点名的工具。"""
    choice = response.choices[0]
    names = [
        tc.function.name + digest_args(tc.function.arguments or "")
        for tc in (choice.message.tool_calls or [])
    ]
    usage = response.usage
    logger.info(
        "llm round %d: %.3fs prompt=%s completion=%s finish=%s tools=%s",
        round_no,
        time.monotonic() - start,
        getattr(usage, "prompt_tokens", None),
        getattr(usage, "completion_tokens", None),
        choice.finish_reason,
        names,
    )


def validate_required_args(parameters: Optional[dict[str, Any]], args: dict[str, Any]) -> list[str]:
    """按 JSON Schema 的 required 字段，找出 args 里缺失的参数名。"""
    if not parameters:
        return []
    required = parameters.get("required")
    if not isinstance(required, list):
        return []
    return [name for name in required if isinstance(name, str) and name not in args]


def has_tool_errors(results: list[Any]) -> bool:
    return any(r.status == "error" for r in results)


def get_error_summary(results: list[Any]) -> str:
    parts = [
        f"- {r.error_type or 'unknown'}: {r.content[:200]}"
        for r in results
        if r.status == "error"
    ]
    return "\n".join(parts) if parts else "unknown error"
