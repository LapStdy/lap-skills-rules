#!/usr/bin/env python3
"""新旧实现差分取证：同一组输入分别跑 old/new，比较返回值与异常。

用法：
    python diff_harness.py --old old.py --new new.py --function find_duplicates
    python diff_harness.py --old old.py --new new.py --function f --inputs cases.json
    python diff_harness.py --old old.py --new new.py --function f \
        --sizes 10,50,100 --seed 0 --json out.json

输入集 --inputs 支持两种 JSON 形状：
    {"cases": [{"args": [1, 2], "kwargs": {"k": 3}}, ...]}
    [[1, 2], [3, 4], ...]

不给 --inputs 时用 random.Random(seed) 生成 int list 单参数语料，
长度取自 --sizes（逗号分隔）；**该自动语料只适用于单参数函数**。

比较口径：
    返回值：先试 ==；== 抛异常或结果不是 bool 时退回 repr 比较。
    异常：按「异常类型名 + 消息」比较；类型不同即差异，类型相同但消息不同也算差异。

输出：total / identical / mismatched / errored 计数；每个差异给 index、args、
old、new（--max-show 截断）。--json 另写机器可读结果。

退出码：0 全部一致；1 存在差异；2 参数、加载或取函数失败。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import random
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any

EXIT_OK = 0
EXIT_DIFF = 1
EXIT_USAGE = 2


@dataclass
class CallResult:
    """一次调用的结果：返回值或异常。"""

    kind: str
    raw: Any = None
    display: str = ""
    exc_type: str | None = None
    exc_message: str | None = None


@dataclass
class CaseResult:
    """一条输入的对拍结果。"""

    index: int
    args: list[Any]
    kwargs: dict[str, Any]
    old: CallResult
    new: CallResult
    same: bool
    comparison: str
    errored: bool


def configure_stdio() -> None:
    """尽量把标准输出/错误切成 UTF-8，避免 Windows 控制台编码炸裂。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


def safe_repr(value: Any) -> str:
    """repr 不炸：极端对象也可能让 repr 抛异常。"""
    try:
        return repr(value)
    except Exception as exc:
        return "<repr 失败: " + type(exc).__name__ + ">"


def safe_str(value: Any) -> str:
    """str 不炸：异常对象的消息也可能再次抛异常。"""
    try:
        return str(value)
    except Exception as exc:
        return "<str 失败: " + type(exc).__name__ + ">"


def truncate(text: str, limit: int) -> str:
    """按字符数截断，并标注原始长度。"""
    if len(text) <= limit:
        return text
    marker = "...(共 " + str(len(text)) + " 字符)"
    if limit <= len(marker):
        return text[:limit]
    return text[: limit - len(marker)] + marker


def values_equal(left: Any, right: Any) -> tuple[bool, str]:
    """先 ==，失败或结果不是 bool（不可比较）时退回 repr 比较。"""
    try:
        outcome = left == right
    except Exception:
        return safe_repr(left) == safe_repr(right), "repr"
    if isinstance(outcome, bool):
        return outcome, "=="
    return safe_repr(left) == safe_repr(right), "repr"


def invoke(
    func: Callable[..., Any], call_args: list[Any], call_kwargs: dict[str, Any]
) -> CallResult:
    """调用一次，把返回值或异常都收敛成 CallResult。"""
    try:
        outcome = func(*call_args, **call_kwargs)
    except Exception as exc:
        return CallResult(kind="raise", exc_type=type(exc).__name__, exc_message=safe_str(exc))
    return CallResult(kind="return", raw=outcome, display=safe_repr(outcome))


def compare_results(old: CallResult, new: CallResult) -> tuple[bool, str]:
    """比较两侧结果，返回 (是否一致, 比较口径说明)。"""
    if old.kind != new.kind:
        return False, "一侧返回、一侧异常"
    if old.kind == "raise":
        if old.exc_type != new.exc_type:
            return False, "异常类型不同"
        if old.exc_message != new.exc_message:
            return False, "异常消息不同"
        return True, "异常一致"
    equal, method = values_equal(old.raw, new.raw)
    if equal:
        return True, "返回值一致（" + method + "）"
    return False, "返回值不同（" + method + " 判定）"


def load_module(path: Path, tag: str) -> ModuleType:
    """按文件路径加载模块；加载期间临时把同级目录放进 sys.path。"""
    module_name = "diff_harness_" + tag + "_" + path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError("无法为 " + str(path) + " 创建模块加载器")
    module = importlib.util.module_from_spec(spec)
    parent = str(path.parent)
    added = parent not in sys.path
    if added:
        sys.path.insert(0, parent)
    try:
        spec.loader.exec_module(module)
    finally:
        if added:
            try:
                sys.path.remove(parent)
            except ValueError:
                pass
    return module


