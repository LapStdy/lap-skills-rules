#!/usr/bin/env python3
"""零依赖边界 smoke：对目标函数跑一组边界/非法输入，分类返回、异常与崩溃。

用法：
    python probe_inputs.py --module path/to/mod.py --function parse_duration
    python probe_inputs.py --module m.py --function f --corpus corpus.json
    python probe_inputs.py --module m.py --function f --expect ValueError,TypeError
    python probe_inputs.py --module m.py --function f --minimize --json

输入集 JSON：顶层是数组。元素是标量 -> 单个位置参数；元素是 {"args": [...]} -> 多个位置参数。
缺省用内置边界语料（空/空白/符号/数值/大小写/超长/Unicode/None/容器）。

定位：边界 smoke + 异常分类 + 简单最小化；**不是**覆盖率引导 fuzz，**不隔离**进程。
限制：进程内运行、无超时；不要在不可信或原生代码上跑；卡死需由外部 timeout 处理。
退出码：0 完成（即使发现失败）；2 参数/加载错误。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

DEFAULT_CORPUS: list[Any] = [
    "",
    " ",
    chr(9),
    "0",
    "-1",
    "+1",
    "1.5",
    "1e3",
    "ms",
    "MS",
    "1ms",
    "1MS",
    "1 s",
    "-1ms",
    "1h30m",
    "1.2.3",
    "0001",
    "9" * 64,
    "ü",
    "٣",
    "１２３",
    "1" + chr(0),
    None,
    0,
    -1,
    1,
    True,
    False,
    [],
    {},
    b"",
    b"1ms",
]


@dataclass
class Outcome:
    """一次调用的结果。"""

    index: int
    args: str
    status: str
    detail: str
    exc_type: str | None = None
    minimized: str | None = None


def load_module(path: Path) -> ModuleType:
    """按文件路径加载模块。"""
    module_name = "probe_inputs_" + path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError("无法加载模块：" + str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        sys.modules.pop(module_name, None)
    return module


def call(func: Callable[..., Any], args: list[Any]) -> tuple[str, str, str | None]:
    """调用一次，返回 (status, detail, exc_type)；status 为 ok/raised/crash。"""
    try:
        result = func(*args)
    except KeyboardInterrupt:
        raise
    except BaseException as exc:
        status = "raised" if isinstance(exc, Exception) else "crash"
        exc_type = type(exc).__name__
        return status, exc_type + ": " + str(exc), exc_type
    return "ok", repr(result)[:160], None


def signature(func: Callable[..., Any], args: list[Any]) -> str:
    """失败签名：ok 或 状态:异常类型（最小化时要求签名不变）。"""
    status, _detail, exc_type = call(func, args)
    if status == "ok":
        return "ok"
    return status + ":" + (exc_type or "unknown")


def minimize(func: Callable[..., Any], args: list[Any], max_calls: int = 200) -> list[Any] | None:
    """对单参数的 str/bytes/list/tuple 做块删除最小化；签名不变才算更小。"""
    if len(args) != 1 or not isinstance(args[0], (str, bytes, list, tuple)):
        return None
    target = signature(func, args)
    if target == "ok":
        return None
    value: Any = args[0]
    calls = 0
    size = max(1, len(value) // 2)
    while size >= 1 and calls < max_calls:
        index = 0
        changed = False
        while index < len(value) and calls < max_calls:
            candidate = value[:index] + value[index + size :]
            calls += 1
            if signature(func, [candidate]) == target:
                value = candidate
                changed = True
            else:
                index += size
        if not changed:
            if size == 1:
                break
            size = max(1, size // 2)
    if value == args[0]:
        return None
    return [value]


def parse_corpus(raw: Any) -> list[list[Any]]:
    """把 JSON 输入集转成参数列表；标量=单参数，对象=多参数。"""
    if not isinstance(raw, list):
        raise ValueError("corpus 顶层必须是数组")
    corpus: list[list[Any]] = []
    for item in raw:
        if isinstance(item, dict):
            call_args = item.get("args")
            if not isinstance(call_args, list):
                raise ValueError("对象元素必须含 args 数组")
            corpus.append(call_args)
        else:
            corpus.append([item])
    return corpus


def main(argv: list[str] | None = None) -> int:
    """命令行入口。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass

    parser = argparse.ArgumentParser(description="零依赖边界 smoke：跑输入集并分类返回/异常/崩溃")
    parser.add_argument("--module", type=Path, required=True, help="目标模块 .py 路径")
    parser.add_argument("--function", required=True, help="目标函数名")
    parser.add_argument("--corpus", type=Path, help="输入集 JSON（缺省用内置边界语料）")
    parser.add_argument(
        "--expect", default="", help="视为预期异常的异常名，逗号分隔，如 ValueError,TypeError"
    )
    parser.add_argument("--minimize", action="store_true", help="对失败输入做简单最小化")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args(argv)

    module_path = args.module.resolve()
    if not module_path.is_file():
        print("模块不存在：" + str(module_path), file=sys.stderr)
        return 2
    try:
        module = load_module(module_path)
    except Exception as exc:
        print("加载失败：" + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        return 2
    func = getattr(module, args.function, None)
    if not callable(func):
        print("函数不存在或不可调用：" + args.function, file=sys.stderr)
        return 2

    if args.corpus:
        try:
            corpus = parse_corpus(json.loads(args.corpus.read_text(encoding="utf-8")))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            print("输入集读取失败：" + str(exc), file=sys.stderr)
            return 2
    else:
        corpus = [[item] for item in DEFAULT_CORPUS]

    expected = {name.strip() for name in args.expect.split(",") if name.strip()}
    outcomes: list[Outcome] = []
    for index, call_args in enumerate(corpus, start=1):
        status, detail, exc_type = call(func, call_args)
        minimized: str | None = None
        if args.minimize and status != "ok":
            shrunk = minimize(func, call_args)
            if shrunk is not None:
                minimized = repr(shrunk[0])
        outcomes.append(
            Outcome(
                index=index,
                args=repr(call_args),
                status=status,
                detail=detail,
                exc_type=exc_type,
                minimized=minimized,
            )
        )

    unexpected = [
        outcome
        for outcome in outcomes
        if outcome.status == "crash"
        or (outcome.status == "raised" and outcome.exc_type not in expected)
    ]
    summary = {
        "inputs": len(outcomes),
        "ok": sum(1 for outcome in outcomes if outcome.status == "ok"),
        "raised": sum(1 for outcome in outcomes if outcome.status == "raised"),
        "crash": sum(1 for outcome in outcomes if outcome.status == "crash"),
        "unexpected": len(unexpected),
    }

    if args.json:
        payload = {
            "module": str(module_path),
            "function": args.function,
            "corpus": str(args.corpus) if args.corpus else "builtin",
            "expect": sorted(expected),
            "outcomes": [asdict(outcome) for outcome in outcomes],
            "summary": summary,
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    print("边界 smoke · " + str(module_path) + "::" + args.function)
    print(
        "输入 "
        + str(summary["inputs"])
        + " 条（"
        + ("内置边界语料" if not args.corpus else "自定义输入集")
        + "）；预期异常："
        + (",".join(sorted(expected)) if expected else "未声明")
    )
    for outcome in outcomes:
        marker = ""
        if outcome.status == "crash":
            marker = "  <-- 崩溃级"
        elif outcome.status == "raised" and outcome.exc_type not in expected:
            marker = "  <-- 未预期异常"
        print(
            "["
            + f"{outcome.index:02d}"
            + "] "
            + outcome.status.ljust(6)
            + " "
            + outcome.args
            + " -> "
            + outcome.detail
            + marker
        )
        if outcome.minimized is not None:
            print("      最小化：" + outcome.minimized)
    print(
        "汇总：ok={ok} raised={raised} crash={crash} unexpected={unexpected}".format(**summary)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
