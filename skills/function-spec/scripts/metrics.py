#!/usr/bin/env python3
"""函数规范审计用的零依赖 AST 指标：SKILL.md 与 references 的唯一计算入口。

用法::

    python metrics.py PATH [PATH ...] [--json] [--func NAME]

只读被分析文件、不写磁盘、只用标准库。``--json`` 的字段名是与 SKILL.md 的契约，
改动前先同步文档；默认输出人类可读摘要。``candidates`` 只是可供模型复核的证据，
不是最终判定。
"""

import argparse
import ast
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import TypedDict

EXIT_OK = 0
EXIT_FAIL = 2

FunctionNode = ast.FunctionDef | ast.AsyncFunctionDef

_NESTING_TYPES: tuple[type[ast.AST], ...] = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.Try,
    ast.TryStar,
    ast.Match,
)
_BRANCH_TYPES: tuple[type[ast.AST], ...] = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.With,
    ast.AsyncWith,
    ast.ExceptHandler,
)
_SCOPE_TYPES: tuple[type[ast.AST], ...] = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.Lambda,
)
_MUTABLE_DEFAULT_TYPES: tuple[type[ast.AST], ...] = (
    ast.List,
    ast.Dict,
    ast.Set,
    ast.Call,
)
_LOGGER_METHODS = frozenset(
    {"debug", "info", "warning", "warn", "error", "exception", "critical", "log"}
)
_LOGGER_NAMES = frozenset({"logger", "log"})
_LOGGING_BENIGN = frozenset({"getLogger", "getLevelName", "addLevelName", "disable"})
_CLOCK_DATETIME = frozenset({"now", "today", "utcnow"})
_CLOCK_TIME = frozenset(
    {"time", "time_ns", "monotonic", "perf_counter", "process_time", "thread_time"}
)
_NETWORK_ROOTS = frozenset({"requests", "urllib", "httpx", "aiohttp"})
_SENTINEL_STRINGS = frozenset(
    {"ERROR", "ERR", "FAIL", "FAILED", "INVALID", "NONE", "NULL", "UNKNOWN", "NOT_FOUND"}
)
_SENTINEL_NUMBERS = frozenset({0, -1})
_NEVER_CALLS = frozenset({"sys.exit", "os._exit", "exit", "quit"})
_R4_KINDS = frozenset({"clock", "random", "network", "db", "read_file", "write_file"})
_CONTAINER_NAMES = frozenset(
    {
        "list",
        "dict",
        "set",
        "frozenset",
        "tuple",
        "deque",
        "sequence",
        "mapping",
        "mutablesequence",
        "mutablemapping",
        "iterable",
        "iterator",
        "collection",
        "abstractset",
    }
)

_HEADER = (
    "# 说明：branches = if/for/while/except/with 计数，是复杂度代理值（非精确圈复杂度）；"
    "lines 从 def 行到末行（不含装饰器行）；末尾 candidates 只是候选证据，不是最终判定。"
)


class _InputError(Exception):
    """被分析文件不可用（缺失、不可读或语法错误）。"""


class SideEffect(TypedDict):
    """一条副作用证据。"""

    line: int
    kind: str
    detail: str


class ReturnInfo(TypedDict):
    """一条 return 语句的失败语义分类。"""

    line: int
    kind: str


class MutableDefault(TypedDict):
    """一个可变默认参数。"""

    param: str
    line: int


class BareExcept(TypedDict):
    """一个裸 except 处理器的行号。"""

    line: int


class Duplicate(TypedDict):
    """同作用域同名 def 的行号列表。"""

    name: str
    lines: list[int]


class DuplicateGroup(TypedDict):
    """带作用域标签的重复定义分组（用于生成 N4 证据）。"""

    scope: str
    name: str
    lines: list[int]


class Candidate(TypedDict):
    """一条规则候选证据；function 为 None 表示模块级问题。"""

    rule: str
    line: int
    function: str | None
    evidence: str


FunctionMetrics = TypedDict(
    "FunctionMetrics",
    {
        "name": str,
        "line": int,
        "end_line": int,
        "lines": int,
        "params": int,
        "bool_flags": int,
        "max_nesting": int,
        "branches": int,
        "docstring": bool,
        "annotated_params": int,
        "annotated_return": bool,
        "public": bool,
        "async": bool,
        "side_effects": list[SideEffect],
        "returns": list[ReturnInfo],
        "mutable_defaults": list[MutableDefault],
        "bare_excepts": list[BareExcept],
    },
)


