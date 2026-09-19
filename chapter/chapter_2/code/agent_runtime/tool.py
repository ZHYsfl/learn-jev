from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Union


ToolFunc = Callable[[dict[str, Any]], Union[str, Awaitable[str]]]


@dataclass
class Tool:
    name: str
    description: str
    func: ToolFunc
    parameters: dict[str, Any]  # JSON Schema（required 字段会被预校验）


@dataclass
class ToolResponse:
    """工具执行结果。

    message 是追加回历史的 tool 消息；status / error_type 供重试判断。
    """

    message: dict[str, Any]
    content: str
    status: str  # "success" or "error"
    error_type: Optional[str] = None  # parse_error / not_found / arg_error / exec_error
