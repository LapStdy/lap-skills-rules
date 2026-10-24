#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把仓库 skills/ 安装到 DSH 用户级技能目录。

用法：
    python tools/install_skills.py                 # 安装/更新全部技能
    python tools/install_skills.py --check         # 只比对，不写盘
    python tools/install_skills.py --dry-run       # 打印会做什么，不写盘
    python tools/install_skills.py --dest <目录>   # 指定安装目录
    python tools/install_skills.py first-principles function-spec   # 只装指定技能

规则：
- 仓库是唯一真源；安装副本只读，不回写仓库。
- 默认覆盖同名文件；安装目录里多出来的文件不删除，只在 --check 时报告。
- 安装前校验 SKILL.md：存在、frontmatter 有 name/description、name 与目录名一致。
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"
DEFAULT_DEST = Path.home() / ".dsh" / "skills"
FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.S)
NAME_LINE = re.compile(r"^name:\s*(\S+)\s*$", re.M)
DESC_LINE = re.compile(r'^description:\s*"?(.*?)"?\s*$', re.M)


def read_frontmatter(skill_md: Path) -> tuple[str, str] | None:
    text = skill_md.read_text(encoding="utf-8")
    match = FRONTMATTER.match(text)
    if not match:
        return None
    block = match.group(1)
    name = NAME_LINE.search(block)
    desc = DESC_LINE.search(block)
    if not name or not desc:
        return None
    return name.group(1).strip(), desc.group(1).strip()


def validate(skill_dir: Path) -> list[str]:
    problems: list[str] = []
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        return [f"{skill_dir.name}: 缺少 SKILL.md"]
    front = read_frontmatter(md)
    if front is None:
        return [f"{skill_dir.name}: frontmatter 缺少 name 或 description"]
    name, desc = front
    if name != skill_dir.name:
        problems.append(f"{skill_dir.name}: name={name} 与目录名不一致")
    if not desc:
        problems.append(f"{skill_dir.name}: description 为空")
    elif len(desc) > 500:
        problems.append(f"{skill_dir.name}: description {len(desc)} 字符，超过 500")
    if "disable-model-invocation" in md.read_text(encoding="utf-8"):
        problems.append(f"{skill_dir.name}: 含 disable-model-invocation，模型将不可达")
    return problems


TEXT_SUFFIXES = {".md", ".py", ".ps1", ".sh", ".json", ".txt", ".yaml", ".yml", ".toml"}


def digest(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def relative_files(root: Path) -> set[Path]:
    return {
        p.relative_to(root)
        for p in root.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
    }


def compare(src: Path, dest: Path) -> tuple[list[Path], list[Path], list[Path]]:
    src_files = relative_files(src)
    dest_files = relative_files(dest) if dest.is_dir() else set()
    missing = sorted(src_files - dest_files)
    extra = sorted(dest_files - src_files)
    changed = sorted(
        rel
        for rel in (src_files & dest_files)
        if digest(src / rel) != digest(dest / rel)
    )
    return missing, changed, extra


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="把仓库 skills/ 安装到 DSH 用户级技能目录"
    )
    parser.add_argument("names", nargs="*", help="只处理指定技能（缺省全部）")
    parser.add_argument(
        "--dest", default=str(DEFAULT_DEST), help="安装目录（默认 ~/.dsh/skills）"
    )
    parser.add_argument("--check", action="store_true", help="只比对，不写盘")
    parser.add_argument("--dry-run", action="store_true", help="打印计划，不写盘")
    parser.add_argument(
        "--uninstall", action="store_true", help="从安装目录删除指定技能"
    )
    args = parser.parse_args(argv)

    if not SKILLS.is_dir():
        print(f"错误：找不到 {SKILLS}")
        return 1

    dirs = sorted(p for p in SKILLS.iterdir() if p.is_dir())
    if args.names:
        wanted = set(args.names)
        dirs = [p for p in dirs if p.name in wanted]
        unknown = wanted - {p.name for p in dirs}
        if unknown:
            print(f"错误：仓库里没有这些技能：{', '.join(sorted(unknown))}")
            return 1
    if not dirs:
        print("错误：没有可处理的技能")
        return 1

    dest_root = Path(args.dest).expanduser().resolve()

    if args.uninstall:
        if not args.names:
            print("错误：--uninstall 需要指定技能名")
            return 1
        for name in args.names:
            dest = dest_root / name
            if not dest.is_dir():
                print(f"跳过：{name} 未安装")
                continue
            shutil.rmtree(dest)
            print(f"已卸载：{name}")
        return 0

    problems = [(p.name, validate(p)) for p in dirs]
    problems = [(name, errs) for name, errs in problems if errs]
    for name, errs in problems:
        for err in errs:
            print(f"校验失败：{err}")
    if problems:
        print("中止：校验失败的技能不会被安装。")
        return 1

    drift = False
    planned = 0
    for src in dirs:
        dest = dest_root / src.name
        if args.check:
            missing, changed, extra = (
                compare(src, dest)
                if dest.exists()
                else (list(relative_files(src)), [], [])
            )
            if not dest.exists():
                print(f"{src.name}: 未安装")
                drift = True
            elif missing or changed or extra:
                print(
                    f"{src.name}: 有差异（缺 {len(missing)} / 变 {len(changed)} / 多 {len(extra)}）"
                )
                for rel in (missing + changed)[:10]:
                    print(f"  - {rel.as_posix()}")
                for rel in extra[:10]:
                    print(f"  + {rel.as_posix()}（仅安装副本）")
                drift = True
            else:
                print(f"{src.name}: 一致")
            continue

        print(f"{'计划安装' if args.dry_run else '安装'}：{src.name} -> {dest}")
        planned += 1
        if not args.dry_run:
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, dest, dirs_exist_ok=True)

    if args.check:
        return 1 if drift else 0
    if args.dry_run:
        print(f"计划：{planned} 个技能 -> {dest_root}（未写盘）")
    else:
        print(f"完成：{planned} 个技能 -> {dest_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