class FileReport(TypedDict):
    """单个文件的完整报告（JSON files 数组的元素）。"""

    file: str
    module_side_effects: list[SideEffect]
    duplicates: list[Duplicate]
    functions: list[FunctionMetrics]
    candidates: list[Candidate]


class Report(TypedDict):
    """JSON 顶层结构。"""

    files: list[FileReport]


def _dotted_name(node: ast.expr) -> str | None:
    """把 Name/Attribute 链拼成点号名；含调用、下标等复杂节点时返回 None。"""
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return ".".join(reversed(parts))


def _render_call(node: ast.Call) -> str:
    """给出适合写进证据的调用描述，如 ``logging.info(...)``。"""
    name = _dotted_name(node.func)
    if name is not None:
        return f"{name}(...)"
    if isinstance(node.func, ast.Attribute):
        return f"...{node.func.attr}(...)"
    return "...(...)"


def _looks_like_logger(parts: list[str]) -> bool:
    """判断调用是否形如 logger.info(...) / self._logger.error(...)。"""
    if len(parts) < 2 or parts[-1] not in _LOGGER_METHODS:
        return False
    return any(part.strip("_").lower() in _LOGGER_NAMES for part in parts[:-1])


def _is_path_like(node: ast.expr) -> bool:
    """判断表达式是否 Path(...) 这类路径对象（用于识别 Path(...).open）。"""
    if not isinstance(node, ast.Call):
        return False
    return _dotted_name(node.func) in {"Path", "pathlib.Path", "PurePath", "pathlib.PurePath"}


def _open_mode(node: ast.Call) -> str:
    """取 open()/Path.open() 的 mode 参数，缺省按只读处理。"""
    candidates: list[ast.expr] = []
    if len(node.args) >= 2:
        candidates.append(node.args[1])
    candidates.extend(keyword.value for keyword in node.keywords if keyword.arg == "mode")
    for candidate in candidates:
        if isinstance(candidate, ast.Constant) and isinstance(candidate.value, str):
            return candidate.value
    return "r"


def _classify_call(node: ast.Call) -> tuple[str, str] | None:
    """识别一次调用属于哪类副作用；返回 (kind, detail)，不匹配返回 None。"""
    name = _dotted_name(node.func)
    detail = _render_call(node)
    parts = name.split(".") if name is not None else []
    root = parts[0] if parts else ""
    last = parts[-1] if parts else ""
    if name is None and isinstance(node.func, ast.Attribute):
        last = node.func.attr
    file_kind = _classify_file_call(node, name, last)
    if file_kind is not None:
        return file_kind, detail
    if name == "print":
        return "logging", detail
    if root == "logging":
        return None if last in _LOGGING_BENIGN else ("logging", detail)
    if _looks_like_logger(parts):
        return "logging", detail
    world_kind = _classify_world_call(name, root, last)
    return (world_kind, detail) if world_kind is not None else None


def _classify_file_call(node: ast.Call, name: str | None, last: str) -> str | None:
    """识别文件读写调用；open(...) 按 mode 判断读/写方向。"""
    if _is_open_call(node, name, last):
        mode = _open_mode(node)
        writing = any(flag in mode for flag in "wax")
        return "write_file" if writing else "read_file"
    if last in {"read_text", "read_bytes"}:
        return "read_file"
    if last in {"write_text", "write_bytes"}:
        return "write_file"
    return None


def _classify_world_call(name: str | None, root: str, last: str) -> str | None:
    """识别 clock/random/env/network/db 这些外部世界依赖调用。"""
    if root in {"datetime", "date"} and last in _CLOCK_DATETIME:
        return "clock"
    if root == "time" and last in _CLOCK_TIME:
        return "clock"
    if root == "random":
        return "random"
    if name in {"os.getenv"} or (name is not None and name.startswith("os.environ.")):
        return "env"
    if root in _NETWORK_ROOTS:
        return "network"
    if root == "sqlite3":
        return "db"
    return None


def _is_open_call(node: ast.Call, name: str | None, last: str) -> bool:
    """判断是否内置 open / io.open / Path(...).open 这类文件打开调用。"""
    if name in {"open", "io.open"}:
        return True
    if last != "open" or not isinstance(node.func, ast.Attribute):
        return False
    return _is_path_like(node.func.value)


