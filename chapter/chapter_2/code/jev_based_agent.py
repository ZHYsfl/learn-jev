"""基于 jev decisions API 的 agent。"""
import json
import os
import sys
import urllib.request
from pathlib import Path

class JEVAgent:
    """JEV Based Agent，调用 jev decisions API 进行决策。"""

    def __init__(self, api_key: str, model: str = "~typesafe/jev-latest", api_url: str = "https://openrouter.ai/api/alpha/decisions"):
        self.api_key = api_key
        self.model = model
        self.api_url = api_url

    def decide(self, state: str, questions: dict) -> dict:
        """调用 jev decisions 接口，返回响应字典（含 answers / usage / id 等）。"""
        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("缺少 OPENROUTER_API_KEY：请在项目根目录的 .env 文件中配置")

        body = json.dumps({"model": self.model, "state": state, "questions": questions}).encode("utf-8")
        request = urllib.request.Request(
            self.api_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            return json.load(response)

    def action(self, state: str, questions: dict) -> dict:
        """调用 decide 方法获取决策结果，并返回 answers 字典。"""
        response = self.decide(state, questions)
        return response.get("answers", {})