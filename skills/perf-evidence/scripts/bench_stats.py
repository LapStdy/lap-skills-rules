#!/usr/bin/env python3
"""零依赖性能采样与回归门禁：run / exec 采样，compare 用 median/IQR 判定回归。

用法：
    python bench_stats.py run --cmd "python target.py 400" --warmup 2 --repeat 10 \
        --label baseline --json-out before.json
    python bench_stats.py exec --target target.py:find_duplicates \
        --args-json '[[400]]' --label before --json-out before.json
    python bench_stats.py compare --baseline before.json --candidate after.json \
        --threshold 0.10

run 用 subprocess 跑整条命令（含解释器启动），exec 在进程内直接调用函数
（单次调用耗时）。两者都丢弃子进程输出，避免污染计时。

统计口径：n / min / median / mean / stdev / q1 / q3 / iqr / rel_iqr，
外加 Python 版本、platform、machine、cpu_count 与 UTC 时间。

compare 规则：delta = candidate.median / baseline.median - 1；
判定 regression 当且仅当 delta > threshold 且
(candidate.median - baseline.median) > baseline.iqr。
环境不一致（Python 或平台不同）与样本数 n < 5 会给出警告。

退出码：compare 为 0 未回归 / 1 回归 / 2 参数或文件错误；
run / exec 为 0 成功 / 2 参数、命令或目标错误。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import platform
import shlex
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

EXIT_OK = 0
EXIT_REGRESSION = 1
EXIT_USAGE = 2


def configure_stdio() -> None:
    """尽量把标准输出/错误切成 UTF-8，避免 Windows 控制台编码炸裂。"""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                pass


def fail(message: str) -> int:
    """打印错误并返回参数/环境错误码。"""
    print("错误：" + message, file=sys.stderr)
    return EXIT_USAGE


def split_command(command: str) -> list[str]:
    """解析 --cmd。

    不走 shell：避免 shell 启动开销污染计时，也不执行管道/重定向。
    Windows 下按非 POSIX 规则分词，并去掉整词外层的双引号（保留路径里的反斜杠）。
    """
    if os.name == "nt":
        tokens = shlex.split(command, posix=False)
        cleaned: list[str] = []
        for token in tokens:
            if len(token) >= 2 and token[0] == '"' and token[-1] == '"':
                token = token[1:-1]
            cleaned.append(token)
        return cleaned
    return shlex.split(command, posix=True)


def run_command(argv: list[str]) -> tuple[int, float]:
    """跑一次命令，返回 (退出码, 耗时秒)；stdout/stderr 直接丢弃。"""
    start = time.perf_counter()
    completed = subprocess.run(
        argv,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    elapsed = time.perf_counter() - start
    return completed.returncode, elapsed


def load_module(path: Path) -> ModuleType:
    """按文件路径加载模块；加载期间临时把同级目录放进 sys.path。"""
    module_name = "bench_stats_" + path.stem
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


def parse_target(raw: str) -> tuple[Path, str]:
    """解析 --target 的 path.py:function（Windows 盘符冒号在 func 之前，取最后一个冒号）。"""
    path_text, separator, function_name = raw.rpartition(":")
    if not separator or not path_text or not function_name:
        raise ValueError("--target 必须形如 path/to/file.py:function")
    return Path(path_text).expanduser(), function_name


def parse_exec_args(raw: str) -> list[dict[str, Any]]:
    """解析 --args-json：数组，元素是参数数组或 {"args": [...], "kwargs": {...}}。"""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("--args-json 不是合法 JSON：" + str(exc)) from exc
    if not isinstance(payload, list) or not payload:
        raise ValueError("--args-json 必须是至少含一个元素的数组")
    calls: list[dict[str, Any]] = []
    for position, entry in enumerate(payload, start=1):
        if isinstance(entry, dict):
            call_args = entry.get("args", [])
            call_kwargs = entry.get("kwargs", {})
        elif isinstance(entry, list):
            call_args, call_kwargs = entry, {}
        else:
            raise ValueError("第 " + str(position) + " 个调用必须是数组或对象")
        if not isinstance(call_args, list):
            raise ValueError("第 " + str(position) + " 个调用的 args 必须是数组")
        if not isinstance(call_kwargs, dict):
            raise ValueError("第 " + str(position) + " 个调用的 kwargs 必须是对象")
        calls.append({"args": call_args, "kwargs": call_kwargs})
    return calls


def timed_call(
    func: Callable[..., Any], call_args: list[Any], call_kwargs: dict[str, Any]
) -> float:
    """在进程内调用一次并返回耗时秒；异常向上抛给调用方。"""
    start = time.perf_counter()
    func(*call_args, **call_kwargs)
    return time.perf_counter() - start


def collect_env() -> dict[str, Any]:
    """记录可复现性需要的环境信息。"""
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count() or 0,
    }


def compute_stats(samples: list[float]) -> dict[str, float | int]:
    """计算 n / min / median / mean / stdev / q1 / q3 / iqr / rel_iqr。"""
    ordered = sorted(samples)
    count = len(ordered)
    median = statistics.median(ordered)
    if count >= 2:
        stdev = statistics.stdev(ordered)
        q1, _q2, q3 = statistics.quantiles(ordered, n=4, method="inclusive")
    else:
        stdev = 0.0
        q1 = median
        q3 = median
    iqr = q3 - q1
    rel_iqr = iqr / median if median else 0.0
    return {
        "n": count,
        "min": ordered[0],
        "median": median,
        "mean": statistics.fmean(ordered),
        "stdev": stdev,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "rel_iqr": rel_iqr,
    }


def build_payload(
    *,
    mode: str,
    label: str,
    samples: list[float],
    warmup: int,
    repeat: int,
    command: str | None = None,
    target: str | None = None,
    args_json: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """组装可被 compare 直接读取的结果 JSON。"""
    return {
        "schema": 1,
        "tool": "bench_stats",
        "mode": mode,
        "label": label,
        "created_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "warmup": warmup,
        "repeat": repeat,
        "command": command,
        "target": target,
        "args_json": args_json,
        "calls_per_round": len(args_json) if args_json is not None else None,
        "env": collect_env(),
        "stats": compute_stats(samples),
        "samples_s": samples,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """写 JSON；父目录不存在时自动创建。"""
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def print_sampling_summary(payload: dict[str, Any], json_out: Path | None) -> None:
    """打印 run / exec 的人读摘要。"""
    stats = payload["stats"]
    env = payload["env"]
    print("采样完成 · mode=" + str(payload["mode"]) + " · label=" + str(payload["label"]))
    if payload["command"]:
        print("命令：" + str(payload["command"]))
    if payload["target"]:
        print(
            "目标："
            + str(payload["target"])
            + " · 每轮调用 "
            + str(payload["calls_per_round"])
            + " 次"
        )
    print(
        "n={} median={:.6f}s IQR={:.6f}s min={:.6f}s mean={:.6f}s stdev={:.6f}s".format(
            stats["n"],
            stats["median"],
            stats["iqr"],
            stats["min"],
            stats["mean"],
            stats["stdev"],
        )
    )
    print("rel_iqr={:.2%}".format(stats["rel_iqr"]))
    print(
        "环境：Python "
        + str(env["python"])
        + " · "
        + str(env["platform"])
        + " · "
        + str(env["machine"])
        + " · cpu="
        + str(env["cpu_count"])
    )
    if json_out is not None:
        print("JSON 已写入：" + str(json_out))


def finish_sampling(payload: dict[str, Any], json_out: Path | None) -> int:
    """采样成功后统一收尾：写 JSON 并打印摘要。"""
    if json_out is not None:
        try:
            write_json(json_out, payload)
        except OSError as exc:
            return fail("写 JSON 失败：" + str(exc))
    print_sampling_summary(payload, json_out)
    return EXIT_OK


def handle_run(args: argparse.Namespace) -> int:
    """run 子命令：subprocess 重复跑命令计时。"""
    warmup: int = args.warmup
    repeat: int = args.repeat
    if warmup < 0:
        return fail("--warmup 不能为负数")
    if repeat < 1:
        return fail("--repeat 至少为 1")
    command: str = args.cmd
    if not command.strip():
        return fail("--cmd 不能为空")
    argv = split_command(command)
    if not argv:
        return fail("--cmd 解析后没有任何可执行部分")
    try:
        for _ in range(warmup):
            returncode, _elapsed = run_command(argv)
            if returncode != 0:
                return fail("预热命令返回 " + str(returncode) + "，计时无效：" + command)
        samples: list[float] = []
        for _ in range(repeat):
            returncode, elapsed = run_command(argv)
            if returncode != 0:
                return fail("命令返回 " + str(returncode) + "，计时无效：" + command)
            samples.append(elapsed)
    except FileNotFoundError:
        return fail("找不到命令：" + argv[0])
    except OSError as exc:
        return fail("启动命令失败：" + str(exc))
    payload = build_payload(
        mode="run",
        label=args.label,
        samples=samples,
        warmup=warmup,
        repeat=repeat,
        command=command,
    )
    return finish_sampling(payload, args.json_out)


def handle_exec(args: argparse.Namespace) -> int:
    """exec 子命令：进程内重复调用函数，单次调用耗时。"""
    warmup: int = args.warmup
    repeat: int = args.repeat
    if warmup < 0:
        return fail("--warmup 不能为负数")
    if repeat < 1:
        return fail("--repeat 至少为 1")
    try:
        module_path, function_name = parse_target(args.target)
    except ValueError as exc:
        return fail(str(exc))
    if not module_path.is_file():
        return fail("目标文件不存在：" + str(module_path))
    try:
        module = load_module(module_path)
    except Exception as exc:
        return fail("加载目标模块失败：" + type(exc).__name__ + ": " + str(exc))
    function = getattr(module, function_name, None)
    if not callable(function):
        return fail("目标函数不存在或不可调用：" + function_name)
    try:
        calls = parse_exec_args(args.args_json)
    except ValueError as exc:
        return fail(str(exc))
    samples: list[float] = []
    try:
        for _ in range(warmup):
            for call in calls:
                timed_call(function, call["args"], call["kwargs"])
        for _ in range(repeat):
            for call in calls:
                samples.append(timed_call(function, call["args"], call["kwargs"]))
    except Exception as exc:
        return fail("调用目标函数失败：" + type(exc).__name__ + ": " + str(exc))
    payload = build_payload(
        mode="exec",
        label=args.label,
        samples=samples,
        warmup=warmup,
        repeat=repeat,
        target=args.target,
        args_json=calls,
    )
    return finish_sampling(payload, args.json_out)


def env_of(payload: dict[str, Any]) -> dict[str, Any]:
    """取 JSON 里的 env 对象；缺失或类型不对时返回空对象。"""
    env = payload.get("env")
    return env if isinstance(env, dict) else {}


def load_stats(path: Path) -> dict[str, Any]:
    """读取并校验 bench_stats 结果 JSON。"""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError("读取 " + str(path) + " 失败：" + str(exc)) from exc
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(str(path) + " 不是合法 JSON：" + str(exc)) from exc
    if not isinstance(payload, dict):
        raise ValueError(str(path) + " 顶层不是 JSON 对象")
    stats = payload.get("stats")
    if not isinstance(stats, dict):
        raise ValueError(str(path) + " 缺少 stats 对象（不是 bench_stats.py 产物？）")
    for key in ("median", "iqr", "n"):
        value = stats.get(key)
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise ValueError(str(path) + " 的 stats." + key + " 缺失或不是数值")
    return payload


def compare_warnings(baseline: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    """收集「不可直接比」的警告：环境、模式、命令/目标、样本数。"""
    warnings: list[str] = []
    base_env = env_of(baseline)
    cand_env = env_of(candidate)
    if base_env.get("python") != cand_env.get("python"):
        warnings.append(
            "Python 版本不一致："
            + str(base_env.get("python"))
            + " -> "
            + str(cand_env.get("python"))
        )
    if base_env.get("platform") != cand_env.get("platform"):
        warnings.append(
            "平台不一致：" + str(base_env.get("platform")) + " -> " + str(cand_env.get("platform"))
        )
    if baseline.get("mode") != candidate.get("mode"):
        warnings.append(
            "测量模式不同：" + str(baseline.get("mode")) + " -> " + str(candidate.get("mode"))
        )
    base_command = baseline.get("command")
    cand_command = candidate.get("command")
    if base_command and cand_command and base_command != cand_command:
        warnings.append("两次 run 命令不同，比较可能无意义")
    base_target = baseline.get("target")
    cand_target = candidate.get("target")
    if base_target and cand_target and base_target != cand_target:
        warnings.append("两次 exec 目标不同，比较可能无意义")
    for name, payload in (("基线", baseline), ("候选", candidate)):
        stats = payload["stats"]
        n = stats["n"]
        if isinstance(n, int) and n < 5:
            warnings.append(name + "样本数 n=" + str(n) + " < 5，median/IQR 不稳定")
    return warnings


def print_compare_table(payload: dict[str, Any]) -> None:
    """打印人读的前后对比表与判定理由。"""
    base = payload["baseline_stats"]
    cand = payload["candidate_stats"]
    print(
        "性能对比 · "
        + str(payload["baseline_label"])
        + " -> "
        + str(payload["candidate_label"])
    )
    print("指标".ljust(10) + "基线".rjust(16) + "候选".rjust(16) + "变化".rjust(14))
    base_median = f"{base['median']:.6f}s"
    cand_median = f"{cand['median']:.6f}s"
    delta_text = f"{payload['delta']:+.2%}"
    print("median".ljust(10) + base_median.rjust(16) + cand_median.rjust(16) + delta_text.rjust(14))
    base_iqr = f"{base['iqr']:.6f}s"
    cand_iqr = f"{cand['iqr']:.6f}s"
    print("IQR".ljust(10) + base_iqr.rjust(16) + cand_iqr.rjust(16) + "-".rjust(14))
    base_n = str(base["n"])
    cand_n = str(cand["n"])
    print("n".ljust(10) + base_n.rjust(16) + cand_n.rjust(16) + "-".rjust(14))
    print("-" * 56)
    print("判定规则：" + str(payload["rule"]))
    print(
        "delta={:+.2%} 阈值={:.2%} 绝对增量={:+.6f}s 基线 IQR={:.6f}s".format(
            payload["delta"],
            payload["threshold"],
            payload["abs_delta_s"],
            payload["base_iqr_s"],
        )
    )
    threshold_text = "超出" if payload["exceeds_threshold"] else "未超出"
    iqr_text = "超出" if payload["exceeds_iqr"] else "未超出"
    verdict_text = "回归（退出码 1）" if payload["regression"] else "未回归（退出码 0）"
    print("阈值：" + threshold_text + "；IQR：" + iqr_text + " => " + verdict_text)


def handle_compare(args: argparse.Namespace) -> int:
    """compare 子命令：用 median/IQR 规则判定回归。"""
    threshold: float = args.threshold
    if not math.isfinite(threshold) or threshold < 0:
        return fail("--threshold 必须是有限非负数")
    try:
        baseline = load_stats(args.baseline)
        candidate = load_stats(args.candidate)
    except ValueError as exc:
        return fail(str(exc))
    base_stats = baseline["stats"]
    cand_stats = candidate["stats"]
    base_median = float(base_stats["median"])
    cand_median = float(cand_stats["median"])
    base_iqr = float(base_stats["iqr"])
    if base_median <= 0:
        return fail("基线 median 必须为正数才能计算相对 delta")
    delta = cand_median / base_median - 1.0
    abs_delta = cand_median - base_median
    exceeds_threshold = delta > threshold
    exceeds_iqr = abs_delta > base_iqr
    regression = exceeds_threshold and exceeds_iqr
    warnings = compare_warnings(baseline, candidate)
    base_env = env_of(baseline)
    cand_env = env_of(candidate)
    payload = {
        "baseline": str(args.baseline),
        "candidate": str(args.candidate),
        "baseline_label": baseline.get("label"),
        "candidate_label": candidate.get("label"),
        "threshold": threshold,
        "delta": delta,
        "abs_delta_s": abs_delta,
        "base_iqr_s": base_iqr,
        "exceeds_threshold": exceeds_threshold,
        "exceeds_iqr": exceeds_iqr,
        "regression": regression,
        "rule": "regression 当且仅当 delta > threshold 且绝对增量 > 基线 IQR",
        "baseline_stats": base_stats,
        "candidate_stats": cand_stats,
        "baseline_env": base_env,
        "candidate_env": cand_env,
        "env_consistent": base_env.get("python") == cand_env.get("python")
        and base_env.get("platform") == cand_env.get("platform"),
        "warnings": warnings,
    }
    for warning in warnings:
        print("警告：" + warning, file=sys.stderr)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print_compare_table(payload)
    return EXIT_REGRESSION if regression else EXIT_OK


def add_sampling_args(parser: argparse.ArgumentParser) -> None:
    """run / exec 共用的采样参数。"""
    parser.add_argument("--warmup", type=int, default=2, help="预热次数，计时后丢弃（默认 2）")
    parser.add_argument("--repeat", type=int, default=10, help="采样次数（默认 10）")
    parser.add_argument("--label", default="baseline", help="基线标签，写进 JSON（默认 baseline）")
    parser.add_argument(
        "--json-out",
        type=Path,
        metavar="OUT.JSON",
        help="把结果 JSON 写到该路径，供 compare 直接读取",
    )


def build_parser() -> argparse.ArgumentParser:
    """命令行定义：run / exec / compare 三个子命令各有完整 --help。"""
    parser = argparse.ArgumentParser(
        prog="bench_stats.py",
        description="零依赖性能采样与回归门禁：median/IQR 统计 + 前后对比。",
        epilog=(
            "示例：\n"
            '  bench_stats.py run --cmd "python target.py 400" --label baseline '
            "--json-out before.json\n"
            "  bench_stats.py exec --target target.py:func --args-json '[[400]]' "
            "--label before --json-out before.json\n"
            "  bench_stats.py compare --baseline before.json --candidate after.json "
            "--threshold 0.10\n\n"
            "退出码：compare 0 未回归 / 1 回归 / 2 参数或文件错误；"
            "run/exec 0 成功 / 2 参数、命令或目标错误。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        metavar="{run,exec,compare}",
        help="子命令：run / exec / compare",
    )

    run_parser = subparsers.add_parser(
        "run",
        help="子进程跑命令并计时（含解释器启动）",
        description="反复执行一条命令并计时；stdout/stderr 丢弃，避免污染计时。",
        epilog=(
            "命令按 shlex 分词、不经过 shell（不支持管道/重定向，请写成脚本）。\n"
            "退出码：0 成功 / 2 参数或命令错误。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    run_parser.add_argument(
        "--cmd",
        required=True,
        metavar="COMMAND",
        help='要重复执行的命令，如 "python target.py 400"',
    )
    add_sampling_args(run_parser)
    run_parser.set_defaults(handler=handle_run)

    exec_parser = subparsers.add_parser(
        "exec",
        help="进程内调用 file:func 并计时（单次调用耗时）",
        description="按 file:func 加载目标函数，用 --args-json 给出的参数反复调用计时。",
        epilog=(
            "--args-json 是数组，元素为参数数组或 {\"args\": [...], \"kwargs\": {...}}：\n"
            "  '[[400]]'            -> 每次调用 func(400)\n"
            "  '[[[1, 2, 3]]]'      -> 每次调用 func([1, 2, 3])\n"
            "  '[{\"args\": [400], \"kwargs\": {}}]'\n"
            "多元素时每轮依次各调用一次，样本数为 repeat × 元素数。\n"
            "退出码：0 成功 / 2 参数、目标或调用错误。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    exec_parser.add_argument(
        "--target",
        required=True,
        metavar="PATH.PY:FUNC",
        help="目标模块路径与函数名，如 target.py:find_duplicates",
    )
    exec_parser.add_argument(
        "--args-json",
        required=True,
        metavar="JSON",
        help='调用参数数组，如 \'[[400]]\'',
    )
    add_sampling_args(exec_parser)
    exec_parser.set_defaults(handler=handle_exec)

    compare_parser = subparsers.add_parser(
        "compare",
        help="用 median/IQR 规则比较基线与候选，判定回归",
        description=(
            "读取 run/exec 产出的 JSON，计算 delta = candidate.median / baseline.median - 1，"
            "仅当 delta > threshold 且绝对增量 > 基线 IQR 时判 regression。"
        ),
        epilog=(
            "环境不一致（Python/平台）、测量模式不同、样本数 n < 5 会给出警告。\n"
            "退出码：0 未回归 / 1 回归 / 2 参数或文件错误。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    compare_parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        metavar="BEFORE.JSON",
        help="基线结果 JSON（run/exec 的 --json-out 产物）",
    )
    compare_parser.add_argument(
        "--candidate",
        type=Path,
        required=True,
        metavar="AFTER.JSON",
        help="候选结果 JSON",
    )
    compare_parser.add_argument(
        "--threshold",
        type=float,
        default=0.10,
        help="median 相对回归阈值（默认 0.10 = 10%%）",
    )
    compare_parser.add_argument("--json", action="store_true", help="以 JSON 输出判定结果")
    compare_parser.set_defaults(handler=handle_compare)
    return parser


def main(argv: list[str] | None = None) -> int:
    """命令行入口，返回进程退出码。"""
    configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    handler: Callable[[argparse.Namespace], int] = args.handler
    try:
        return handler(args)
    except KeyboardInterrupt:
        print("已中断", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