def _env_access(node: ast.AST) -> str | None:
    """识别 os.environ[...] 形式的全局环境读取。"""
    if isinstance(node, ast.Subscript) and _dotted_name(node.value) == "os.environ":
        return "os.environ[...]"
    return None


def _iter_nodes(node: ast.AST) -> Iterator[ast.AST]:
    """遍历后代节点，但不进入嵌套的函数/类/lambda 作用域。"""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _SCOPE_TYPES):
            continue
        yield child
        yield from _iter_nodes(child)


def _side_effects(node: ast.AST) -> list[SideEffect]:
    """收集作用域内（不含嵌套作用域）的副作用证据。"""
    effects: list[SideEffect] = []
    for child in _iter_nodes(node):
        if isinstance(child, ast.Call):
            classified = _classify_call(child)
            if classified is not None:
                kind, detail = classified
                effects.append({"line": child.lineno, "kind": kind, "detail": detail})
        elif isinstance(child, ast.Subscript):
            env_detail = _env_access(child)
            if env_detail is not None:
                effects.append({"line": child.lineno, "kind": "env", "detail": env_detail})
    return effects


def _literal_number(node: ast.expr) -> int | float | None:
    """取字面量数字，包含 -1 这种一元负号写法。"""
    if isinstance(node, ast.Constant) and not isinstance(node.value, bool):
        if isinstance(node.value, int | float):
            return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub | ast.UAdd):
        inner = _literal_number(node.operand)
        if inner is not None:
            return -inner if isinstance(node.op, ast.USub) else inner
    return None


def _empty_container(node: ast.expr) -> bool:
    """判断是否空容器字面量（{} / [] / () / set() 之外的空字面量）。"""
    if isinstance(node, ast.Dict):
        return not node.keys
    if isinstance(node, ast.List | ast.Set | ast.Tuple):
        return not node.elts
    return False


def _constant_kind(value: object) -> str:
    """把常量值按失败语义归类：none / sentinel / value。"""
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "sentinel" if value is False else "value"
    if isinstance(value, int | float):
        return "sentinel" if value in _SENTINEL_NUMBERS else "value"
    if isinstance(value, str):
        return "sentinel" if value == "" or value.upper() in _SENTINEL_STRINGS else "value"
    return "value"


def _return_kind(value: ast.expr | None) -> str:
    """按失败语义归类一条 return：none / sentinel / value。"""
    if value is None:
        return "none"
    if isinstance(value, ast.Constant):
        return _constant_kind(value.value)
    number = _literal_number(value)
    if number is not None:
        return "sentinel" if number in _SENTINEL_NUMBERS else "value"
    if _empty_container(value):
        return "sentinel"
    return "value"


def _sentinel_category(value: ast.expr | None) -> str | None:
    """若该返回值是哨兵，给出类别（bool/number/string/container）；否则 None。"""
    if value is None:
        return None
    if isinstance(value, ast.Constant):
        if isinstance(value.value, bool):
            return "bool" if value.value is False else None
        if _constant_kind(value.value) != "sentinel":
            return None
        return "string" if isinstance(value.value, str) else "number"
    number = _literal_number(value)
    if number is not None:
        return "number" if number in _SENTINEL_NUMBERS else None
    if _empty_container(value):
        return "container"
    return None


def _annotation_text(annotation: ast.expr | None) -> str | None:
    """把返回注解渲染成文本；字符串前向引用直接取其内容。"""
    if annotation is None:
        return None
    if isinstance(annotation, ast.Constant) and isinstance(annotation.value, str):
        return annotation.value
    try:
        return ast.unparse(annotation)
    except (ValueError, RecursionError):
        return None


def _base_name(part: str) -> str:
    """取注解片段的基类型名（去掉模块前缀与泛型参数，转小写）。"""
    base = part.split("[", 1)[0].strip()
    return base.rsplit(".", 1)[-1].lower()


def _split_annotation(text: str) -> list[str]:
    """拆开注解的联合类型：Optional[X] 或 X | Y。"""
    compact = text.strip()
    if compact.startswith("Optional[") and compact.endswith("]"):
        return [compact.removeprefix("Optional[").removesuffix("]")]
    return compact.split("|")


