"""查询天气的最小示例：真 LLM（OpenRouter）+ 模拟天气工具（不访问真实天气 API）。

虚拟环境：复用 chapter/chapter_2/code/.venv。
运行：
    chapter/chapter_2/code/.venv/bin/python chapter/chapter_2/code/agent_runtime/example/example.py

需要项目根目录 .env 里配置 OPENROUTER_API_KEY。
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # 上三级 = chapter/chapter_2/code

from agent_runtime import Agent, LLMConfig, Tool, with_debug  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parents[5]  # 上五级 = 项目根目录


def load_env(path: Path) -> None:
    """加载 .env（不覆盖已有环境变量）。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


# ─── 模拟天气工具 ───

FAKE_WEATHER_DB = {
    "北京": "晴，26°C，北风 2 级",
    "上海": "多云转小雨，22°C，东南风 3 级",
    "深圳": "雷阵雨，29°C，湿度 85%",
    "成都": "阴，20°C，微风",
}


def get_weather(args: dict) -> str:
    """模拟工具：查内置"数据库"，不发起真实网络请求。"""
    city = args["city"]
    if city in FAKE_WEATHER_DB:
        return f"{city}：{FAKE_WEATHER_DB[city]}"
    return f"{city}：模拟数据库里没有这个城市（只收录了：{'、'.join(FAKE_WEATHER_DB)}）"


GET_WEATHER_TOOL = Tool(
    name="get_weather",
    description="查询指定城市的实时天气",
    func=get_weather,
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名，如 北京、上海"},
        },
        "required": ["city"],
    },
)


async def main() -> None:
    load_env(ROOT_DIR / ".env")

    agent = Agent(
        LLMConfig(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
            model="openai/gpt-4o-mini",
        ),
        [GET_WEATHER_TOOL],
        with_debug(True),
    )

    question = "北京今天天气怎么样？适合出门跑步吗？"
    print(f"用户：{question}\n")

    history = await agent.loop([{"role": "user", "content": question}])

    print("\n--- 本轮历史 ---")
    for m in history:
        if m["role"] == "assistant" and m.get("tool_calls"):
            for tc in m["tool_calls"]:
                print(f"[assistant] 调用工具 {tc['function']['name']}({tc['function']['arguments']})")
        elif m["role"] == "assistant":
            print(f"[assistant] {m.get('content')}")
        elif m["role"] == "tool":
            print(f"[tool] {m['content']}")


if __name__ == "__main__":
    asyncio.run(main())
