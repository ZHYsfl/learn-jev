"""调用 OpenRouter decisions API（typesafe/jev-latest）的最小示例。

用法：在项目根目录的 .env 文件里配置 OPENROUTER_API_KEY，然后运行
    chapter/chapter_1/code/.venv/bin/python chapter/chapter_1/code/api_openrouter.py
"""

import json
import os
import urllib.request
from pathlib import Path

API_URL = "https://openrouter.ai/api/alpha/decisions"
ROOT_DIR = Path(__file__).resolve().parents[3]  # 本文件位于 chapter/chapter_1/code/，上三级即项目根目录


def load_env(path: Path) -> None:
    """加载 .env 到环境变量（已存在的环境变量优先，不覆盖）。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def decide(state: str, questions: dict, model: str = "~typesafe/jev-latest") -> dict:
    """调用 jev decisions 接口，返回响应字典（含 answers / usage / id 等）。"""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("缺少 OPENROUTER_API_KEY：请在项目根目录的 .env 文件中配置")

    body = json.dumps({"model": model, "state": state, "questions": questions}).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


QUESTIONS = {
    "is_urgent": {
        "type": "noul",
        "instructions": "Does this message convey urgency?",
        "criteria": {
            "true": "Explicitly time-sensitive",
            "false": "No urgency expressed",
        },
    },
    "department": {
        "type": "choice",
        "instructions": "Which team should handle this?",
        "criteria": {
            "billing": "Payments, invoicing, refunds",
            "technical": "Bugs, outages, integrations",
            "sales": "Pricing, upgrades, new accounts",
        },
    },
    "frustration": {
        "type": "score",
        "instructions": "How frustrated is the customer?",
        "criteria": ["Calm", "Frustrated", "Very angry"],
    },
}


def route(state: str) -> dict:
    """示例：把返回的决策结果用起来（noul→if，choice→match，score→阈值）。"""
    result = decide(state, QUESTIONS)
    answers = result["answers"]

    p_urgent = answers["is_urgent"]["noul"]      # Bernoulli 参数 p = P(true)
    department = answers["department"]["choice"]  # argmax 后的选项
    score = answers["frustration"]["score"]       # criteria 刻度上的连续值

    if p_urgent > 0.3:
        print(f"[紧急] P(true)={p_urgent:.2f}，进入加急通道")
    else:
        print(f"[普通] P(true)={p_urgent:.2f}，走正常流程")

    match department:
        case "billing":
            print("[路由] 转 billing 团队（支付/发票/退款）")
        case "technical":
            print("[路由] 转 technical 团队（故障/集成）")
        case "sales":
            print("[路由] 转 sales 团队（定价/新开户）")

    if score >= 1.5:
        print(f"[情绪] score={score:.2f}，客户非常愤怒，转人工安抚")
    else:
        print(f"[情绪] score={score:.2f}，按标准话术回复")

    return result


if __name__ == "__main__":
    load_env(ROOT_DIR / ".env")
    result = route("Help! My payouts have been failing for 3 days.")
    print("\n原始返回：")
    print(json.dumps(result, indent=2, ensure_ascii=False))