def _annotation_kind(node: FunctionNode) -> str | None:
    """把返回注解归一成 bool / container；不明确时返回 None（不抑制候选）。"""
    text = _annotation_text(node.returns)
    if text is None:
        return None
    parts = [part.strip() for part in _split_annotation(text)]
    parts = [part for part in parts if part and part != "None"]
    if not parts:
        return None
    if all(part == "bool" for part in parts):
        return "bool"
    if all(_base_name(part) in _CONTAINER_NAMES for part in parts):
        return "container"
    return None


def _effective_sentinel_lines(node: FunctionNode) -> list[int]:
    """列出应视为失败哨兵的返回行；按返回注解放过合法的布尔/容器返回值。"""
    annotation = _annotation_kind(node)
    lines: list[int] = []
    for child in _iter_nodes(node):
        if not isinstance(child, ast.Return):
            continue
        category = _sentinel_category(child.value)
        if category is None:
            continue
        if category == "bool" and annotation == "bool":
            continue
        if category == "container" and annotation == "container":
            continue
        lines.append(child.lineno)
    return lines


def _never_line(node: ast.AST) -> int | None:
    """找出能让函数总不返回的 raise / sys.exit 行号。"""
    for child in _iter_nodes(node):
        if isinstance(child, ast.Raise):
            return child.lineno
        if isinstance(child, ast.Call) and _dotted_name(child.func) in _NEVER_CALLS:
            return child.lineno
    return None


def _returns(node: ast.AST) -> list[ReturnInfo]:
    """收集 return 分类；无 return 且总以 raise/exit 结束时记一条 never。"""
    entries: list[ReturnInfo] = [
        {"line": child.lineno, "kind": _return_kind(child.value)}
        for child in _iter_nodes(node)
        if isinstance(child, ast.Return)
    ]
    if entries:
        return entries
    never_line = _never_line(node)
    return [{"line": never_line, "kind": "never"}] if never_line is not None else []


def _bare_excepts(node: ast.AST) -> list[BareExcept]:
    """收集裸 except（无异常类型）的行号。"""
    return [
        {"line": child.lineno}
        for child in _iter_nodes(node)
        if isinstance(child, ast.ExceptHandler) and child.type is None
    ]


def _max_nesting(node: ast.AST, depth: int = 0) -> int:
    """统计 if/for/while/with/try/match 的最大嵌套层数（elif 与 if 同层）。"""
    best = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _SCOPE_TYPES):
            continue
        if isinstance(child, ast.If) and _is_elif(node, child):
            best = max(best, _max_nesting(child, depth))
            continue
        child_depth = depth + 1 if isinstance(child, _NESTING_TYPES) else depth
        best = max(best, child_depth, _max_nesting(child, child_depth))
    return best


def _is_elif(parent: ast.AST, child: ast.AST) -> bool:
    """判断 child 是否为 elif（if 的唯一 else 分支里的那个 if）。"""
    return isinstance(parent, ast.If) and len(parent.orelse) == 1 and parent.orelse[0] is child


def _count_branches(node: ast.AST) -> int:
    """统计 if/for/while/except/with 的数量（圈复杂度代理值）。"""
    return sum(1 for child in _iter_nodes(node) if isinstance(child, _BRANCH_TYPES))


def _params(node: FunctionNode) -> list[tuple[str, ast.expr | None, ast.expr | None]]:
    """列出全部参数 (name, annotation, default)，含 posonly/vararg/kwonly/kwarg。"""
    positional = [*node.args.posonlyargs, *node.args.args]
    defaults = list(node.args.defaults)
    offset = len(positional) - len(defaults)
    pairs: list[tuple[str, ast.expr | None, ast.expr | None]] = []
    for index, arg in enumerate(positional):
        default = defaults[index - offset] if index >= offset else None
        pairs.append((arg.arg, arg.annotation, default))
    vararg = node.args.vararg
    if vararg is not None:
        pairs.append((vararg.arg, vararg.annotation, None))
    for kwonly, kw_default in zip(node.args.kwonlyargs, node.args.kw_defaults, strict=True):
        pairs.append((kwonly.arg, kwonly.annotation, kw_default))
    kwarg = node.args.kwarg
    if kwarg is not None:
        pairs.append((kwarg.arg, kwarg.annotation, None))
    return pairs


