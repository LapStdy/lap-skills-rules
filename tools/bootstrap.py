#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键开工：把交付物规矩与检查器装进一个新项目。

用法：
    python tools/bootstrap.py <项目目录>            # 安装（不覆盖已有文件）
    python tools/bootstrap.py <项目目录> --check    # 只检查项目侧与仓库是否漂移
    python tools/bootstrap.py <项目目录> --update   # 用仓库版本覆盖检查器

做三件事：
1. 把 tools/check_artifacts.py 复制到 <项目目录>/scripts/
2. 没有 AGENTS.md 就按模板生成；已有就只追加「交付物通道」一节
3. 打印下一步

目标目录不存在会自动创建；默认不覆盖已有内容。AGENTS.md 的更新只做追加，
已有版本里的规则段落需要人工按仓库模板同步。
"""

from __future__ import annotations

import argparse
import hashlib
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


def digest(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def check(target: Path) -> int:
    scripts = target / "scripts"
    dest = scripts / "check_artifacts.py"
    agents = target / "AGENTS.md"
    drift = False

    if not dest.is_file():
        print("缺少：scripts/check_artifacts.py")
        drift = True
    elif digest(dest) != digest(CHECKER):
        print("漂移：scripts/check_artifacts.py 与仓库不一致（用 --update 覆盖）")
        drift = True
    else:
        print("一致：scripts/check_artifacts.py")

    if not agents.is_file():
        print("缺少：AGENTS.md")
        drift = True
    elif SESSION_START not in agents.read_text(encoding="utf-8"):
        print("漂移：AGENTS.md 缺少「交付物通道」一节")
        drift = True
    else:
        print("存在：AGENTS.md 交付物通道")

    return 1 if drift else 0


def main(argv: list) -> int:
    ap = argparse.ArgumentParser(description="把交付物规矩与检查器装进一个新项目")
    ap.add_argument("target", help="新项目目录")
    ap.add_argument("--check", action="store_true", help="只检查漂移，不写盘")
    ap.add_argument("--update", action="store_true", help="用仓库版本覆盖检查器")
    args = ap.parse_args(argv)

    target = Path(args.target).resolve()
    if args.check:
        if not target.is_dir():
            print(f"目标目录不存在：{target}", file=sys.stderr)
            return 2
        return check(target)

    target.mkdir(parents=True, exist_ok=True)

    scripts = target / "scripts"
    scripts.mkdir(exist_ok=True)
    dest = scripts / "check_artifacts.py"
    if dest.exists() and not args.update:
        print(f"跳过：{dest} 已存在（需要覆盖用 --update）")
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
            print(f"跳过：{agents} 已有交付物通道（规则段落需按模板人工同步）")
        else:
            agents.write_text(
                old.rstrip() + "\n\n" + section_of(template), encoding="utf-8"
            )
            print(f"已追加规矩：{agents}")

    print()
    print("下一步：")
    print(f"  1. cd {target}")
    print("  2. python scripts/check_artifacts.py .")
    print("  3. 把项目目标、技术栈、首个里程碑写进 README")
    print("  4. 需要本仓库技能时，在仓库根运行 python tools/install_skills.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
