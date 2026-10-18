"""pytest-benchmark 模板：计时与正确性断言同文件。

复制到被测模块同目录，改 TARGET / FUNCTION / SIZE 与 fixture 输入即可。

命令（在准备区根跑；benchmark 存储路径由 pyproject 的 --benchmark-storage 指到 .tmp/benchmarks）：
    pytest bench.py --benchmark-save=baseline
    pytest bench.py --benchmark-compare=0001
    pytest bench.py --benchmark-compare=0001 --benchmark-compare-fail=median:10%
注意：--benchmark-compare 按「文件名前缀」过滤，存成 0001_baseline.json 后要用编号
      0001（或完整文件路径），写 --benchmark-compare=baseline 匹配不到文件。

约定：
    - expected 在 fixture 里用与实现无关的参考算法先算好。
    - benchmark 只包被测函数调用；assert 在 benchmark 之外执行（正确性与计时同文件）。
    - pytest-benchmark 不存在时整文件 skip，模板本身始终可编译、可收集。
    - 无 pytest-benchmark 时的降级命令见文件末尾注释。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

# 插件缺失时整文件 skip，避免 fixture 'benchmark' not found 报错。
pytest.importorskip(
    "pytest_benchmark",
    reason="需要 pytest-benchmark：python -m pip install pytest-benchmark",
)

TARGET = Path(__file__).with_name("target.py")
FUNCTION = "find_duplicates"
SIZE = 400


def load_target() -> Any:
    """按路径加载被测模块；不存在或加载失败时 skip，而不是让模板爆炸。"""
    if not TARGET.is_file():
        pytest.skip(
            "被测模块不存在：" + str(TARGET) + "（复制被测实现为 target.py，或改 TARGET）"
        )
    spec = importlib.util.spec_from_file_location("target_under_bench", TARGET)
    if spec is None or spec.loader is None:
        pytest.skip("无法加载被测模块：" + str(TARGET))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def target() -> Any:
    """被测模块。"""
    return load_target()


@pytest.fixture(scope="module")
def items() -> list[int]:
    """固定输入：覆盖重复值与无重复段，规模由 SIZE 控制。"""
    return [(index * 7919) % 100 for index in range(SIZE)]


@pytest.fixture(scope="module")
def expected(items: list[int]) -> list[int]:
    """先算 expected：用与实现无关的参考算法（集合计数），不调用被测函数。"""
    seen: set[int] = set()
    duplicates: list[int] = []
    for value in items:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


def test_correctness(target: Any, items: list[int], expected: list[int]) -> None:
    """正确性：不带计时的普通调用；行为不对先修行为，再谈性能。"""
    assert target.find_duplicates(items) == expected


def test_benchmark(
    benchmark: Any,
    target: Any,
    items: list[int],
    expected: list[int],
) -> None:
    """计时：benchmark 只包被测调用，返回值断言在 benchmark 之外执行。"""
    result = benchmark(target.find_duplicates, items)
    assert result == expected


# --- 无 pytest-benchmark 时的降级（标准库手写采样，零第三方依赖） ---
# exec 模式（进程内单次调用耗时；适合接收规模参数的函数，如 build_report(size)）：
#   python skills/perf-evidence/scripts/bench_stats.py exec \
#       --target target.py:build_report --args-json '[[400]]' \
#       --warmup 2 --repeat 10 --label before --json-out before.json
#   # 改完实现后同命令，改 --label after --json-out after.json
#   python skills/perf-evidence/scripts/bench_stats.py compare \
#       --baseline before.json --candidate after.json --threshold 0.10
#
# run 模式（子进程含解释器启动；适合带 __main__ 的入口脚本）：
#   python skills/perf-evidence/scripts/bench_stats.py run \
#       --cmd "python target.py 400" --label before --json-out before.json
#
# 降级口径：median/IQR/样本数与环境照常写 JSON，但噪声比 pytest-benchmark 大，
# 只能做趋势/粗门禁；CI 硬门禁优先用 pytest-benchmark。