def _function_metrics(node: FunctionNode, is_method: bool) -> FunctionMetrics:
    """计算单个函数行的全部指标；方法的首个 self/cls 不计入参数。"""
    end_line = node.end_lineno or node.lineno
    params = _params(node)
    if is_method and params and params[0][0] in {"self", "cls"}:
        params = params[1:]
    mutable_defaults: list[MutableDefault] = [
        {"param": name, "line": node.lineno}
        for name, _, default in params
        if isinstance(default, _MUTABLE_DEFAULT_TYPES)
    ]
    bool_flags = sum(
        1
        for _, _, default in params
        if isinstance(default, ast.Constant) and isinstance(default.value, bool)
    )
    return {
        "name": node.name,
        "line": node.lineno,
        "end_line": end_line,
        "lines": end_line - node.lineno + 1,
        "params": len(params),
        "bool_flags": bool_flags,
        "max_nesting": _max_nesting(node),
        "branches": _count_branches(node),
        "docstring": bool(ast.get_docstring(node)),
        "annotated_params": sum(1 for _, annotation, _ in params if annotation is not None),
        "annotated_return": node.returns is not None,
        "public": not node.name.startswith("_"),
        "async": isinstance(node, ast.AsyncFunctionDef),
        "side_effects": _side_effects(node),
        "returns": _returns(node),
        "mutable_defaults": mutable_defaults,
        "bare_excepts": _bare_excepts(node),
    }


def _collect_functions(
    root: ast.AST,
    scope: tuple[str, ...],
    found: list[tuple[tuple[str, ...], FunctionNode]],
) -> None:
    """收集所有作用域里的函数定义（含方法与嵌套函数），并记录所属作用域。"""
    for child in ast.iter_child_nodes(root):
        if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
            found.append((scope, child))
            _collect_functions(child, (*scope, f"{child.name}@{child.lineno}"), found)
        elif isinstance(child, ast.ClassDef):
            _collect_functions(child, (*scope, f"class {child.name}@{child.lineno}"), found)
        else:
            _collect_functions(child, scope, found)


def _scope_label(scope: tuple[str, ...]) -> str:
    """把作用域元组渲染成证据里的可读标签。"""
    return "模块顶层" if scope == ("<module>",) else " → ".join(scope)


def _duplicate_groups(
    found: list[tuple[tuple[str, ...], FunctionNode]],
) -> list[DuplicateGroup]:
    """按 (作用域, 名字) 分组，返回定义次数 >1 的组。"""
    buckets: dict[tuple[tuple[str, ...], str], list[int]] = {}
    for scope, node in found:
        buckets.setdefault((scope, node.name), []).append(node.lineno)
    return [
        {"scope": _scope_label(scope), "name": name, "lines": lines}
        for (scope, name), lines in buckets.items()
        if len(lines) > 1
    ]


def _candidate(rule: str, line: int, function: str | None, evidence: str) -> Candidate:
    """构造一条候选证据；字段名是 JSON 契约的一部分，勿改。"""
    return {"rule": rule, "line": line, "function": function, "evidence": evidence}


def _s1_candidates(item: FunctionMetrics) -> list[Candidate]:
    """S1：参数 >4 或布尔开关 >1。"""
    problems: list[str] = []
    if item["params"] > 4:
        problems.append(f"有 {item['params']} 个参数（>4）")
    if item["bool_flags"] > 1:
        problems.append(f"有 {item['bool_flags']} 个布尔开关（>1）")
    if not problems:
        return []
    evidence = f"{item['name']} " + "、".join(problems) + "；建议改配置对象或关键字参数"
    return [_candidate("S1", item["line"], item["name"], evidence)]


def _s2_candidates(item: FunctionMetrics) -> list[Candidate]:
    """S2：可变默认参数（list/dict/set/调用）。"""
    return [
        _candidate(
            "S2",
            mutable["line"],
            item["name"],
            f"参数 {mutable['param']} 的默认值是可变对象（定义期只求值一次，跨调用共享）",
        )
        for mutable in item["mutable_defaults"]
    ]


def _s3_candidates(item: FunctionMetrics) -> list[Candidate]:
    """S3：公共函数缺参数/返回注解。"""
    if not item["public"]:
        return []
    missing_params = item["annotated_params"] < item["params"]
    missing_return = not item["annotated_return"]
    if not missing_params and not missing_return:
        return []
    details: list[str] = []
    if missing_params:
        details.append(f"参数注解 {item['annotated_params']}/{item['params']}")
    if missing_return:
        details.append("缺返回注解")
    evidence = f"公共函数 {item['name']} 缺类型注解（{'、'.join(details)}）"
    return [_candidate("S3", item["line"], item["name"], evidence)]


