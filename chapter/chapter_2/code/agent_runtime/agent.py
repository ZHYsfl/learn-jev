"""Agent：结构、函数式选项、工具执行，以及核心的 LLM 循环（loop）。

无状态的纯函数在 helpers.py，数据结构与客户端在 tool.py / config.py / client.py。
"""

from __future__ import annotations

import asyncio
import inspect
import json
import time
from typing import Any, Callable, Optional

from .client import new_openai_client
from .config import LLMConfig
from .helpers import (
    get_error_summary,
    has_tool_errors,
    log_round,
    validate_required_args,
)
from .tool import Tool, ToolResponse

# 函数式选项：with_debug / with_before_round_hook / with_max_tool_retries
AgentOption = Callable[["Agent"], None]


class ChatCompletionError(RuntimeError):
    """LLM 调用失败。partial_messages 是出错前已累积的历史（部分回合不丢）。"""

    def __init__(self, message: str, partial_messages: list[dict[str, Any]]):
        super().__init__(message)
        self.partial_messages = partial_messages


def with_debug(debug: bool) -> AgentOption:
    return lambda a: setattr(a, "debug", debug)


def with_before_round_hook(f: Callable[[], list[dict[str, Any]]]) -> AgentOption:
    """注入"每次 LLM 调用前的附加消息"（每次调用都触发，包括工具轮）。"""
    return lambda a: setattr(a, "before_round_hook", f)


def with_max_tool_retries(max_tool_retries: int) -> AgentOption:
    return lambda a: setattr(a, "max_tool_retries", max_tool_retries)


