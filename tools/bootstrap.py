#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键开工：把交付物规矩与可验证的门禁装进一个新项目。

用法：
    python tools/bootstrap.py <项目目录>            # 安装（不覆盖已有文件）
    python tools/bootstrap.py <项目目录> --check    # 只检查项目侧与仓库是否漂移
    python tools/bootstrap.py <项目目录> --update   # 用仓库版本覆盖已装文件

装四样东西：
1. `scripts/check_artifacts.py`（交付物检查器）
2. `scripts/check_structure.py`（结构上限检查器）
3. `scripts/gate.py`（门禁骨架，串行跑全部检查）
4. `AGENTS.md`（没有就按模板生成；已有就只追加缺失的规矩章节）

目标目录不存在会自动创建；默认不覆盖已有文件。
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
INSTALLS = (
    (REPO / "tools" / "check_artifacts.py", "scripts/check_artifacts.py"),
    (REPO / "tools" / "check_structure.py", "scripts/check_structure.py"),
    (REPO / "templates" / "gate.py", "scripts/gate.py"),
)
SECTIONS = ("## 交付物通道", "## 完成判据", "## 账本")


def digest(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def check(target: Path) -> int:
    drift = False
    for _, relative in INSTALLS:
        dest = target / relative
        source = next(src for src, rel in INSTALLS if rel == relative)
        if not dest.is_file():
            print(f"缺少：{relative}")
            drift = True
        elif digest(dest) != digest(source):
            print(f"漂移：{relative} 与仓库不一致（用 --update 覆盖）")
            drift = True
        else:
            print(f"一致：{relative}")
    agents = target / "AGENTS.md"
    if not agents.is_file():
        print("缺少：AGENTS.md")
        drift = True
    else:
        text = agents.read_text(encoding="utf-8")
        missing = [section for section in SECTIONS if section not in text]
        if missing:
            print(f"漂移：AGENTS.md 缺少 {'、'.join(missing)}")
            drift = True
        else:
            print("存在：AGENTS.md 三段规矩")
    return 1 if drift else 0


def install_files(target: Path, update: bool) -> None:
    for source, relative in INSTALLS:
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and not update:
            print(f"跳过：{relative} 已存在（需要覆盖用 --update）")
            continue
        shutil.copy2(source, dest)
        print(f"已装：{relative}")


def install_agents(target: Path) -> None:
    template = TEMPLATE.read_text(encoding="utf-8").replace("<项目名>", target.name)
    agents = target / "AGENTS.md"
    if not agents.exists():
        agents.write_text(template, encoding="utf-8")
        print("已生成：AGENTS.md")
        return
    old = agents.read_text(encoding="utf-8")
    missing = [section for section in SECTIONS if section not in old]
    if not missing:
        print("跳过：AGENTS.md 已有全部规矩章节")
        return
    blocks = []
    for section in missing:
        start = template.find(section)
        if start < 0:
            continue
        nxt = template.find("\n## ", start + 1)
        blocks.append(template[start:] if nxt < 0 else template[start:nxt])
    agents.write_text(old.rstrip() + "\n\n" + "\n".join(blocks), encoding="utf-8")
    print(f"已追加规矩章节：{'、'.join(section.lstrip('# ') for section in missing)}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="把交付物规矩与门禁装进一个新项目")
    parser.add_argument("target", help="新项目目录")
    parser.add_argument("--check", action="store_true", help="只检查漂移，不写盘")
    parser.add_argument("--update", action="store_true", help="用仓库版本覆盖已装文件")
    args = parser.parse_args(argv)

    target = Path(args.target).resolve()
    if args.check:
        if not target.is_dir():
            print(f"目标目录不存在：{target}", file=sys.stderr)
            return 2
        return check(target)

    target.mkdir(parents=True, exist_ok=True)
    install_files(target, args.update)
    install_agents(target)

    print()
    print("下一步：")
    print(f"  1. cd {target}")
    print("  2. python scripts/gate.py            # 首次会因缺少工具与实现而红，按输出逐条补齐")
    print("  3. 把项目目标、技术栈、首个里程碑写进 README")
    print("  4. 既有超限写进 structure-allow.txt 并在 DEBT.md 记账")
    print("  5. 需要本仓库技能时，在仓库根运行 python tools/install_skills.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