def _d1_candidates(item: FunctionMetrics) -> list[Candidate]:
    """D1：公共函数无 docstring。"""
    if not item["public"] or item["docstring"]:
        return []
    return [_candidate("D1", item["line"], item["name"], f"公共函数 {item['name']} 无 docstring")]


def _e4_candidates(item: FunctionMetrics) -> list[Candidate]:
    """E4：裸 except。"""
    return [
        _candidate(
            "E4",
            bare["line"],
            item["name"],
            f"第 {bare['line']} 行裸 except 捕获全部异常（含 KeyboardInterrupt/SystemExit）",
        )
        for bare in item["bare_excepts"]
    ]


def _failure_candidates(node: FunctionNode, item: FunctionMetrics) -> list[Candidate]:
    """E1/E2：值域哨兵返回；布尔/容器注解下的合法返回值不算失败哨兵。"""
    sentinel_lines = _effective_sentinel_lines(node)
    none_lines = [entry["line"] for entry in item["returns"] if entry["kind"] == "none"]
    found: list[Candidate] = []
    if none_lines and sentinel_lines:
        mixed = sorted([*none_lines, *sentinel_lines])
        evidence = f"{item['name']} 同时用 none 与 sentinel 表示失败（返回行 {_join_lines(mixed)}）"
        found.append(_candidate("E1", mixed[0], item["name"], evidence))
    if sentinel_lines:
        evidence = f"{item['name']} 返回值域哨兵表示失败（行 {_join_lines(sentinel_lines)}）"
        found.append(_candidate("E2", sentinel_lines[0], item["name"], evidence))
    return found


def _r4_candidates(item: FunctionMetrics) -> list[Candidate]:
    """R4/P2：纯核心或函数体内直接使用 clock/random/network/db/文件 IO。"""
    return [
        _candidate(
            "R4/P2",
            effect["line"],
            item["name"],
            f"函数内直接调用 {effect['detail']}（{effect['kind']} 副作用）；"
            "应限定在边界层或改为参数注入",
        )
        for effect in item["side_effects"]
        if effect["kind"] in _R4_KINDS
    ]


def _size_candidates(item: FunctionMetrics) -> list[Candidate]:
    """G1/G2：函数过长、嵌套过深或分支（代理值）过多。"""
    found: list[Candidate] = []
    if item["lines"] > 50:
        evidence = f"函数 {item['lines']} 行（>50，考虑拆分）"
        found.append(_candidate("G1", item["line"], item["name"], evidence))
    problems: list[str] = []
    if item["max_nesting"] > 3:
        problems.append(f"最大嵌套 {item['max_nesting']}（>3）")
    if item["branches"] > 10:
        problems.append(f"分支代理值 {item['branches']}（>10）")
    if problems:
        evidence = f"{item['name']} " + "、".join(problems)
        found.append(_candidate("G2", item["line"], item["name"], evidence))
    return found


def _x1_candidates(item: FunctionMetrics) -> list[Candidate]:
    """X1 提示：无副作用且无其它候选的公共函数可直接单测，无需 mock。"""
    if not item["public"] or item["side_effects"]:
        return []
    evidence = f"{item['name']} 无副作用调用且未见其它候选，可直接编写单测，无需 mock"
    return [_candidate("X1", item["line"], item["name"], evidence)]


def _rules_for(node: FunctionNode, item: FunctionMetrics) -> list[Candidate]:
    """按固定规则顺序汇总单个函数的候选。"""
    found: list[Candidate] = []
    found.extend(_s1_candidates(item))
    found.extend(_s2_candidates(item))
    found.extend(_s3_candidates(item))
    found.extend(_d1_candidates(item))
    found.extend(_e4_candidates(item))
    found.extend(_failure_candidates(node, item))
    found.extend(_r4_candidates(item))
    found.extend(_size_candidates(item))
    return found


def _join_lines(lines: list[int]) -> str:
    """把行号列表渲染成「第 40、41 行」这样的中文片段。"""
    return "、".join(str(line) for line in lines)


def _n4_candidates(groups: list[DuplicateGroup]) -> list[Candidate]:
    """N4：同作用域重复定义；每个后出现的定义一条候选。"""
    candidates: list[Candidate] = []
    for group in groups:
        evidence = _duplicate_evidence(group)
        for line in group["lines"][1:]:
            candidates.append(_candidate("N4", line, group["name"], evidence))
    return candidates


