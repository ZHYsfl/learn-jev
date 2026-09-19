"""最小 agent 运行时：一个带工具调用的 LLM 循环。

核心就是 loop：observations -> LLM -> tool_calls -> 并行执行工具 ->
结果追加回历史 -> ... 直到模型不再调用工具（finish_reason != "tool_calls"），
最后一条 assistant 消息即本轮最终回复。

模块划分：
- config.py   LLMConfig
- tool.py     ToolFunc / Tool / ToolResponse
- client.py   new_openai_client
- helpers.py  无状态纯函数：digest_args / log_round / validate_required_args / 错误判断与汇总
- agent.py    Agent、函数式选项、Loop、工具执行
"""

from .agent import (
    Agent,
    AgentOption,
    ChatCompletionError,
    with_before_round_hook,
    with_debug,
    with_max_tool_retries,
)
from .client import new_openai_client
from .config import LLMConfig
from .tool import Tool, ToolFunc, ToolResponse

__all__ = [
    "Agent",
    "AgentOption",
    "ChatCompletionError",
    "LLMConfig",
    "Tool",
    "ToolFunc",
    "ToolResponse",
    "new_openai_client",
    "with_before_round_hook",
    "with_debug",
    "with_max_tool_retries",
]
