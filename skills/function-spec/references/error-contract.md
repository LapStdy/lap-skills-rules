# 错误契约（E1–E6 展开）

错误契约规定一个函数在失败时给调用方什么：返回空值、抛异常，或两者都不许混用。规则 ID 与级别沿用 [function-standard-v0.md](./function-standard-v0.md) 的规则表；本文只展开 E1–E6，并给出契约三档的落地方式。

## 1. 两类失败

| 类型 | 判据 | 例子 | 正确处理 | 依据 |
|---|---|---|---|---|
| 可预期失败 | 业务上"本来就可能发生"，不是代码写错 | 按 ID 查不到用户；配置里没有该键；请求的资源已被删除 | 返回空值：Python `T \| None`，TS `T \| undefined`；调用方必须处理 | [Go · In-Band Errors](https://go.dev/wiki/CodeReviewComments)、[Google §2.4](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md) |
| 不可预期失败 | 代码或环境的错误：调用方违约、配置缺失、内部不变量破坏 | 传入负数容量；必需的 API key 未设置；缓存结构被外部改坏 | 抛异常：`ValueError`/`TypeError`/自定义 `Error` | [Google §2.4](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md) |
| 外部数据非法 | 数据来自不可信边界（文件/HTTP/数据库/用户输入） | JSON 缺字段、类型不符、超出值域 | 在边界抛 `ValueError`（消息带原始值），不把非法值送进核心 | [pydantic Validators](https://pydantic.dev/docs/validation/latest/concepts/validators/)、[Google §2.4](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md) |

两类失败的归因不同：可预期失败是"查询结果为空"，调用方继续走正常分支；不可预期失败是"调用方 bug 或实现 bug"，必须让故障尽早可见。把后者降级为空值，等于把故障点后移，最终在离现场很远的地方报错。

## 2. 判定顺序

按顺序判断，命中即停：

1. 失败原因是"调用方给错了参数、环境没配好、内部状态被破坏"？→ 抛异常（调用方 bug 或实现 bug，必须暴露）。
2. 失败原因是"这个对象/键/记录在业务上可以不存在"？→ 返回 `None`/`undefined`，并在 docstring 的 `Returns` 中写明空值的含义。
3. 失败原因是"外部数据格式非法"？→ 在边界解析处抛 `ValueError`，消息带原始片段。
4. 同一个函数两种情况都要？→ 拆成两个：`try_parse_x()` 返回 `X | None`（可预期），`parse_x()` 抛异常（供要求严格的调用方使用）。命名差异本身就是契约差异。
5. 以上都不适用？→ 说明契约尚未定义清楚；先补 docstring，再写实现。

| 场景 | 处理 | 原因 |
|---|---|---|
| 按 key 查缓存未命中 | 返回 `None` | 业务上可以不存在 |
| 除数为零 | 不捕获，向上抛 `ZeroDivisionError` | 调用方违约 |
| 用户输入 `"abc"` 当数字 | 边界处 `raise ValueError` | 外部数据非法 |
| 分页参数 `page < 1` | `raise ValueError` | 违反前置条件 |
| 可选配置未设置 | 返回 `None` 或默认值（在配置层定死） | 业务上可以不存在 |
| 必需依赖未注入 | `raise RuntimeError` 或自定义 `Error` | 环境错误 |
| 第三方响应缺必需字段 | 边界处抛 `ValueError`，带响应片段 | 外部数据非法 |
| 数据库连接失败 | 向上抛，不在业务函数里吞 | 环境错误 |
| 写文件失败（磁盘满/无权限） | 向上抛 | 环境错误 |

## 3. 同一模块内必须一致（硬规则）

在同一个模块（或同一组对外接口）里，同一种失败的表达必须只有一种。这是 E3 的核心，也是调用方最容易踩的坑：每个函数各用一套表达，调用点就必须同时写 `if x is None`、`if x == -1`、`try/except`，漏掉一个就是线上故障。

| 事故 | 症状 | 修法 |
|---|---|---|
| A 函数返 `None`、B 函数抛 `KeyError` | 调用方必须同时判空与捕获异常 | 统一为空值或统一为异常；在边界把 `dict.get` 与异常版本分开暴露 |
| 查不到返 `-1`、参数错返 `None` | 调用方无法区分"没找到"与"调用错了" | 哨兵改为 `None`；参数错误改抛 `ValueError` |
| docstring 写 `Raises: ValueError`，实现抛 `RuntimeError` | 按文档写的 `except` 抓不到 | 改实现或改文档，二者只能有一个真源 |
| `None` 同时表示"成功但无内容"与"失败" | 调用方无法判断成功与否 | 失败改抛异常；确需区分时用显式类型（如判别联合 `{ok: true} \| {ok: false, error}`），属团队可选方案，不是 v0 默认 |

判定方法：在一个模块内列出所有"查不到/没找到"的分支，检查它们的返回或抛出是否同形。不同形即 E3 命中，与单个函数写得好不好无关。

## 4. E1–E6 逐条

### E1 可预期失败返空值，不可预期失败抛异常，不混用（MUST）

违规：签名看不出失败语义，调用方猜。

```python
def find_user(uid: int) -> dict:
    row = _DB.get(uid)
    if row is None:
        return {}          # 空字典冒充"没找到"
    return row
```

正确：签名与 docstring 都写清空值含义，参数错误抛异常。

```python
def find_user(uid: int) -> User | None:
    """Return the user with ``uid``, or None if no such user exists.

    Raises:
        ValueError: If ``uid`` is not a positive integer.
    """
    if uid <= 0:
        raise ValueError(f"uid must be positive, got {uid!r}")
    return _DB.get(uid)
```

检查：失败路径单测（§6）+ 模块内一致性（§3）。

### E2 禁止值域哨兵（MUST）

值域哨兵指"用一个合法值表示失败"。问题不在写法难看，而在于哨兵会参与后续计算，产生错误结果而不是报错。

| 哨兵 | 问题 | 改法 |
|---|---|---|
| `-1` 表示"没找到" | `-1` 是合法整数，调用方会照常参与计算 | 返回 `None` 或抛异常 |
| `-1` 表示"长度未知" | 同上 | `int \| None` |
| `""` 表示失败 | 空串是合法值（字段本来就可以为空） | 返回 `None` 或抛异常 |
| `"ERROR"` 表示失败 | 与真实字符串数据无法区分 | 抛异常 |
| `{}` 表示失败 | 空字典是合法的"无数据" | 返回 `None` 或区分类型 |
| `False` 冒充失败 | `False` 是合法布尔结果 | 抛异常，或返回 `bool` 并另设错误通道 |
| `(1e6, 1e6)` 表示退化坐标 | 哨兵进入下游计算，静默算出错误结果 | 返回 `None` 或抛异常 |

Go 的论证：in-band 错误值会被调用方当正常值继续用，正确做法是额外返回一个"是否成功"的值；Python/TS 没有多返回值传统，对等做法是 `Optional` + 异常 + docstring 的 `Raises`（[Go · In-Band Errors](https://go.dev/wiki/CodeReviewComments)）。

### E3 同一模块失败语义一致，`Raises:` 与实现一致（MUST）

- 模块内"查不到"只有一种表达（全返空值，或全抛同一种异常）。
- docstring 的 `Raises:` 列出实现实际会抛的异常类型；列了但不会抛、抛了但没列，都算命中。
- 异常类型转换处必须保留因果：`raise ValueError(...) from exc`。

检查：`grep -n "raise "` 与 docstring 的 `Raises:` 逐条比对；失败路径测试断言异常类型。

### E4 禁裸 `except`、只捕能处理的异常、`raise X from Y`（MUST）

违规：

```python
try:
    cfg = json.loads(text)
except:                     # 连 KeyboardInterrupt / SystemExit 一起吞
    cfg = {}
```

正确：

```python
try:
    cfg = json.loads(text)
except json.JSONDecodeError as exc:
    raise ValueError(f"invalid config: {text[:80]!r}") from exc
```

| 做法 | 允许 | 原因 |
|---|---|---|
| `except:` | 禁止 | 捕获 `BaseException` 子类，会打断 Ctrl-C 与进程退出 |
| `except Exception:` | 仅最外层降级处 | 必须记录原始异常并决定是否继续；不得静默 `pass` |
| 捕获后静默 | 禁止 | 失败必须暴露或显式降级，`pass` 等于丢弃证据 |
| `raise X from Y` | 转换异常时必写 | 保留 `__cause__`，堆栈可追到原始错误 |
| `try` 范围 | 只包可能失败的行 | 范围越大，误捕越可能，定位越难 |

依据：[PEP 8 · Programming Recommendations](https://peps.python.org/pep-0008/)、[Google §2.4](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md)。

### E5 `assert` 只用于内部不变量（MUST）

`assert` 在 `python -O` 下整条不生成字节码（[Python 语言参考 · assert](https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement)），因此它不能承担任何影响正确性的职责。可用判据：把 `assert` 删掉，代码仍应正确（[Google §2.4](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md)）。

| 用途 | 判定 | 例子 |
|---|---|---|
| 内部不变量（数据结构自洽） | 允许 | 唯一性断言、分支互斥断言 |
| 开发期检查（性能敏感路径） | 允许，需注释说明 | 热循环里的形状检查 |
| 校验用户输入/外部数据 | 禁止 | `assert value >= 1024` |
| 前置条件校验 | 禁止 | `assert path.endswith(".json")` |
| 控制流分支 | 禁止 | 依赖 `assert` 成立才继续 |

正确（内部不变量，删掉不影响逻辑）：

```python
def _reindex(rows: list[Row]) -> dict[int, Row]:
    mapping = {row.id: row for row in rows}
    assert len(mapping) == len(rows), "row ids must be unique"  # 内部不变量
    return mapping
```

违规（用 `assert` 做入参校验，`-O` 后校验消失）：

```python
def set_capacity(value: int) -> None:
    assert value >= 1024, "capacity too small"   # 用户输入校验：禁止
    self._cap = value
```

### E6 自定义异常与错误消息（SHOULD）

| 要求 | 好 | 坏 |
|---|---|---|
| 继承最近的合适内建异常 | `class ConfigError(ValueError)` | `class ConfigError(Exception)`（无差别捕获） |
| 名字以 `Error` 结尾 | `ParseError`、`ConfigError` | `ParseFailure`、`BadThing` |
| 不重复模块名 | `config.Error` | `config.ConfigError` |
| 消息精确可 grep | `"config key 'timeout' missing in /etc/app.toml"` | `"错误"`、`"invalid"` |
| 消息带出错值 | `f"unexpected status {status!r}"` | `"unexpected status"` |
| 不拼不可信输入全文与密钥 | `text[:80]!r` | 整个请求体、token、密码 |

依据：[PEP 8](https://peps.python.org/pep-0008/)、[Google §2.4](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md)。

## 5. 契约三档

| 档 | 做法 | 成本/依赖 | 何时用 | 本规范处理 |
|---|---|---|---|---|
| L1 文档契约 | docstring 写 `Args`/`Returns`/`Raises`，写明前置条件与空值含义 | 零依赖 | 所有公共函数 | 强制（D1/D2） |
| L2 代码契约 | 边界显式 `raise ValueError/TypeError`；外部输入用 pydantic 校验；内部 `assert` 只做不变量 | 零依赖（pydantic 可选） | 所有公共 API 入口 | 强制（E1–E5） |
| L3 库契约 | icontract / deal：`@require`/`@ensure`/`@invariant` | 新依赖 + 运行时开销 | 出现稳定公共 API 后再评估 | v0 不引入 |

### 5.1 L1 模板

```python
def transfer(src: Account, dst: Account, amount: int) -> None:
    """Move ``amount`` from ``src`` to ``dst``.

    Args:
        src: Source account; must have at least ``amount`` available.
        dst: Destination account; must not be ``src``.
        amount: Positive integer, in minor units.

    Returns:
        None.

    Raises:
        ValueError: If ``amount`` is not positive, or ``src`` is ``dst``.
        InsufficientFundsError: If ``src`` has less than ``amount`` available.

    Side Effects:
        Mutates the balances of ``src`` and ``dst``; appends one ledger row.
        Not idempotent: retrying the same call moves the money twice.
    """
```

L1 的最小要求是四件事写成文字：输入域、输出保证、错误类型、副作用。缺副作用说明的 docstring 会把"有副作用"的函数伪装成查询函数，属 D2 命中。

### 5.2 L2 模板

```python
def transfer(src: Account, dst: Account, amount: int) -> None:
    if amount <= 0:
        raise ValueError(f"amount must be positive, got {amount!r}")
    if src is dst:
        raise ValueError("cannot transfer to the same account")
    if src.balance < amount:
        raise InsufficientFundsError(
            f"insufficient funds: balance={src.balance!r}, amount={amount!r}"
        )
    ...
```

L2 的原则是"边界检查只做一次，失败立刻抛，核心逻辑不再防御"。核心里的重复检查会把契约变成散落的 `if`，也让失败信息失去来源。

### 5.3 L3 延后的原因

| 理由 | 说明 | 依据 |
|---|---|---|
| `python -O` 下整体关闭 | 装饰器的契约默认只在 `__debug__` 为真时执行；关闭后行为与生产不一致，不能当业务校验 | [icontract Usage](https://icontract.readthedocs.io/en/latest/usage.html) |
| 条件会被重放求值 | 契约条件必须无副作用，否则每次调用都可能触发额外副作用 | [icontract Usage](https://icontract.readthedocs.io/en/latest/usage.html) |
| 新依赖与启动成本 | 零依赖环境无法安装；导入期有成本 | [deal](https://github.com/life4/deal) |

结论：v0 用 L1 + L2 覆盖"边界显式抛异常 + docstring 记录 + 失败路径测试"，可拿到主要收益且零新增依赖。出现稳定公共 API、且有依赖管理流程后，再评估把 L3 作为本技能的补充文档。

## 6. 失败路径测试

规则：每个可预期失败至少 1 个用例；每个不可预期失败至少 1 个抛异常断言；成功路径同时要有用例，否则契约只测了一半。

```python
import pytest

from shop.accounts import InsufficientFundsError, transfer


def test_find_user_returns_none_when_missing(repo):
    assert repo.find_user(999) is None          # 可预期失败 → 空值


@pytest.mark.parametrize("amount", [0, -1, -100])
def test_transfer_rejects_non_positive_amount(accounts, amount):
    with pytest.raises(ValueError, match="amount must be positive"):
        transfer(accounts.src, accounts.dst, amount)


def test_transfer_rejects_same_account(accounts):
    with pytest.raises(ValueError, match="same account"):
        transfer(accounts.src, accounts.src, 100)


def test_transfer_raises_when_funds_missing(accounts):
    with pytest.raises(InsufficientFundsError, match="insufficient funds"):
        transfer(accounts.broke, accounts.dst, 100)
```

| 路径 | 断言什么 | 说明 |
|---|---|---|
| 键不存在/查不到 | `is None` | 空值是契约的一部分，不是异常情况 |
| 参数非法 | `pytest.raises(ValueError, match=...)` | `match` 只匹配稳定片段（关键短语），不匹配整句 |
| 前置条件缺失 | `pytest.raises(RuntimeError)` | 依赖未注入、环境错误 |
| 外部数据非法 | `pytest.raises(ValueError)`，并断言消息含原始值 | 防止非法值流进核心 |
| 正常路径 | 断言返回值 | 保证契约另一侧也成立 |

要点：不用 `try/except + assert False` 的形式，`pytest.raises` 更精确且失败信息更好；`match` 用正则，注意转义括号等字符。

## 7. 常见陷阱

| 陷阱 | 现象 | 改法 | 依据 |
|---|---|---|---|
| `dict.get(key)` 的默认 `None` 混入业务 | "缺键"与"值本身是 None"无法区分 | 需要区分时用 `key in d` 先判，或用唯一哨兵对象 `_MISSING = object()`，或改用 `d[key]` + `KeyError` | Python 语言语义 |
| 真值判断吞掉合法值 | `if not x:` 把 `0`、`""`、`[]`、`False` 都当失败 | 空值判断用 `if x is None:`；容器判空单独写 `if not items:` 并明确语义 | Python 语言语义 |
| 兜底 `return None` 掩盖契约 | 该抛的异常也被吞，故障点后移 | 只在"业务上可不存在"处返回 `None`；其余显式 `raise` | [Google §2.4](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md) |
| `except Exception: log; return None` | 同一模式把所有 bug 变成空值 | 只在最外层降级；保留 `raise`/`from`，或返回显式失败结果 | [PEP 8](https://peps.python.org/pep-0008/) |
| `assert` 校验入参 | `-O` 后校验消失 | 改 `raise ValueError` | [assert 语义](https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement) |
| 用 `False` 表示失败 | 与合法布尔结果冲突 | 抛异常，或返回独立的状态值 | [Go](https://go.dev/wiki/CodeReviewComments) |
| 异常消息拼进整段用户输入 | 日志注入、密钥泄漏、无法 grep | 截断（如前 80 字符）+ `repr` + 去掉敏感字段 | [Google §2.4](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md) |
| 用异常做正常控制流 | 循环里靠 `StopIteration`/`KeyError` 走常规分支 | 改用显式判断（`in`、`next(..., default)`） | [Google §2.4](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md) |

## 8. 检查清单

| # | 检查项 | 方法 | 通过条件 |
|---|---|---|---|
| 1 | 每个公共函数的 docstring 有 `Raises` | 读 docstring | 与实现实际抛出的类型一致 |
| 2 | 模块内"查不到"只有一种表达 | 列出所有相关分支 | 同形（全空值或全同一种异常） |
| 3 | 无值域哨兵返回 | `grep -nE 'return -1\|return ""\|return {}\|return "ERROR"'` | 无命中 |
| 4 | 无裸 `except` | `grep -n "except:"` | 无命中 |
| 5 | 异常转换处有 `from` | 读 `raise` 语句 | 转换时全部带 `from` |
| 6 | `assert` 只做不变量 | `grep -n "assert "` + 人工判 | 删掉后代码仍正确 |
| 7 | 失败路径有测试 | 读测试文件 | 每类失败至少 1 个用例 |
| 8 | 异常消息可 grep 且带值 | 读 `raise` 语句 | 稳定前缀 + 出错值 + 无敏感信息 |