def _duplicate_evidence(group: DuplicateGroup) -> str:
    """渲染 N4 证据，包含全部行号与作用域。"""
    line_text = _join_lines(group["lines"])
    if group["scope"] == "模块顶层":
        return f"def {group['name']} 在第 {line_text} 行重复定义（后一份静默覆盖前一份）"
    return f"def {group['name']} 在第 {line_text} 行重复定义（作用域 {group['scope']}）"


def _function_candidates(
    records: list[tuple[FunctionNode, FunctionMetrics]], groups: list[DuplicateGroup]
) -> list[Candidate]:
    """生成函数级候选：N4 优先，随后按函数出现顺序与规则固定顺序。"""
    n4_by_line = {candidate["line"]: candidate for candidate in _n4_candidates(groups)}
    result: list[Candidate] = []
    for node, item in records:
        duplicate = n4_by_line.get(item["line"])
        if duplicate is not None:
            result.append(duplicate)
        rules = _rules_for(node, item)
        if not rules and duplicate is None:
            rules = _x1_candidates(item)
        result.extend(rules)
    return result


def _module_candidates(effects: list[SideEffect]) -> list[Candidate]:
    """P1：模块级（导入期）副作用。"""
    return [
        _candidate(
            "P1",
            effect["line"],
            None,
            f"第 {effect['line']} 行在导入期执行 {effect['kind']}：{effect['detail']}；"
            "import 即产生副作用",
        )
        for effect in effects
    ]


def _load_tree(raw_path: str) -> ast.Module:
    """读取并解析源文件；不可读或语法错误时抛 _InputError。"""
    path = Path(raw_path)
    if not path.exists():
        raise _InputError(f"文件不存在：{raw_path}")
    if not path.is_file():
        raise _InputError(f"不是普通文件：{raw_path}")
    try:
        source = path.read_text(encoding="utf-8-sig")
    except OSError as error:
        raise _InputError(f"无法读取：{raw_path}（{error.strerror or error}）") from error
    except UnicodeDecodeError as error:
        raise _InputError(f"无法以 UTF-8 解码：{raw_path}") from error
    try:
        return ast.parse(source, filename=raw_path)
    except (SyntaxError, ValueError) as error:
        line = getattr(error, "lineno", None)
        position = f"第 {line} 行" if line is not None else "位置未知"
        raise _InputError(f"语法错误：{raw_path}（{position}：{error}）") from error


def _function_records(
    found: list[tuple[tuple[str, ...], FunctionNode]],
) -> list[tuple[FunctionNode, FunctionMetrics]]:
    """为每个函数定义生成 (AST 节点, 指标)；方法的首个 self/cls 不计入参数。"""
    return [
        (node, _function_metrics(node, bool(scope) and scope[-1].startswith("class ")))
        for scope, node in found
    ]


def _analyze_file(raw_path: str, func_filter: str | None) -> FileReport:
    """分析单个文件，返回与 JSON schema 一致的报告。"""
    tree = _load_tree(raw_path)
    found: list[tuple[tuple[str, ...], FunctionNode]] = []
    _collect_functions(tree, ("<module>",), found)
    groups = _duplicate_groups(found)
    effects = _side_effects(tree)
    records = _function_records(found)
    if func_filter is not None:
        records = [record for record in records if record[1]["name"] == func_filter]
    return {
        "file": raw_path,
        "module_side_effects": effects,
        "duplicates": [{"name": group["name"], "lines": group["lines"]} for group in groups],
        "functions": [item for _, item in records],
        "candidates": [
            *_module_candidates(effects),
            *_function_candidates(records, groups),
        ],
    }


def _render_effects(title: str, effects: list[SideEffect]) -> list[str]:
    """渲染副作用小节。"""
    if not effects:
        return [f"{title}: none"]
    rows = [f"{title} ({len(effects)}):"]
    rows.extend(f"  L{effect['line']} [{effect['kind']}] {effect['detail']}" for effect in effects)
    return rows


def _render_duplicates(groups: list[Duplicate]) -> list[str]:
    """渲染重定义小节。"""
    if not groups:
        return ["duplicates: none"]
    rows = [f"duplicates ({len(groups)}):"]
    rows.extend(
        f"  {group['name']}: " + ", ".join(f"L{line}" for line in group["lines"])
        for group in groups
    )
    return rows