def get_function(module: ModuleType, name: str) -> Callable[..., Any]:
    """取同名函数；不存在或不可调用时给出清晰错误。"""
    candidate = getattr(module, name, None)
    if not callable(candidate):
        raise AttributeError("模块中没有可调用对象：" + name)
    return candidate


def parse_sizes(raw: str) -> list[int]:
    """解析 --sizes：逗号分隔的正整数。"""
    sizes: list[int] = []
    for chunk in raw.split(","):
        text = chunk.strip()
        if not text:
            continue
        try:
            size = int(text)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("非法规模：" + repr(text)) from exc
        if size <= 0:
            raise argparse.ArgumentTypeError("规模必须为正整数：" + str(size))
        sizes.append(size)
    if not sizes:
        raise argparse.ArgumentTypeError("至少需要一个规模，如 --sizes 10,50,100")
    return sizes


def generate_cases(sizes: list[int], seed: int) -> list[dict[str, Any]]:
    """用固定 seed 生成 int list 单参数语料（含重复值）。"""
    rng = random.Random(seed)
    cases: list[dict[str, Any]] = []
    for size in sizes:
        upper = max(1, size // 2)
        items = [rng.randint(0, upper) for _ in range(size)]
        cases.append({"args": [items], "kwargs": {}})
    return cases


def parse_cases(raw: Any) -> list[dict[str, Any]]:
    """把 JSON 输入集规范成 [{"args": [...], "kwargs": {...}}, ...]。"""
    if isinstance(raw, dict):
        if "cases" not in raw:
            raise ValueError('顶层对象必须含 "cases" 数组')
        items = raw["cases"]
    elif isinstance(raw, list):
        items = raw
    else:
        raise ValueError("顶层必须是对象或数组")
    if not isinstance(items, list):
        raise ValueError('"cases" 必须是数组')
    cases: list[dict[str, Any]] = []
    for position, item in enumerate(items, start=1):
        if isinstance(item, dict):
            call_args = item.get("args", [])
            call_kwargs = item.get("kwargs", {})
        elif isinstance(item, list):
            call_args, call_kwargs = item, {}
        else:
            raise ValueError("第 " + str(position) + " 个 case 必须是数组或对象")
        if not isinstance(call_args, list):
            raise ValueError("第 " + str(position) + " 个 case 的 args 必须是数组")
        if not isinstance(call_kwargs, dict):
            raise ValueError("第 " + str(position) + " 个 case 的 kwargs 必须是对象")
        cases.append({"args": call_args, "kwargs": call_kwargs})
    return cases


def call_to_payload(result: CallResult, max_show: int) -> dict[str, Any]:
    """单侧结果的 JSON 视图。"""
    if result.kind == "raise":
        return {
            "kind": "raise",
            "exception": result.exc_type,
            "message": truncate(result.exc_message or "", max_show),
        }
    return {"kind": "return", "value": truncate(result.display, max_show)}


def case_to_payload(case: CaseResult, max_show: int) -> dict[str, Any]:
    """单条 case 的 JSON 视图。"""
    return {
        "index": case.index,
        "args": truncate(safe_repr(case.args), max_show),
        "kwargs": truncate(safe_repr(case.kwargs), max_show),
        "old": call_to_payload(case.old, max_show),
        "new": call_to_payload(case.new, max_show),
        "same": case.same,
        "comparison": case.comparison,
        "errored": case.errored,
    }


def describe_result(result: CallResult, max_show: int) -> str:
    """给人看的一侧结果描述。"""
    if result.kind == "raise":
        message = truncate(result.exc_message or "", max_show)
        return "异常 " + (result.exc_type or "?") + ": " + message
    return "返回 " + truncate(result.display, max_show)


def build_parser() -> argparse.ArgumentParser:
    """命令行定义；--help 里保留完整的输入格式与退出码说明。"""
    parser = argparse.ArgumentParser(
        prog="diff_harness.py",
        description="新旧实现差分：同输入对拍返回值与异常，找行为差异。",
        epilog=(
            "输入集 --inputs 的两种 JSON 形状：\n"
            '  {"cases": [{"args": [1, 2], "kwargs": {}}, ...]}\n'
            "  [[1, 2], [3, 4], ...]\n"
            "省略 --inputs 时按 --sizes 生成 int list 单参数语料（只适用单参函数）。\n\n"
            "退出码：0 全部一致 / 1 存在差异 / 2 参数、加载或取函数失败。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--old",
        type=Path,
        required=True,
        metavar="OLD.PY",
        help="旧实现 .py 文件路径",
    )
    parser.add_argument(
        "--new",
        type=Path,
        required=True,
        metavar="NEW.PY",
        help="新实现 .py 文件路径",
    )
    parser.add_argument("--function", required=True, help="两边都要调用的同名函数名")
    parser.add_argument(
        "--inputs",
        type=Path,
        metavar="CASES.JSON",
        help="输入集 JSON；不给则用 --sizes 自动生成",
    )
    parser.add_argument(
        "--sizes",
        type=parse_sizes,
        default=parse_sizes("10,50,100"),
        help="自动生成语料的 list 长度，逗号分隔（默认 10,50,100）",
    )
    parser.add_argument("--seed", type=int, default=0, help="自动生成语料的随机种子（默认 0）")
    parser.add_argument(
        "--json",
        type=Path,
        metavar="OUT.JSON",
        help="把机器可读结果写到该路径",
    )
    parser.add_argument(
        "--max-show",
        type=int,
        default=200,
        help="args / 返回值在输出中的最大字符数（默认 200）",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """命令行入口，返回进程退出码。"""
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.max_show <= 0:
        parser.error("--max-show 必须是正整数")

    old_path = args.old.expanduser().resolve()
    new_path = args.new.expanduser().resolve()
    for option, path in (("--old", old_path), ("--new", new_path)):
        if not path.is_file():
            print("文件不存在（" + option + "）：" + str(path), file=sys.stderr)
            return EXIT_USAGE

    try:
        old_func = get_function(load_module(old_path, "old"), args.function)
        new_func = get_function(load_module(new_path, "new"), args.function)
    except Exception as exc:
        print("加载失败：" + type(exc).__name__ + ": " + safe_str(exc), file=sys.stderr)
        return EXIT_USAGE

    if args.inputs is not None:
        input_path = args.inputs.expanduser().resolve()
        if not input_path.is_file():
            print("输入集不存在：" + str(input_path), file=sys.stderr)
            return EXIT_USAGE
        try:
            raw_cases = json.loads(input_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            print("输入集读取失败：" + safe_str(exc), file=sys.stderr)
            return EXIT_USAGE
        try:
            cases = parse_cases(raw_cases)
        except ValueError as exc:
            print("输入集格式错误：" + safe_str(exc), file=sys.stderr)
            return EXIT_USAGE
        corpus_description = "输入集 " + str(input_path)
        sizes: list[int] | None = None
    else:
        sizes = args.sizes
        cases = generate_cases(sizes, args.seed)
        corpus_description = (
            "自动生成 seed=" + str(args.seed) + " sizes=" + ",".join(str(size) for size in sizes)
        )

    results: list[CaseResult] = []
    for index, case in enumerate(cases, start=1):
        call_args = case["args"]
        call_kwargs = case["kwargs"]
        old_result = invoke(old_func, call_args, call_kwargs)
        new_result = invoke(new_func, call_args, call_kwargs)
        same, comparison = compare_results(old_result, new_result)
        results.append(
            CaseResult(
                index=index,
                args=call_args,
                kwargs=call_kwargs,
                old=old_result,
                new=new_result,
                same=same,
                comparison=comparison,
                errored=old_result.kind == "raise" or new_result.kind == "raise",
            )
        )

    total = len(results)
    mismatched = [result for result in results if not result.same]
    errored = sum(1 for result in results if result.errored)
    identical = total - len(mismatched)

    print(
        "差分取证 · "
        + str(old_path)
        + "::"
        + args.function
        + "  vs  "
        + str(new_path)
        + "::"
        + args.function
    )
    print("语料：" + str(total) + " 条（" + corpus_description + "）")
    print(
        f"total={total} identical={identical} mismatched={len(mismatched)} errored={errored}"
    )
    for result in mismatched:
        print("")
        print("[" + f"{result.index:02d}" + "] 差异：" + result.comparison)
        print("  args: " + truncate(safe_repr(result.args), args.max_show))
        if result.kwargs:
            print("  kwargs: " + truncate(safe_repr(result.kwargs), args.max_show))
        print("  old : " + describe_result(result.old, args.max_show))
        print("  new : " + describe_result(result.new, args.max_show))
    consistent_errors = [result.index for result in results if result.errored and result.same]
    if consistent_errors:
        print(
            "两侧同异常（视为一致）：index "
            + ", ".join(str(index) for index in consistent_errors)
        )

    if args.json is not None:
        json_path = args.json.expanduser()
        payload = {
            "old": str(old_path),
            "new": str(new_path),
            "function": args.function,
            "corpus": corpus_description,
            "seed": args.seed if sizes is not None else None,
            "sizes": sizes,
            "summary": {
                "total": total,
                "identical": identical,
                "mismatched": len(mismatched),
                "errored": errored,
            },
            "cases": [case_to_payload(result, args.max_show) for result in results],
        }
        try:
            if json_path.parent and not json_path.parent.exists():
                json_path.parent.mkdir(parents=True, exist_ok=True)
            json_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        except OSError as exc:
            print("写 JSON 失败：" + safe_str(exc), file=sys.stderr)
            return EXIT_USAGE
        print("JSON 已写入：" + str(json_path))

    return EXIT_DIFF if mismatched else EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
