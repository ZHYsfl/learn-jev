"""一键给每章的 code/ 目录准备虚拟环境。

用法（在项目根目录）：
    python env_setup.py

对每个 chapter/chapter_*/code/：
1. 还没有 .venv 就 `uv venv` 创建（已存在则跳过，不碰现有环境）
2. 有 requirements.txt 就 `uv pip install -r` 装进该 venv（没有就跳过）
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CODE_GLOB = "chapter/chapter_*/code"


def setup_code_dir(code_dir: Path) -> None:
    venv_dir = code_dir / ".venv"

    if venv_dir.exists():
        print(f"[跳过] {code_dir}：已有 .venv")
    else:
        print(f"[创建] {venv_dir}")
        subprocess.run(["uv", "venv"], cwd=code_dir, check=True)

    requirements = code_dir / "requirements.txt"
    if requirements.exists():
        print(f"[安装] {requirements}")
        env = {**os.environ, "VIRTUAL_ENV": str(venv_dir)}
        subprocess.run(["uv", "pip", "install", "-r", str(requirements)], cwd=code_dir, env=env, check=True)
    else:
        print(f"[跳过] {code_dir}：没有 requirements.txt")


def main() -> None:
    if not shutil.which("uv"):
        sys.exit("未找到 uv：请先安装（https://docs.astral.sh/uv/）")

    code_dirs = sorted(ROOT.glob(CODE_GLOB))
    if not code_dirs:
        sys.exit(f"没有找到 {CODE_GLOB} 目录")

    for code_dir in code_dirs:
        setup_code_dir(code_dir)
    print("完成")


if __name__ == "__main__":
    main()