def _function_extras(item: FunctionMetrics) -> str:
    """拼出 returns/mut/bare/side 这些补充标记。"""
    extras: list[str] = []
    kinds = list(dict.fromkeys(entry["kind"] for entry in item["returns"]))
    if kinds:
        extras.append("returns=" + "+".join(kinds))
    if item["mutable_defaults"]:
        extras.append("mut=" + ",".join(entry["param"] for entry in item["mutable_defaults"]))
    if item["bare_excepts"]:
        extras.append("bare=" + ",".join(str(entry["line"]) for entry in item["bare_excepts"]))
    if item["side_effects"]:
        side_kinds = list(dict.fromkeys(effect["kind"] for effect in item["side_effects"]))
        extras.append("side=" + ",".join(side_kinds))
    return " ".join(extras)


def _render_function(item: FunctionMetrics) -> str:
    """渲染单个函数的一行指标。"""
    parts = [
        item["name"].ljust(22),
        f"L{item['line']}-{item['end_line']}".ljust(12),
        f"{item['lines']}L".ljust(5),
        f"params={item['params']}",
        f"bools={item['bool_flags']}",
        f"nest={item['max_nesting']}",
        f"branches={item['branches']}",
        f"doc={'yes' if item['docstring'] else 'no'}",
        f"ann={item['annotated_params']}/{item['params']}",
        f"ret={'yes' if item['annotated_return'] else 'no'}",
        "public" if item["public"] else "private",
        "async" if item["async"] else "sync",
    ]
    extras = _function_extras(item)
    if extras:
        parts.append(extras)
    return "  " + " ".join(parts)


def _render_candidate(item: Candidate) -> str:
    """渲染一条候选证据。"""
    where = item["function"] if item["function"] is not None else "<module>"
    return f"  [{item['rule']}] L{item['line']} {where}: {item['evidence']}"


def _render_file(report: FileReport) -> list[str]:
    """渲染单个文件的完整小节。"""
    rows = [f"=== {report['file']} ==="]
    rows.extend(_render_effects("module_side_effects", report["module_side_effects"]))
    rows.extend(_render_duplicates(report["duplicates"]))
    functions = report["functions"]
    if functions:
        rows.append(f"functions ({len(functions)}):")
        rows.extend(_render_function(item) for item in functions)
    else:
        rows.append("functions: none")
    candidates = report["candidates"]
    if candidates:
        rows.append(f"candidates ({len(candidates)}):")
        rows.extend(_render_candidate(item) for item in candidates)
    else:
        rows.append("candidates: none")
    return rows


def _render_summary(reports: list[FileReport]) -> str:
    """渲染多文件总计一行。"""
    functions = sum(len(report["functions"]) for report in reports)
    candidates = sum(len(report["candidates"]) for report in reports)
    return (
        f"共 {len(reports)} 个文件 / {functions} 个函数 / {candidates} 条候选证据"
        "（候选需按规则逐条复核，不是最终判定）。"
    )


def _render_reports(reports: list[FileReport]) -> list[str]:
    """渲染多文件的人类可读输出（表头 + 每个文件 + 总计）。"""
    output = [_HEADER, ""]
    for report in reports:
        output.extend(_render_file(report))
        output.append("")
    output.append(_render_summary(reports))
    return output


def _configure_stdio() -> None:
    """强制 stdout/stderr 用 UTF-8，保证中文证据与 ensure_ascii=False 的 JSON 可读。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    """CLI 入口：分析给定文件并输出；输入不可用时返回退出码 2。"""
    _configure_stdio()
    parser = argparse.ArgumentParser(
        prog="metrics.py",
        description="零依赖 AST 指标：行数/参数/嵌套/副作用/重复定义/失败语义候选证据。",
    )
    parser.add_argument("paths", nargs="+", metavar="PATH", help="要分析的 Python 文件")
    parser.add_argument("--json", action="store_true", help="输出 JSON（UTF-8，字段名固定）")
    parser.add_argument("--func", metavar="NAME", help="只报告指定名字的函数")
    arguments = parser.parse_args(argv)
    try:
        reports = [_analyze_file(path, arguments.func) for path in arguments.paths]
    except _InputError as error:
        print(f"metrics.py: {error}", file=sys.stderr)
        return EXIT_FAIL
    if arguments.json:
        print(json.dumps({"files": reports}, ensure_ascii=False, indent=2))
        return EXIT_OK
    print("\n".join(_render_reports(reports)))
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
