#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资产仓自洽检查：README 索引、技能 frontmatter、评测目录、版本一致。

只查「文档说有的东西是否真的有、说的是否与文件一致」，不查内容质量。
内容质量由 check_artifacts 与人工评审负责。

用法：
    python tools/check_repo.py [--selftest] [--check-tools]

退出码：
    0  自洽
    1  有漂移
    2  参数或环境错误
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

REPO = Path(__file__).resolve().parent.parent
PATH_PREFIXES = ("rules/", "tools/", "templates/", "skills/", "evals/", "docs/", "scripts/")
VERSION_RE = re.compile(r"\bv(\d+\.\d+\.\d+)\b")
BACKTICK_RE = re.compile(r"`([^`\s]+)`")
DESCRIPTION_LIMIT = 500


@dataclass(frozen=True)
class Drift:
    """一处不自洽。"""

    where: str
    problem: str
    fix: str


def read_frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    values: dict[str, str] = {}
    for raw in parts[1].splitlines():
        line = raw.strip()
        if ":" in line and not line.startswith("-"):
            key, _, value = line.partition(":")
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def read_version(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        match = VERSION_RE.search(line)
        if match:
            return match.group(1)
    return None


def check_paths(root: Path, readme: str) -> list[Drift]:
    drifts: list[Drift] = []
    seen: set[str] = set()
    for token in BACKTICK_RE.findall(readme):
        candidate = token.rstrip("/")
        if candidate in seen or not candidate.startswith(PATH_PREFIXES):
            continue
        seen.add(candidate)
        if "*" in candidate or "::" in candidate or "<" in candidate:
            continue
        if not (root / candidate).exists():
            drifts.append(
                Drift(candidate, "README 引用的路径不存在", "补齐文件，或从 README 删掉这条索引")
            )
    return drifts


def check_skills(root: Path, readme: str) -> list[Drift]:
    drifts: list[Drift] = []
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return [Drift("skills/", "缺少技能目录", "建立 skills/<name>/SKILL.md")]
    for skill_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        name = skill_dir.name
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.is_file():
            drifts.append(Drift(f"skills/{name}", "缺少 SKILL.md", "补 SKILL.md 或删掉该目录"))
            continue
        meta = read_frontmatter(skill_file)
        if meta.get("name") != name:
            drifts.append(
                Drift(f"skills/{name}/SKILL.md", f"frontmatter name 为 {meta.get('name')!r}，与目录名不一致",
                      "把 name 改成目录名")
            )
        description = meta.get("description", "")
        if not description:
            drifts.append(Drift(f"skills/{name}/SKILL.md", "description 为空", "补触发词与用途，≤500 字符"))
        elif len(description) > DESCRIPTION_LIMIT:
            drifts.append(
                Drift(f"skills/{name}/SKILL.md", f"description {len(description)} 字符，超过 {DESCRIPTION_LIMIT}",
                      "压到 500 字符内，保留触发词")
            )
        if not meta.get("version"):
            drifts.append(Drift(f"skills/{name}/SKILL.md", "缺 metadata.version", "补 metadata.version"))
        if f"skills/{name}" not in readme and f"`{name}`" not in readme:
            drifts.append(
                Drift(f"skills/{name}", "README 没有该技能的索引", "在技能表里加一行")
            )
    return drifts


def check_evals(root: Path) -> list[Drift]:
    drifts: list[Drift] = []
    evals_dir = root / "evals"
    if not evals_dir.is_dir():
        return drifts
    for eval_dir in sorted(p for p in evals_dir.iterdir() if p.is_dir()):
        if not (root / "skills" / eval_dir.name).is_dir():
            drifts.append(
                Drift(f"evals/{eval_dir.name}", "没有同名技能", "改名为对应技能，或删掉该评测目录")
            )
    return drifts


def check_versions(root: Path) -> list[Drift]:
    drifts: list[Drift] = []
    readme_path = root / "README.md"
    changelog = root / "CHANGELOG.md"
    if not readme_path.is_file() or not changelog.is_file():
        return drifts
    readme_version = read_version(readme_path)
    changelog_version = read_version(changelog)
    if readme_version and changelog_version and readme_version != changelog_version:
        drifts.append(
            Drift("README.md", f"版本 {readme_version} 与 CHANGELOG 头 {changelog_version} 不一致",
                  "README 只写「版本见 CHANGELOG」，或同步成同一个版本")
        )
    return drifts


def check_tools(root: Path) -> list[Drift]:
    drifts: list[Drift] = []
    commands = [
        (["python", "tools/check_artifacts.py", "."], "交付物检查"),
        (["python", "tools/check_structure.py", ".", "--allow", "structure-allow.txt"], "结构检查"),
        (["python", "tools/install_skills.py", "--check"], "技能安装比对"),
    ]
    for argv, label in commands:
        completed = subprocess.run(
            argv,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stdout or completed.stderr).strip().splitlines()
            tail = detail[-1] if detail else f"退出码 {completed.returncode}"
            drifts.append(Drift(label, f"未通过：{tail}", "按该命令输出里的改法处理"))
    return drifts


def run_checks(root: Path, *, with_tools: bool = False) -> list[Drift]:
    readme_path = root / "README.md"
    if not readme_path.is_file():
        return [Drift("README.md", "缺少仓库入口", "写 README：一页看懂规矩、技能与工具")]
    readme = readme_path.read_text(encoding="utf-8", errors="replace")
    drifts: list[Drift] = []
    drifts.extend(check_paths(root, readme))
    drifts.extend(check_skills(root, readme))
    drifts.extend(check_evals(root))
    drifts.extend(check_versions(root))
    if with_tools:
        drifts.extend(check_tools(root))
    return drifts


def selftest() -> int:
    with tempfile.TemporaryDirectory() as raw:
        root = Path(raw)
        (root / "skills" / "good").mkdir(parents=True)
        (root / "skills" / "good" / "SKILL.md").write_text(
            "---\nname: wrong\n---\n正文\n", encoding="utf-8"
        )
        (root / "skills" / "nofile").mkdir()
        (root / "evals" / "orphan").mkdir(parents=True)
        (root / "README.md").write_text(
            "当前 v0.0.1\n见 `rules/missing.md` 与 `skills/good`。\n", encoding="utf-8"
        )
        (root / "CHANGELOG.md").write_text("# 变更记录\n\n## v9.9.9\n", encoding="utf-8")
        drifts = run_checks(root)
        kinds = {
            "README 引用的路径不存在": any(d.problem.startswith("README 引用") for d in drifts),
            "name 不一致": any("frontmatter name" in d.problem for d in drifts),
            "缺 description": any("description" in d.problem for d in drifts),
            "缺 version": any("metadata.version" in d.problem for d in drifts),
            "缺 SKILL.md": any("缺少 SKILL.md" in d.problem for d in drifts),
            "孤立评测": any("没有同名技能" in d.problem for d in drifts),
            "版本不一致": any("CHANGELOG" in d.problem for d in drifts),
        }
        missed = [name for name, hit in kinds.items() if not hit]
        if missed:
            print(f"自检 FAIL  漏检：{missed}")
            return 1
    print("自检结果：全部通过（路径、frontmatter、评测、版本四类漂移都能检出）")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="资产仓自洽检查")
    parser.add_argument("--selftest", action="store_true", help="内置样例自检")
    parser.add_argument("--check-tools", action="store_true", help="同时跑三个工具检查")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    drifts = run_checks(REPO, with_tools=args.check_tools)
    if not drifts:
        print(f"仓库自洽：PASS（扫描 {len(list((REPO / 'skills').glob('*/SKILL.md')))} 个技能）")
        return 0
    print(f"仓库自洽：FAIL（{len(drifts)} 处漂移）")
    for drift in drifts:
        print(f"  {drift.where}：{drift.problem}")
        print(f"    改法：{drift.fix}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
