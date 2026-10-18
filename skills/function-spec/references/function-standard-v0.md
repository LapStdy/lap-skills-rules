# 函数规范 v0 · 29 条规则

适用范围：单个函数、单个类的公共方法，或包含若干函数的小 diff。语言范围为 Python 与 TypeScript，两语言共用同一套规则 ID，差异见 §7。
配套文档：[error-contract.md](./error-contract.md)，E1–E6 的展开、两类失败的判定与契约三档。
依据：29 条规则每行给出一手来源与可点击链接（标签与 URL 对照见 §8）。

## 1. 使用方式

### 1.1 级别

| 级别 | 含义 | 处理方式 |
|---|---|---|
| MUST | 违反即缺陷 | 计入不通过；每个命中给出规则 ID、证据（文件:行号）、改法、依据 |
| SHOULD | 默认遵守 | 偏离需一句理由；理由成立即通过，不计入不通过 |
| MAY | 可选 | 只在项目既有约定要求时检查 |

判定口径：**MUST 命中数 = 0 即通过**。SHOULD 命中只记录理由，不改变结论。

### 1.2 单次检查的固定顺序

| 步 | 动作 | 完成判据 |
|---|---|---|
| 1 | 读函数、调用点、项目既有约定 | 能写出输入域、输出域、错误类型、副作用清单 |
| 2 | 判定语言与公共/内部 | 公共 API 按 MUST 全查；私有函数可略过对外文档与签名要求 |
| 3 | 取指标数字 | 行数、参数个数、嵌套深度、副作用调用、同名 `def` 均有数字 |
| 4 | 按 §2 分组顺序逐条过 29 条 | 每条 MUST 有 ✅/❌ 与证据；SHOULD 有命中理由 |
| 5 | 单独核对错误契约（E1–E6） | 空值与异常的边界在模块内只有一种表达 |
| 6 | 出最小改写 | 只改命中处；不改公共签名语义（除非显式标 BREAKING） |

只改命中处的含义：一次检查不顺手重排无关代码，避免评审噪音掩盖行为变化。

### 1.3 豁免机制

在函数定义上方写一行注释，格式固定：

```python
# std-exempt: 生成的查表函数，行数阈值不适用
def render_table(rows: list[Row]) -> str:
    ...
```

- 理由写给下一位读者看：一句话说明为什么这条规则在此不适用，不写"临时""特殊"这类空话。
- 适用场景：超阈值（生成代码、配置表、扁平解析）、跨语言惯例冲突、第三方接口适配层。
- 豁免只对写明的函数生效，不改变规则级别，也不改变其他函数。
- 豁免理由是评审对象；写不出理由时说明规则成立，按规则处理。

### 1.4 命中表的输出格式

| 字段 | 内容 |
|---|---|
| 规则 | ID + 级别 |
| 证据 | 文件:行号，或 `函数名` |
| 现状 | 一句话描述当前写法 |
| 改法 | 一句话，或 3–8 行最小改写 |
| 依据 | §8 中的一手 URL |

## 2. 分组速查

| 组 | 管什么 | 规则 | 通过判据（一句话） |
|---|---|---|---|
| N 命名 | 名字是否说明"做什么、有没有副作用、贵不贵" | N1–N4 | 只看名字能判断用途与代价 |
| S 签名与参数 | 参数个数、默认值、类型注解、可变参数滥用 | S1–S4 | 调用点读得懂，参数不易调错 |
| R 职责与内聚 | 一个函数是否只做一件事、是否混抽象层 | R1–R4 | 能用一句"做 X 返回 Y"说清 |
| P 纯度与副作用 | 导入期副作用、端口注入、幂等性 | P1–P3 | 纯核心不碰外部世界 |
| E 错误契约 | 空值还是异常、值域哨兵、异常纪律、assert 边界 | E1–E6 | 同类失败在模块内只有一种表达 |
| D 文档 | 摘要、`Args`/`Returns`/`Raises`、注释解释为什么 | D1–D2 | 文档与实现一致 |
| T 类型 | 注解完整度、`Any` 滥用、`Protocol`、TS 形态 | T1–T2 | 公共签名可被静态检查器验证 |
| G 长度与复杂度 | 行数、圈复杂度、嵌套深度 | G1–G2 | 拆分有独立意义，不是凑数字 |
| X 可测试性 | 能否直接单测、性能敏感项有无正确性断言 | X1–X2 | 不启动外部世界也能测 |

