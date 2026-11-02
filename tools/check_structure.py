#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""结构上限检查器：函数行数、参数个数、类行数、模块行数。

判据来自项目代码规约的规模上限：函数 50 行、参数 4 个、类 300 行、模块 500 行。
超限要么拆，要么按欠账入允许清单并写归还期限；允许清单只缩不涨。

用法：
    python tools/check_structure.py [路径 ...] [--allow FILE] [--selftest]
    python tools/check_structure.py . --allow structure-allow.txt

允许清单格式（一行一条，# 开头为注释）：
    path/to/module.py                 整个模块超限
    path/to/module.py::function_name
    path/to/module.py::ClassName
    path/to/module.py::ClassName.method

退出码：
    0  无未入清单的超限
    1  有超限
    2  参数或环境错误
"""

from __future__ import annotations

import argparse
import ast
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

MAX_FUNCTION_LINES = 50
MAX_PARAMS = 4
MAX_CLASS_LINES = 300
MAX_MODULE_LINES = 500

SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "build",
    "dist",
    "out",
    "node_modules",
    "archive",
    ".tmp",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".import_linter_cache",
    "site-packages",
}


@dataclass(frozen=True)
class Limits:
    """四类上限；调用方按项目规模覆盖。"""

    function_lines: int = MAX_FUNCTION_LINES
    params: int = MAX_PARAMS
    class_lines: int = MAX_CLASS_LINES
    module_lines: int = MAX_MODULE_LINES


@dataclass(frozen=True)
class Finding:
    """一处超限；key 用于与允许清单比对。"""

    path: str
    line: int
    key: str
    kind: str
    name: str
    actual: int
    limit: int
    fix: str


def span_lines(node: ast.AST) -> int:
    start = getattr(node, "lineno", 1)
    end = getattr(node, "end_lineno", start)
    decorators = getattr(node, "decorator_list", [])
    for deco in decorators:
        start = min(start, getattr(deco, "lineno", start))
    return end - start + 1


def param_count(node: ast.FunctionDef | ast.AsyncFunctionDef, *, method: bool) -> int:
    args = node.args
    names = [*args.posonlyargs, *args.args]
    if method and names:
        names = names[1:]
    total = len(names) + len(args.kwonlyargs)
    if args.vararg is not None:
        total += 1
    if args.kwarg is not None:
        total += 1
    return total


@dataclass(frozen=True)
class DefSite:
    """一处定义的位置信息：限定名、节点、种类、是否类方法。"""

    name: str
    node: ast.AST
    kind: str
    in_class: bool


def walk_defs(body: list[ast.stmt], prefix: str = "", *, in_class: bool = False):
    """逐个产出 DefSite；嵌套定义也跟进去。"""
    for node in body:
        if isinstance(node, ast.ClassDef):
            yield DefSite(prefix + node.name, node, "class", in_class)
            yield from walk_defs(node.body, prefix + node.name + ".", in_class=True)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield DefSite(prefix + node.name, node, "function", in_class)
            yield from walk_defs(node.body, prefix + node.name + ".", in_class=False)
        else:
            inner = getattr(node, "body", None)
            if isinstance(inner, list):
                yield from walk_defs(inner, prefix, in_class=in_class)


def measure(site: DefSite, rel: str, limits: Limits) -> list[Finding]:
    findings: list[Finding] = []
    line = getattr(site.node, "lineno", 1)
    actual = span_lines(site.node)
    if site.kind == "class":
        if actual > limits.class_lines:
            findings.append(
                Finding(rel, line, site.name, "class", site.name, actual, limits.class_lines,
                        "拆类：按职责拆成协作对象，或把一部分搬进同目录子模块")
            )
        return findings
    if actual > limits.function_lines:
        findings.append(
            Finding(rel, line, site.name, "function", site.name, actual, limits.function_lines,
                    "拆函数：按阶段拆开，每段独立命名并写清完成判据")
        )
    params = param_count(site.node, method=site.in_class)
    if params > limits.params:
        findings.append(
            Finding(rel, line, site.name, "params", site.name, params, limits.params,
                    "用 dataclass 收敛参数，或把成组参数拆成独立协作对象")
        )
    return findings


def scan_file(path: Path, root: Path, limits: Limits) -> list[Finding]:
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    findings: list[Finding] = []
    module_lines = len(text.splitlines())
    if module_lines > limits.module_lines:
        findings.append(
            Finding(rel, 1, rel, "module", rel, module_lines, limits.module_lines,
                    "拆模块：按主题拆开，对外导出保持不变")
        )
    try:
        tree = ast.parse(text, filename=rel)
    except SyntaxError as error:
        findings.append(
            Finding(rel, error.lineno or 1, rel, "syntax", rel, 0, 0,
                    f"先修语法错误：{error.msg}")
        )
        return findings
    for site in walk_defs(tree.body):
        findings.extend(measure(site, rel, limits))
    return findings


def iter_python_files(root: Path):
    for path in sorted(root.rglob("*.py")):
        parts = set(path.parts)
        if parts & SKIP_DIRS:
            continue
        yield path


def load_allow(path: Path | None) -> set[str]:
    if path is None or not path.is_file():
        return set()
    allowed: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            allowed.add(line.replace("\\", "/"))
    return allowed


def blocked(findings: list[Finding], allow: set[str]) -> list[Finding]:
    out: list[Finding] = []
    for item in findings:
        keys = {f"{item.path}::{item.key}", item.path}
        if keys & allow:
            continue
        out.append(item)
    return out


def run(roots: list[Path], limits: Limits, allow: set[str]) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    scanned = 0
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            scanned += 1
            findings.extend(scan_file(root, root.parent, limits))
            continue
        for path in iter_python_files(root):
            scanned += 1
            findings.extend(scan_file(path, root, limits))
    return blocked(findings, allow), scanned


def report(items: list[Finding], scanned: int, allow: set[str]) -> int:
    if not items:
        print(f"结构检查：PASS（扫描 {scanned} 个文件，允许清单 {len(allow)} 项，无未入清单的超限）")
        return 0
    print(f"结构检查：FAIL（扫描 {scanned} 个文件，{len(items)} 处超限）")
    for item in items:
        print(f"  {item.path}:{item.line}  [{item.kind}] {item.name} 实际 {item.actual} 上限 {item.limit}")
        print(f"    改法：{item.fix}")
        entry = item.path if item.kind == "module" else f"{item.path}::{item.key}"
        print(f"    既有欠账：写进 DEBT.md 并把 `{entry}` 加进允许清单，清单只缩不涨")
    return 1


SELFTEST_CLEAN = '''

def small(value: int) -> int:
    """原样返回。"""
    return value
'''


def selftest() -> int:
    limits = Limits()
    long_function = "def too_long() -> int:\n" + "".join(
        f"    x{i} = {i}\n" for i in range(55)
    ) + "    return x0\n"
    bad_source = (
        long_function
        + "\n\ndef too_many(a, b, c, d, e):\n    return a\n"
        + "\n\nclass Big:\n    def method(self, a, b, c, d, e, f):\n        return a\n"
    )
    with tempfile.TemporaryDirectory() as raw:
        tmp = Path(raw)
        clean = tmp / "clean.py"
        clean.write_text(SELFTEST_CLEAN, encoding="utf-8")
        if run([clean], limits, set())[0]:
            print("自检 FAIL  干净文件被报")
            return 1
        bad = tmp / "bad.py"
        bad.write_text(bad_source, encoding="utf-8")
        findings, _ = run([bad], limits, set())
        kinds = {item.kind for item in findings}
        if not {"function", "params"} <= kinds:
            print(f"自检 FAIL  期望 function 与 params，实际 {sorted(kinds)}")
            return 1
        allow_file = tmp / "allow.txt"
        allow_file.write_text(
            "\n".join(f"bad.py::{item.key}" for item in findings), encoding="utf-8"
        )
        if run([bad], limits, load_allow(allow_file))[0]:
            print("自检 FAIL  允许清单未生效")
            return 1
    print("自检结果：全部通过（干净文件、超限检出、允许清单放行）")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="检查 Python 结构上限：函数、参数、类、模块")
    parser.add_argument("paths", nargs="*", default=["."], help="要扫描的目录或 .py 文件")
    parser.add_argument("--allow", help="允许清单文件（既有欠账）")
    parser.add_argument("--function-lines", type=int, default=MAX_FUNCTION_LINES)
    parser.add_argument("--params", type=int, default=MAX_PARAMS)
    parser.add_argument("--class-lines", type=int, default=MAX_CLASS_LINES)
    parser.add_argument("--module-lines", type=int, default=MAX_MODULE_LINES)
    parser.add_argument("--selftest", action="store_true", help="内置样例自检")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest()
    limits = Limits(args.function_lines, args.params, args.class_lines, args.module_lines)
    roots = [Path(p) for p in args.paths]
    missing = [str(p) for p in roots if not p.exists()]
    if missing:
        print(f"路径不存在：{', '.join(missing)}", file=sys.stderr)
        return 2
    allow = load_allow(Path(args.allow) if args.allow else None)
    items, scanned = run(roots, limits, allow)
    return report(items, scanned, allow)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