class Agent:
    def __init__(
        self,
        config: LLMConfig,
        tools: Optional[list[Tool]] = None,
        *opts: AgentOption,
    ):
        self.client = new_openai_client(config)
        self.config = config
        self.tools = list(tools or [])
        self.debug = False
        self.max_tool_retries = 3
        # 非 None 时，每次 LLM 调用前（含工具轮）追加它返回的消息，
        # 让长回合内的每轮调用都看得见"此刻"
        self.before_round_hook: Optional[Callable[[], list[dict[str, Any]]]] = None
        for opt in opts:
            opt(self)

    def add_tool(self, tool: Tool) -> None:
        self.tools.append(tool)

    def remove_tool(self, name: str) -> None:
        self.tools = [t for t in self.tools if t.name != name]

    def get_tools(self) -> list[dict[str, Any]]:
        """转换为 OpenAI tools 格式。"""
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self.tools
        ]

    def build_params(self, messages: list[dict[str, Any]], with_tools: bool) -> dict[str, Any]:
        """组装请求参数：可选字段只在非 None 时才下发。"""
        params: dict[str, Any] = {"model": self.config.model, "messages": messages}
        if with_tools:
            params["tools"] = self.get_tools()
            params["tool_choice"] = "auto"
        for key in ("temperature", "top_p", "presence_penalty", "frequency_penalty"):
            value = getattr(self.config, key)
            if value is not None:
                params[key] = value
        if self.config.max_tokens is not None:
            params["max_tokens"] = self.config.max_tokens
        if self.config.extra_body is not None:
            params["extra_body"] = self.config.extra_body
        return params

    async def _execute_tool_call_func(
        self,
        tool_call_id: str,
        func_name: str,
        raw_args: str,
        available_tools: dict[str, Tool],
    ) -> ToolResponse:
        def fail(content: str, error_type: str) -> ToolResponse:
            if self.debug:
                print(f"[ERROR] {content}")
            return ToolResponse(
                message={"role": "tool", "content": content, "tool_call_id": tool_call_id},
                content=content,
                status="error",
                error_type=error_type,
            )

        args: dict[str, Any] = {}
        if raw_args and raw_args.strip() and raw_args != "{}":
            try:
                parsed = json.loads(raw_args)
                if isinstance(parsed, dict):
                    args = parsed
            except json.JSONDecodeError as e:
                return fail(f"[PARSE_ERROR] JSON parse failed: {e}. Raw: '{raw_args}'", "parse_error")

        tool = available_tools.get(func_name)
        if tool is None:
            return fail(f"[NOT_FOUND] Function '{func_name}' not found", "not_found")

        # 先按 JSON Schema 的 required 校验，再真正调用
        missing = validate_required_args(tool.parameters, args)
        if missing:
            return fail(
                f"[ARG_ERROR] Missing required arguments for '{func_name}': {missing}",
                "arg_error",
            )

        if self.debug:
            print(f"[DEBUG] Executing {func_name} with args: {sorted(args)}")

        try:
            result = tool.func(args)
            if inspect.isawaitable(result):
                result = await result
        except Exception as e:
            return fail(f"[EXEC_ERROR] Execution failed: {e}", "exec_error")

        content = str(result)
        if self.debug:
            print(f"[DEBUG] Tool {func_name} returned (id={tool_call_id}): {content}")
        return ToolResponse(
            message={"role": "tool", "content": content, "tool_call_id": tool_call_id},
            content=content,
            status="success",
        )

    async def _execute_tool_call(self, tool_call: Any, available_tools: dict[str, Tool]) -> ToolResponse:
        # 只支持 function 类型的工具调用
        tool_call_id = getattr(tool_call, "id", None)
        if not tool_call_id:
            content = "[NOT_FOUND] Unsupported tool call type (only function tool calls are supported)"
            if self.debug:
                print(f"[ERROR] {content}")
            return ToolResponse(
                message={"role": "tool", "content": content, "tool_call_id": "unsupported-tool-call"},
                content=content,
                status="error",
                error_type="not_found",
            )
        return await self._execute_tool_call_func(
            tool_call_id,
            tool_call.function.name,
            tool_call.function.arguments or "",
            available_tools,
        )

    async def _get_tool_responses(self, tool_calls: list[Any]) -> list[ToolResponse]:
        """并行执行所有工具调用，结果保持调用顺序。"""
        available_tools = {t.name: t for t in self.tools}
        return list(
            await asyncio.gather(*(self._execute_tool_call(tc, available_tools) for tc in tool_calls))
        )

    async def loop(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """喂消息给 LLM，执行工具调用并把结果追加回历史，直到模型不再调用工具。

        出错抛 ChatCompletionError，已累积的历史挂在异常的 partial_messages 上（部分回合不丢）。"""
        if self.before_round_hook is not None:
            messages = [*messages, *self.before_round_hook()]
        params = self.build_params(messages, with_tools=True)

        start = time.monotonic()
        try:
            response = await self.client.chat.completions.create(**params)
        except Exception as e:
            # 首次调用就失败：没有产生任何新内容，部分历史 = 输入本身
            raise ChatCompletionError(f"failed to get chat completion: {e}", list(messages)) from e
        log_round(start, 1, response)

        next_messages = list(messages)
        retry_count = 0
        round_no = 1

        while response.choices[0].finish_reason == "tool_calls":
            next_messages.append(response.choices[0].message.model_dump())

            tool_results = await self._get_tool_responses(response.choices[0].message.tool_calls)
            for tr in tool_results:
                next_messages.append(tr.message)

            if has_tool_errors(tool_results) and retry_count < self.max_tool_retries:
                retry_count += 1
                summary = get_error_summary(tool_results)
                if self.debug:
                    print(f"[RETRY {retry_count}/{self.max_tool_retries}] Tool errors:\n{summary}")
                next_messages.append({
                    "role": "user",
                    "content": (
                        f"Tool execution errors detected:\n\n{summary}\n\n"
                        f"Please fix and retry. Retries left: {self.max_tool_retries - retry_count}"
                    ),
                })

            if self.debug:
                print(
                    f"[DEBUG] Sending {len(next_messages)} messages to LLM:\n"
                    f"{json.dumps(next_messages, ensure_ascii=False, indent=2)}"
                )

            if self.before_round_hook is not None:
                next_messages = [*next_messages, *self.before_round_hook()]
            params["messages"] = next_messages

            round_no += 1
            start = time.monotonic()
            try:
                response = await self.client.chat.completions.create(**params)
            except Exception as e:
                raise ChatCompletionError(f"chat completion (tool loop): {e}", next_messages) from e
            log_round(start, round_no, response)

        next_messages.append(response.choices[0].message.model_dump())
        return next_messages
