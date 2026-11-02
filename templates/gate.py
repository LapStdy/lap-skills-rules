#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目门禁骨架：一条命令跑完全部检查，串行，退出码 0 才算完成。

把本文件复制到项目 `scripts/gate.py`，按项目实际删改 CHECKS：
每项是（说明, 命令列表, 是否必需）。可选检查缺工具时报 SKIP，不算失败；
必需检查缺工具按失败处理，避免「装不上就当通过」。

用法：
    python scripts/gate.py            # 跑到第一条失败为止
    python scripts/gate.py --keep-going  # 跑完全部，汇总失败项
    python scripts/gate.py --list     # 只打印将执行的命令
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

PY = sys.executable

# （说明, 命令, 是否必需）；按依赖顺序排，前面的失败会让后面的结论失去意义。
CHECKS: list[tuple[str, list[str], bool]] = [
    ("格式与静态检查", [PY, "-m", "ruff", "check", "."], True),
    ("格式", [PY, "-m", "ruff", "format", "--check", "."], True),
    ("类型", [PY, "-m", "mypy", "."], True),
    ("测试", [PY, "-m", "pytest", "-q"], True),
    ("依赖方向", ["lint-imports"], False),
    ("契约同步", [PY, "scripts/check_contracts.py"], False),
    ("结构上限", [PY, "scripts/check_structure.py", ".", "--allow", "structure-allow.txt"], True),
    ("交付物文字", [PY, "scripts/check_artifacts.py", "."], True),
]


def executable_state(command: list[str]) -> str:
    """返回 ok / skip / missing：python -m 查模块，其余查可执行文件。"""
    if len(command) >= 3 and command[1] == "-m":
        module = command[2]
        try:
            return "ok" if importlib.util.find_spec(module) else "skip"
        except (ImportError, ValueError):
            return "skip"
    return "ok" if shutil.which(command[0]) else "skip"


def run_check(label: str, command: list[str], required: bool) -> str:
    state = executable_state(command)
    if state == "skip":
        if required:
            print(f"[FAIL] {label}：命令不可用 → {' '.join(command)}")
            return "fail"
        print(f"[SKIP] {label}：未安装，跳过（少了这条证据）")
        return "skip"
    print(f"[RUN ] {label}：{' '.join(command)}")
    completed = subprocess.run(command, check=False)
    if completed.returncode == 0:
        print(f"[PASS] {label}")
        return "pass"
    print(f"[FAIL] {label}：退出码 {completed.returncode}")
    return "fail"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="项目门禁：串行跑完全部检查")
    parser.add_argument("--keep-going", action="store_true", help="失败后继续跑其余检查")
    parser.add_argument("--list", action="store_true", help="只打印将执行的命令")
    args = parser.parse_args(argv)
    if args.list:
        for label, command, required in CHECKS:
            print(f"{'必需' if required else '可选'}  {label}: {' '.join(command)}")
        return 0
    results: list[tuple[str, str]] = []
    for label, command, required in CHECKS:
        verdict = run_check(label, command, required)
        results.append((label, verdict))
        if verdict == "fail" and not args.keep_going:
            break
    failed = [label for label, verdict in results if verdict == "fail"]
    skipped = [label for label, verdict in results if verdict == "skip"]
    total = len(results)
    if failed:
        print(f"门禁：FAIL（{total} 项，失败：{'、'.join(failed)}）")
        return 1
    summary = f"门禁：PASS（{total} 项全绿"
    if skipped:
        summary += f"，跳过 {len(skipped)} 项：{'、'.join(skipped)}"
    print(summary + "）")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