## 3. 副作用边界（L0–L3）

规则 R3、R4、P2 依赖统一的分层判据。分层按"函数是否接触外部世界"划分，不按文件或目录划分。

| 层 | 允许什么 | 禁止什么 | 判定方法 |
|---|---|---|---|
| L0 外部世界 | 文件、网络、数据库、CLI、时钟、随机数 | — | 真实的 `open`/`requests`/`now`/`random` 只出现在这一层 |
| L1 端口适配 | 把 L0 包装成可注入的可调用对象；默认真实实现，测试可替换 | 业务判断、数据加工 | 函数签名里能看到端口参数 |
| L2 纯核心 | 输入数据 → 输出数据 | 读环境、看时间、写任何东西、IO | 函数体内无 `open/requests/now/random` |
| L3 编排 | 决定调用顺序与失败处理 | 承载业务数据 | 只调用 L1 与 L2 |

判据：L2 出现 IO = R4 违规；L1 以外的函数体内出现真实的 `open/requests/now/random` = R4 违规。副作用集中到 L0/L1 后，L2 可直接单测（X1），也可安全 benchmark（X2）。

## 4. 规则表（29 条）

| ID | 级别 | 规则 | 出处 | 检查方式 | 反例 |
|---|---|---|---|---|---|
| N1 | MUST | 函数名是动词短语；Python `snake_case`、TS `camelCase`；不用含糊名/单字母（短作用域循环变量除外） | [PEP 8](https://peps.python.org/pep-0008/)、[Google §3.16](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md) | 正则/AST + 评审 | `def state():`、`def run():`、`data`/`tmp` |
| N2 | MUST | 名字暴露副作用与代价：纯查询用 `get_/is_/has_/to_`；有副作用用 `set_/save_/send_/run_`；昂贵用 `load_/fetch_/build_` | [Rust API Guidelines · Naming](https://rust-lang.github.io/api-guidelines/naming.html) C-CONV 的通用形式 | 评审：只看签名能否判断是否 IO、是否昂贵 | `get_user()` 内部发 HTTP |
| N3 | SHOULD | 纯属性不要包 `get_` 访问器（除非取值有代价或有副作用） | [Google §3.15](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md) | 评审 | `get_name()` 仅 `return self._name` |
| N4 | MUST | 不重复定义同名函数；删除无调用方的转发壳 | [PEP 8](https://peps.python.org/pep-0008/)（可读性） | `grep '^def '`；ruff F811 | 两处 `def place()`，最后一份生效 |
| S1 | MUST | 参数 ≤4；布尔开关 ≤1；超出改配置对象/关键字参数 | [Go · Code Review Comments](https://go.dev/wiki/CodeReviewComments)（参数多→长行→难读）、[ESLint · complexity](https://eslint.org/docs/latest/rules/complexity)（同族 `max-params` 可配） | AST 统计 + 评审调用点 | `f(True, False, 3, "x", None)` |
| S2 | MUST | 禁止可变默认参数（`=[]`/`={}`）；需要时函数内创建 | [Google §2.12](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md)（默认参数在定义期求值一次） | AST/正则 | `def f(x, acc=[])` |
| S3 | MUST | 公共 API 参数与返回类型全注解；`__init__ -> None` | [PEP 484](https://peps.python.org/pep-0484/)、[TS Handbook](https://raw.githubusercontent.com/microsoft/TypeScript-Website/v2/packages/documentation/copy/en/handbook-v2/More%20on%20Functions.md)（隐式 any） | mypy/pyright/`tsc --strict` | `def parse(data):` |
| S4 | SHOULD | 不用 `*args/**kwargs` 掩盖公共签名；确需时在 docstring 写清 | [PEP 257](https://peps.python.org/pep-0257/)（记录参数） | 评审 | `def handle(*args, **kw)` |
| R1 | MUST | 单一职责：能用一句"做 X 返回 Y"说清；出现"并/然后"考虑拆 | [Google §3.18](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md) | 评审 + 长度 | 一个函数里"点卡→截屏→标定→查色→拖放→复查" |
| R2 | MUST | 查询与命令分离：只读函数不改状态；有副作用函数名体现且尽量只返回状态 | [Go · Code Review Comments](https://go.dev/wiki/CodeReviewComments)（错误与结果分离同源，CQS） | 评审 | `get_state()` 里偷偷点击屏幕 |
| R3 | SHOULD | 一个函数只操作一个抽象层（解析/计算/IO 不混） | [Google §3.18](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md)；分层切分为团队约定（§3） | 评审：函数体内前缀种类 | `parse()` 里写文件 |
| R4 | MUST | 副作用在边界：L2 纯核心内不得出现 `open/requests/now/random` | [Google §2.5](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md)、[deal](https://github.com/life4/deal)（`@deal.pure` 可验证） | 正则 + 评审 | 纯计算函数里 `datetime.now()` |
| P1 | MUST | 禁止 import 期副作用（读文件/连网/建目录） | [Google §2.5](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md)（导入期改变模块行为） | 评审 + 单测（import 后断言未触碰 FS） | 模块顶层 `templates = load_templates()` |
| P2 | MUST | 副作用通过参数注入（clock/fs/http/random/外部客户端），不直接取全局 | [PEP 544](https://peps.python.org/pep-0544/)（`Protocol` 表达端口） | 评审 | 函数内 `open("config.json")` |
| P3 | SHOULD | 有副作用的函数要幂等或明确写"不可重试" | 团队约定（重试/补偿需要）；一手规范未给幂等要求，参考 [Go · CodeReviewComments](https://go.dev/wiki/CodeReviewComments) 的错误处理原则 | docstring | `send()` 重试导致重复扣款 |
| E1 | MUST | 可预期失败返空值（`T \| None` / `T \| undefined`），不可预期失败抛异常；不混用 | [Go · In-Band Errors](https://go.dev/wiki/CodeReviewComments)、[Google §2.4](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md) | 评审 + 失败路径单测 | 查不到返回 `-1` 又返回 `None` |
| E2 | MUST | 禁止值域哨兵（`-1`/`""`/`"ERROR"`/`False` 冒充失败） | [Go · In-Band Errors](https://go.dev/wiki/CodeReviewComments) | 评审 | `return (1e6, 1e6)` 表示退化 |
| E3 | MUST | 同一模块内失败语义一致；docstring 的 `Raises:` 与实现一致 | [PEP 257](https://peps.python.org/pep-0257/)（记录异常） | 评审 + 测试 | A 返 `None`、B 抛 `KeyError` |
| E4 | MUST | 禁裸 `except:`；只捕能处理的异常；`raise X from Y` 保留因果 | [PEP 8](https://peps.python.org/pep-0008/)、[Google §2.4](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md) | 正则 + ruff BLE | `except: pass` |
| E5 | MUST | `assert` 只用于"删掉也正确"的内部不变量；不校验入参、不做控制流 | [Python 语言参考 · assert](https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement)（`-O` 移除）、[Google §2.4](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md)（判据） | 评审 | `assert minimum >= 1024` 后依赖它分支 |
| E6 | SHOULD | 自定义异常继承最近内建异常、名以 `Error` 结尾、不重复模块名；错误消息精确可 grep 且带出错值 | [PEP 8](https://peps.python.org/pep-0008/)、[Google §2.4](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md) | 评审 | `raise Exception("错误")` |
| D1 | MUST | 公共函数有 docstring；一行摘要用祈使句、不复述签名 | [PEP 257](https://peps.python.org/pep-0257/) | 评审 + pydocstyle | `"""function(a,b) -> list"""` |
| D2 | MUST | 复杂函数写 `Args/Returns/Raises`；生成器写 `Yields`；注释解释"为什么" | [PEP 257](https://peps.python.org/pep-0257/)、[Google §2.9](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md)、[PEP 8](https://peps.python.org/pep-0008/) | 评审 | 有 `Raises` 但没有副作用说明 |
| T1 | MUST | 不用 `Any` 兜底；外部边界用 `object`/`unknown` 并就地收窄；依赖用 `Protocol`/接口表达 | [PEP 484](https://peps.python.org/pep-0484/)、[PEP 544](https://peps.python.org/pep-0544/)、[TS Handbook](https://raw.githubusercontent.com/microsoft/TypeScript-Website/v2/packages/documentation/copy/en/handbook-v2/More%20on%20Functions.md) | 静态检查 | `def f(x: Any) -> Any` |
| T2 | SHOULD | TS 导出函数写显式返回类型；参数显式注解；能用联合类型不用 overload；泛型参数应出现两次 | [TS Handbook](https://raw.githubusercontent.com/microsoft/TypeScript-Website/v2/packages/documentation/copy/en/handbook-v2/More%20on%20Functions.md) | tsc/eslint | `function f(x) { return ... }`（隐式 any） |
| G1 | SHOULD | 函数 ≤50 行（≈40 触发拆分思考）；拆分必须有独立意义 | [Google §3.18](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md)、[ESLint · max-lines-per-function](https://eslint.org/docs/latest/rules/max-lines-per-function) 默认 50、[Go · Code Review Comments](https://go.dev/wiki/CodeReviewComments) 无 N 行规则 | radon/AST | 80 行函数含 5 个职责 |
| G2 | SHOULD | 圈复杂度 ≤10、嵌套 ≤3、单函数返回值语义唯一 | [ESLint · complexity](https://eslint.org/docs/latest/rules/complexity) 默认 20 仅作报警线、[Radon](https://radon.readthedocs.io/en/latest/) | radon cc / eslint | 12 个分支处理同一件事 |
| X1 | MUST | 纯函数可不启动外部世界直接单测；测试名 `test_<函数>_<状态>` | [Google §3.16](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md) | pytest | 测试必须起模拟器 |
| X2 | SHOULD | 性能敏感函数有 benchmark 且 benchmark 内断言正确性 | [pytest-benchmark](https://pytest-benchmark.readthedocs.io/en/latest/) 官方示例 | pytest-benchmark | 只测时间不测结果 |

（29 条：N1–N4、S1–S4、R1–R4、P1–P3、E1–E6、D1–D2、T1–T2、G1–G2、X1–X2）

## 5. 数字阈值与出处

所有数字都是触发线，不是通过线。超线时先看拆分是否有独立意义，再决定"拆"还是"写理由豁免"。

| 指标 | v0 取值 | 规则 | 级别 | 出处 | 取舍说明 |
|---|---|---|---|---|---|
| 函数行数 | ≤50 行 | G1 | SHOULD | [ESLint max-lines-per-function](https://eslint.org/docs/latest/rules/max-lines-per-function) 默认 50 | 工具默认值，可配置，只作报警线。Google：超过约 40 行"考虑拆分"，不设硬上限（[§3.18](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md)）；Go：不存在 N 行规则（[Go](https://go.dev/wiki/CodeReviewComments)） |
| 圈复杂度 | ≤10 | G2 | SHOULD | [ESLint complexity](https://eslint.org/docs/latest/rules/complexity) 默认 20；[Radon](https://radon.readthedocs.io/en/latest/) | 10 是团队折中值，不是一手规范结论；20 只作"明显超标"的参考线 |
| 嵌套深度 | ≤3 | G2 | SHOULD | 团队取值；一手规范未给数字 | 超过 3 层时优先抽取内层函数，而不是加注释 |
| 参数个数 | ≤4 | S1 | MUST | 团队取值；一手来源只论证"参数多损害可读性"（[Go](https://go.dev/wiki/CodeReviewComments)、[ESLint complexity](https://eslint.org/docs/latest/rules/complexity) 同族 `max-params` 可配） | 数字是触发线；判断点是调用点是否出现位置布尔或裸值 |
| 布尔开关 | ≤1 | S1 | MUST | 同上 | 第二个布尔参数即提示拆函数或改配置对象 |

阈值的来源形状：语言标准（PEP）不给数字；企业规范（Google）给"约 40 行考虑拆分"的软提示；工具（ESLint）给可配置默认值。三者都不是硬上限，因此本规范把行数与复杂度定为 SHOULD。

## 6. 误报防守

命中前先排除下列形态。排除不成立时才记为命中；已排除的形态在命中表里写一句"不适用"。

| 规则 | 误报形态 | 确认方式 |
|---|---|---|
| N3（访问器） | 访问器实际有代价或副作用（惰性加载、缓存未命中、触发 IO、顺带校验）；为兼容既有调用点保留 `get_` 形态；属性由框架约定（ORM 字段、序列化器） | 看实现体是否只 `return self._x`；有任一代价即不算违规 |
| S1（参数） | 参数为框架固定签名（视图函数、回调、`__init__` 转发）；全部参数为必填数据字段且有类型注解、以关键字调用；`functools.partial` 固定部分参数后再暴露 | 不看个数看调用点：调用点无 `f(True, False, 3)` 这类位置裸值时才可记说明项 |
| E1（两类失败） | 函数是薄封装，把两类失败原样上抛；返回语义由协议约定（映射的 `get` 未命中即 `None`）；`None` 是合法业务值而失败另有异常 | 看 docstring 是否写清 `None` 的含义；两种失败无法区分才算违规 |
| D1（文档串） | 私有函数（`_` 前缀）且 7–10 行一目了然；`@overload` 声明无实现体；测试函数；自动生成的协议桩 | 规则只约束公共函数；私有函数与声明体不查 |
| T1（`Any`） | `Any` 从第三方库签名不可避免地向内传播；类型存根（`.pyi`）为兼容而放宽；`@overload` 声明 | 本函数自身签名不得以 `Any` 兜底；入口处未收窄才算违规 |
| G1/G2 | 长但线性的代码（配置表、扁平解析、生成代码）；分支多但每个分支一行映射；拆分会破坏内聚 | 能否给出"有独立意义"的拆分；不能则记超线说明，不判缺陷 |
| N1（命名） | 语言/框架强制名（`__init__`、`setUp`、被覆盖的协议方法）；领域内已经名词化的动词；测试名（由 X1 约定） | 强制名不查 N1；其余按语义判断 |

## 7. 语言差异（同一 ID，不强行统一）

| 维度 | Python | TypeScript | 同 ID 处理 |
|---|---|---|---|
| 命名 | `lower_with_under`；`get_foo()` 合法（[Google §3.15](https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md)） | `camelCase`；访问器用 `get`/`set` 或属性；无 `get_` 前缀惯例 | N1/N3 分语言判断 |
| 空值 | `T \| None`（`Optional[T]`） | `T \| undefined`；前提是开启 `strictNullChecks` | E1 同语义、不同写法 |
| 失败 | 抛异常；转换异常用 `raise X from Y` | 抛 `Error` 子类；`never` 返回类型标记"必然抛出"（[TS Handbook](https://raw.githubusercontent.com/microsoft/TypeScript-Website/v2/packages/documentation/copy/en/handbook-v2/More%20on%20Functions.md)） | E1/E4 同语义 |
| 依赖注入 | `Protocol` + 默认参数（[PEP 544](https://peps.python.org/pep-0544/)） | 接口 + 构造注入 | P2/T1 同思想 |
| 文档 | docstring（[PEP 257](https://peps.python.org/pep-0257/) / Google 风格） | TSDoc/JSDoc；本规范 29 条不引用其细则 | D1/D2 在 TS 侧降为评审项 |
| 阈值 | 50 行 / CC 10 | 同左 | 工具分别为 radon 与 eslint |
| 工具 | ruff、mypy、pydocstyle、radon | `tsc --strict`、typescript-eslint | 工具缺失时降级为评审，不改变级别 |

TS 落地状态（须在报告中标明）：

| 项 | 状态 | 处理 |
|---|---|---|
| T2（TS 专属） | SHOULD，判定依赖 tsc/eslint | 环境无 `tsc --strict` 与 typescript-eslint 时记为"待工具"，不判 FAIL |
| S3、T1 的 TS 分支 | 依赖静态检查器 | 无工具时人工核对签名，只判"有无显式注解/是否 `Any` 兜底" |
| N1 的 `camelCase` 分支 | 可用正则检查 | 与 Python 分支分开报告 |
| D1/D2 | TS 侧无 TSDoc 一手来源 | 只按评审建议处理并在报告中注明来源缺失；规则级别不变 |

## 8. 出处清单

| 标签 | 规范/文档 | 一手 URL | 覆盖规则 |
|---|---|---|---|
| PEP 8 | PEP 8 – Style Guide for Python Code | https://peps.python.org/pep-0008/ | N1、N4、E4、E6、D2 |
| PEP 257 | PEP 257 – Docstring Conventions | https://peps.python.org/pep-0257/ | S4、E3、D1、D2 |
| PEP 484 | PEP 484 – Type Hints | https://peps.python.org/pep-0484/ | S3、T1 |
| PEP 544 | PEP 544 – Protocols | https://peps.python.org/pep-0544/ | P2、T1 |
| Google | Google Python Style Guide（官方仓库 `pyguide.md` 源文件） | https://raw.githubusercontent.com/google/styleguide/gh-pages/pyguide.md | N1、N3、S2、R1、R3、R4、P1、E1、E4、E5、E6、D2、G1、X1 |
| Go | Go Code Review Comments | https://go.dev/wiki/CodeReviewComments | S1、R2、E1、E2、G1、P3（参考） |
| Rust Naming | Rust API Guidelines · Naming | https://rust-lang.github.io/api-guidelines/naming.html | N2 |
| TS Handbook | TypeScript Handbook · More on Functions（官方仓库 markdown） | https://raw.githubusercontent.com/microsoft/TypeScript-Website/v2/packages/documentation/copy/en/handbook-v2/More%20on%20Functions.md | S3、T1、T2 |
| ESLint complexity | ESLint · complexity rule | https://eslint.org/docs/latest/rules/complexity | S1、G2 |
| ESLint max-lines | ESLint · max-lines-per-function | https://eslint.org/docs/latest/rules/max-lines-per-function | G1 |
| assert | Python 语言参考 · The assert statement | https://docs.python.org/3/reference/simple_stmts.html#the-assert-statement | E5 |
| deal | deal（Design by Contract for Python）官方仓库 | https://github.com/life4/deal | R4、契约 L3（见 error-contract.md） |
| Radon | Radon 文档（CC / MI） | https://radon.readthedocs.io/en/latest/ | G2 |
| pytest-benchmark | pytest-benchmark 文档 | https://pytest-benchmark.readthedocs.io/en/latest/ | X2 |
| pydantic | Pydantic Validation · Validators | https://pydantic.dev/docs/validation/latest/concepts/validators/ | 契约 L2（见 error-contract.md） |

说明：Google 与 TS 两处使用官方仓库的源文件作为可抓取的稳定地址；引用时以规范名 + 小节号定位，不以 URL 片段定位。

## 9. 诚实注记

以下是规则表里"级别高于一手来源强度"的部分，评审与对外报告必须照此说明，不得把团队选择说成语言标准。

| 项 | 事实 | 对检查的影响 |
|---|---|---|
| D1、D2 的 MUST | PEP 257 的原文用 "should"（建议）表述，不是语言强制；把公共 API 的文档字符串定为 MUST 是团队选择 | 评审本团队代码按 MUST 计；评审外部或第三方代码按 SHOULD 处理 |
| G1、G2 的 SHOULD | 50 行来自 ESLint 工具默认值（可配置）；Google 的"约 40 行"是考虑拆分的触发点，不是上限；CC 10 是团队折中（ESLint 默认 20）；嵌套 3 无一手来源 | 超线写一句理由即通过，不阻断；不得用"行业标准"描述这些数字 |
| S1 的数字 | "≤4 个参数、≤1 个布尔开关"是团队取值；一手来源只论证参数多损害可读性，不给数字 | 数字是触发线；判断点是调用点是否出现位置布尔或裸值 |
| N2 的前缀表 | 把 Rust 的 `as_/to_/into_` 代价编码迁移到 Python/TS 是团队做法；Python 生态无同构官方惯例 | 评审用，不阻断；与 N3 冲突时以 N3 为准（Python 用 `get_` 合法） |
| R2 的出处 | 查询与命令分离（CQS）本身不在一手规范中；本规范的表述与 Go 的"错误与结果分离"同源 | 评审用；报告中写"同源"而不是"引自" |
| R3 的分层 | §3 的 L0–L3 切分是团队约定，无一手规范给出同名分层 | 分层判据按 §3；R3 用于发现解析/计算/IO 混合 |
| P3 的幂等 | 团队约定，无一手规范 | 只查 docstring 是否写明可重试性，不查实现 |
| X1 的测试名 | `test_<函数>_<状态>` 取自 Google 的命名小节；"不启动外部世界即可测"是设计判据，不是命名约定 | 命名用自动检查，可测性用评审 |

## 10. 附录 A：反例库（按组）

反例取自真实的函数级缺陷形态。每条给出最小改法，改法只动命中处，不顺手重排无关代码。

| 组 | 反例 | 最小改法 | 命中 |
|---|---|---|---|
| N | `def run():`、`def state():` | 换成动词短语并写清对象：`def run_checks():`、`def get_state():` | N1 |
| N | `def get_user()` 内部发 HTTP | 改名为 `fetch_user()`；或将 IO 移到端口，`get_user()` 只读本地数据 | N2、N3 |
| N | 同一文件两处 `def place()`，前一份是死代码 | 删死代码，保留一份；转发壳合并到真实现 | N4 |
| S | `render(x, True, False, None, 3)` | 布尔开关改策略或配置对象：`render(x, options=RenderOptions(...))` | S1 |
| S | `def f(x, acc=[])` | `def f(x, acc: list \| None = None)`，函数体内 `acc = [] if acc is None else acc` | S2 |
| S | `def parse(data):` | `def parse(data: bytes) -> Config:`，`__init__` 标 `-> None` | S3 |
| R | 一个函数完成"读文件→解析→计算→写文件" | 拆为 `read_rows()` / `parse_rows()` / `compute()`，IO 留在边界层 | R1、R3、R4 |
| R | `get_state()` 里顺手点击屏幕 | 查询函数只读；动作拆到 `click_screen()`，名字体现副作用 | R2 |
| P | 模块顶层 `templates = load_templates()` | 改为惰性函数 `get_templates()`，由入口显式初始化 | P1 |
| P | 函数内 `open("config.json")` | 配置对象从参数注入；测试传假配置 | P2 |
| E | 查不到 `return -1`，参数错 `return None` | 查不到 `return None`；参数错 `raise ValueError` | E1、E2 |
| E | `except: pass` | `except json.JSONDecodeError as exc: raise ValueError(...) from exc` | E4 |
| E | `assert value >= 1024` | `if value < 1024: raise ValueError(f"capacity too small: {value!r}")` | E5 |
| D | `"""Get data."""` 但函数写文件 | 摘要写实际行为与副作用：`"""Write normalized rows to out_path."""` | D1、D2 |
| T | `def f(x: Any) -> Any` | `def f(x: object) -> Config:`，入口处收窄为具体类型 | T1 |
| G | 80 行、12 个分支的单函数 | 按"能单独命名、单独测试"拆成 3 个函数；拆不动则写一行超线理由 | G1、G2 |
| X | 测试必须启动模拟器才能跑 | 把 IO 注入为参数后，对纯核心直接传假数据 | X1 |

## 11. 附录 B：检查方式与工具降级

工具缺失不改变规则级别，只改变证据形态：从工具输出改为人工判据 + 行号引用。报告中注明用了哪一种证据。

| 规则 | 有工具时 | 零新增依赖时的替代判据 | 工具缺失时 |
|---|---|---|---|
| N1、N4 | ruff（`N`、`F811`） | `grep '^def '` 查同名；正则查命名形态 | 人工评审 |
| S1、S2 | ruff/AST 脚本 | `ast` 统计参数个数、默认值是否 `list/dict/set` | 人工评审 |
| S3、T1、T2 | mypy / pyright / `tsc --strict` | 读签名：参数与返回有无注解、有无 `Any` 兜底 | 人工评审 |
| R2、R3、R4、P1、P2 | AST 脚本（搜 `open(`、`requests.`、`datetime.now(`、`random.`） | 同左，零依赖可实现 | 人工评审 |
| E1、E2、E3、E4 | 正则（`except:`、`return -1`）+ 失败路径测试 | 同左；失败路径测试用 pytest | 人工评审 |
| E5（assert 边界） | 正则 `assert ` | 人工判"删掉 assert 后代码是否仍正确" | 人工评审 |
| E6（异常类型与消息） | 命名正则 + 消息文本检查 | 人工读 `raise` 语句 | 人工评审 |
| D1、D2 | pydocstyle / ruff `D` | 人工比对 docstring 与实现 | 人工评审 |
| G1、G2 | radon（cc / mi）、eslint（`complexity`、`max-lines-per-function`） | `ast` 统计行数与分支数（`if/elif/for/while/except/and/or`） | 人工评审 |
| X1、X2 | pytest、pytest-benchmark | pytest 内建；benchmark 用 `time.perf_counter` 手工计时 | 人工评审 |

降级的写法要求：每条命中仍必须给规则 ID、证据（文件:行号）、改法与依据 URL；不得因"没有工具"而降低级别或省略依据。
