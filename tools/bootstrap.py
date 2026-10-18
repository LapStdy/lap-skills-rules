#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键开工：把交付物规矩与检查器装进一个新项目。

用法：
    python tools/bootstrap.py <项目目录>

做三件事：
1. 把 tools/check_artifacts.py 复制到 <项目目录>/scripts/
2. 没有 AGENTS.md 就按模板生成；已有就只追加「交付物通道」一节
3. 打印下一步

目标目录不存在会自动创建；已装过则跳过，不覆盖已有内容。
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / "templates" / "AGENTS.md"
CHECKER = REPO / "tools" / "check_artifacts.py"
SESSION_START = "## 交付物通道"


def section_of(template_text: str) -> str:
    idx = template_text.find(SESSION_START)
    return template_text[idx:] if idx >= 0 else template_text


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="把交付物规矩与检查器装进一个新项目")
    ap.add_argument("target", help="新项目目录")
    args = ap.parse_args(argv)

    target = Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)

    scripts = target / "scripts"
    scripts.mkdir(exist_ok=True)
    dest = scripts / "check_artifacts.py"
    if dest.exists():
        print(f"跳过：{dest} 已存在")
    else:
        shutil.copy2(CHECKER, dest)
        print(f"已装检查器：{dest}")

    template = TEMPLATE.read_text(encoding="utf-8").replace("<项目名>", target.name)
    agents = target / "AGENTS.md"
    if not agents.exists():
        agents.write_text(template, encoding="utf-8")
        print(f"已生成：{agents}")
    else:
        old = agents.read_text(encoding="utf-8")
        if SESSION_START in old:
            print(f"跳过：{agents} 已有交付物通道")
        else:
            agents.write_text(old.rstrip() + "\n\n" + section_of(template), encoding="utf-8")
            print(f"已追加规矩：{agents}")

    print()
    print("下一步：")
    print(f"  1. cd {target}")
    print("  2. python scripts/check_artifacts.py .")
    print("  3. 把项目目标、技术栈、首个里程碑写进 README")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
