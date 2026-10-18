# 性能剖析手册（profiling playbook）

> 用途：取证步骤「复杂度/热点」。目标：把「整体慢」压到**函数 → 调用点 → 代码行 → 循环**，产出可复现的相对证据。
> 判据：每条热点结论都带工具、命令、统计/采样口径、文件行号；没有行号的结论不进报告。

## 1. 工具选择

| 工具 | 观测对象 | 开销 | 适用 | 不适用 |
|---|---|---|---|---|
| cProfile | 每个函数的调用次数、tottime/cumtime（确定性插桩） | 高：逐调用插桩，放大调用密集代码 | 开发期、可复现脚本、函数级全貌与调用关系 | 长驻进程、线上、毫秒级微基准、绝对耗时结论 |
| py-spy | 运行中进程的栈采样（默认 100 Hz） | 低：外部采样，可不改代码 | 长驻/线上、卡死进程、无法改代码的场景 | 极短脚本（样本不足）、需要精确调用次数 |
| `python -X importtime` | 每条 import 的自耗时/累计耗时 | 无（解释器内建） | 启动慢、CLI 冷启动、测试收集慢 | 运行期热点、函数内部 |
| `timeit` / `perf_counter` | 指定语句或代码块的墙钟时间 | 低，但受测量方式影响 | 微基准、优化前后对比、验证收益 | 找热点（还不知道测哪）、跨机器绝对时间 |
| `tracemalloc` | Python 对象分配点（文件:行）与峰值 | 高：记录每次分配 | 内存增长、泄漏、峰值定位 | 原生扩展内存、CPU 热点 |
| `line_profiler`（第三方） | 函数内逐行耗时 | 高 | 行级定位、循环体内部 | 未安装环境、长驻进程 |

缺工具时的降级路径见 §9；降级必须在报告里写明「未做采样/未出火焰图」。

## 2. cProfile 配方

```bash
# 直接跑，按累计时间排序
python -m cProfile -s cumtime script.py | head -30

# 落盘再分析：一次采集，多次排序（推荐）
python -m cProfile -o out.prof script.py
python -c "import pstats; pstats.Stats('out.prof').strip_dirs().sort_stats('cumtime').print_stats(20)"
python -c "import pstats; pstats.Stats('out.prof').strip_dirs().sort_stats('tottime').print_stats(20)"
```

| 列 | 含义 | 判据 |
|---|---|---|
| ncalls | 调用次数；递归显示为 `总次数/原语次数`（如 `100/1`） | 次数异常高 → 调用点放错（循环内）或重复计算 |
| tottime | 本函数自身耗时，不含子调用 | 按 tottime 排第一 = 真热点函数 |
| percall（第 1 列） | tottime / ncalls | 单次很贵 → 算法/IO 问题；次数很多 → 调用点问题 |
| cumtime | 含全部子调用的累计耗时 | 按 cumtime 排第一 = 热点子树入口，不一定是自身热点 |
| percall（第 2 列） | cumtime / 原语调用次数 | 递归、外层包装函数看这一列 |

- `print_callers('func')` 找**热点调用点**（谁在调它）；`print_callees('func')` 沿 cumtime 下钻（它调了谁）。
- 同一函数被多处调用时，热度通常集中在**一个调用点**；先看 callers，再决定改函数还是改调用方。
- 降噪：`strip_dirs()` 缩短路径，`print_stats(20)` 只看头部 20 条；报告只引用与自己代码相关的帧。
- **只用于相对定位**。插桩开销随调用次数放大，会系统性高估「短小高频」函数、低估 I/O 与 C 扩展；绝对耗时以 §8 的计时口径为准。

## 3. py-spy 配方

```bash
py-spy top --pid 12345                        # 实时热榜，边跑边找目标
py-spy record -o profile.svg --pid 12345      # 采样落盘，产出火焰图
py-spy dump --pid 12345                       # 抓一次栈：卡死/挂起时看卡在哪
py-spy record -o profile.svg --pid 12345 --rate 200 --native
py-spy record -o profile.svg --pid 12345 --subprocesses
py-spy record -o profile.svg -- python script.py   # 由 py-spy 启动并采样
```

| 参数 | 作用 | 注意 |
|---|---|---|
| `--pid` | 指定目标进程 | pid 变化后需重取，服务重启即失效 |
| `--rate N` | 采样频率（默认 100 次/秒） | 窗口短就调高；过高会引入观测开销 |
| `--native` | 附带 C/原生帧 | 缺调试符号时栈会断，结论只到 Python 帧 |
| `--subprocesses` | 同时采样子进程（record） | worker 池、`multiprocessing` 必加 |
| `--idle` | 记录空闲线程 | 看阻塞/等待时用；默认只采运行中线程 |
| `--gil` | 标注 GIL 状态 | 判断多线程是否被 GIL 卡住；版本差异以 `--help` 为准 |
| `top` / `record` / `dump` | 滚动热榜 / 固化火焰图 / 单次抓栈 | top 找目标，record 出证据，dump 回答「现在卡在哪」 |

权限差异：

- Linux：ptrace 默认只允许同 UID 的父子进程；他人或常驻进程用 `sudo py-spy ...`，或 `sudo setcap cap_sys_ptrace+ep $(command -v py-spy)`；容器内需 `--cap-add SYS_PTRACE`（或 `--pid=host`）。
- Windows：以管理员运行，或保证与目标进程同用户、同会话；服务、计划任务、提权进程通常必须管理员。
- 常见报错：`Permission denied`（权限）、`No such process`（pid 已退出）、`Failed to find python version`（嵌入式/精简解释器）。

降级：无 py-spy 时用 cProfile（离线入口）+ 手工 `perf_counter` 分段计时，报告标注「无采样、无火焰图，仅函数级/粗粒度证据」。

## 4. 火焰图读法

- **宽度 = 样本占比**（≈ CPU 时间占比），不是调用次数；同一函数出现在多个调用点要合并宽度看。
- **x 轴按栈字典序排列，不是时间轴**；从左到右读不出执行先后。
- **y 轴是调用栈深度**，自下而上 caller → callee；底部是根，越靠上越接近叶子。
- **自身时间（self）**：块下方没有子帧的部分。self 宽而深的叶子是热点本体；整体宽但下方很快收窄，说明贵在其子函数。
- **看不到的**：off-CPU 时间（I/O 等待、锁等待、sleep、原生阻塞）默认不进采样。不能用火焰图断言「不是 I/O 问题」；要阻塞证据用 `--idle`、`dump` 或手工计时。
- **record 与 top 分工**：top 找目标函数与占比；record 固化证据、看调用栈归属（同一函数被哪些路径调用）。
- SVG 可直接搜索函数名；报告引用写清「函数 + 占比 + 采样率 + 采集命令」。

## 5. 从热点到代码行

1. **两遍排序**：先按 cumtime 找子树入口，再按 tottime 找自身耗时；两个第一名不同是常态，先修 tottime 高的那个。
2. **看 per-call**：单次耗时异常（毫秒级）多是算法或 IO；次数异常（10⁶ 级）多是循环内调用。
3. **看调用点**：用 `print_callers` 或火焰图上层帧确认热度来自哪个循环/路径；热点函数 ≠ 热点调用点。
4. **进函数内部**：有 line_profiler 时 `kernprof -l -v script.py`（目标函数加 `@profile`）拿逐行耗时；没有则在函数中段插 `perf_counter()` 二分，先分前后半，再二分到循环体。
5. **确认量级**：对候选行做微基准（`timeit`，同数据、同环境），并测 2–3 个输入规模算增长比；比值接近 n² 才是平方级，接近 n·log n 是排序/分治。
6. **写回证据**：文件:行号、数据结构与规模、优化前后同一基准的 median/IQR、正确性回归命令。

## 6. 隐藏平方与反模式

| 写法 | 症状 | 复杂度 | 改法 |
|---|---|---|---|
| 循环内 `x in some_list` | 次数高、单次便宜 | O(n·m) | 先建 `set`/`dict`，再判断成员 |
| 同一集合双层 `for` | 规模 ×2、时间 ×4 | O(n²) | `dict` 分组、排序 + 双指针、`Counter` |
| 循环内 `sorted(...)` | 内层函数 cumtime 占比高 | O(n² log n) | 排序移到循环外，循环内用 `bisect` |
| 循环内 `s += piece` | 字符串越长越慢 | O(n²) | 收集到 list，最后 `"".join(...)` |
| `list.insert(0, x)` / `pop(0)` | 列表越长越慢 | O(n²) | `append` + 收尾 `reverse`，或 `collections.deque` |
| 热路径 `copy.deepcopy` | 深拷贝整个对象图 | 视结构 | 只复制必要字段；用不可变数据或 `copy.copy` |
| 不可信正则 `(a+)+$` | 特定输入指数爆炸 | 指数 | 收紧量词、锚定、避免嵌套量词、限制输入长度 |
| 循环内重算不变量 | 次数高、常数放大 | 常数 | `len()`、属性链、`re.compile`、`datetime.now()` 提到循环外 |
| 循环内重复 `open`/`json.loads`/读配置 | I/O 次数 = 循环次数 | O(n)·IO | 一次读入内存，循环内只处理对象 |
| N+1 查询、逐行 `.apply`/`iterrows()` | 外部调用次数爆炸 | O(n)·RTT | 批量查询、`merge`、向量化、`executemany` |
| 循环内重建容器、`list(d.keys())` | 分配次数高 | 常数/平方放大 | 容器提到循环外复用；直接 `in dict` |
| 为求极值在循环内建大列表 | 峰值内存高、GC 抖动 | O(n) 但常数大 | `min`/`max`/生成器/`heapq.nlargest` |
| 循环内 `list.index`/`list.remove` | 每次线性扫描 | O(n²) | `dict` 存位置、标记删除后重建一次 |

判据：命中任一行先写固定规模的复现脚本，再用 §5 的规模增长比确认；不靠「看起来像」。

## 7. 优化手法与风险

| 手法 | 用法 | 风险/边界 |
|---|---|---|
| `set`/`dict`/`Counter` | 成员判断、去重、计数 | 元素须可哈希；额外内存；要保序用 `dict` |
| 一次排序 + `bisect`/双指针 | 替代循环内查找与嵌套匹配 | 数据变动后必须重排 |
| `heapq.nlargest/nsmallest` | top-k，k 远小于 n | k 接近 n 时不如直接 `sorted` |
| 前缀和/差分 | 区间求和、滑窗 | 只适用可加聚合，不适用 min/max |
| 批量 I/O、`executemany`、`merge` | 减少往返次数 | 受事务/内存上限约束，失败重试粒度变粗 |
| `"".join`、列表收集 | 字符串/序列拼接 | 峰值内存升高 |
| 局部变量、绑定方法名 | 减少属性查找 | 可读性下降，收益通常很小，先测再留 |
| 提前退出/短路 | 命中即返回 | 不得改变统计副作用与语义 |
| `functools.lru_cache` | 纯函数重复计算 | 参数须可哈希；可变参数导致陈旧结果；无界缓存吃内存；命中率低时更慢；须给 `maxsize` 与失效策略 |
| 换数据结构/算法 | 降低复杂度 | 改动最大，须配正确性四件套与契约零变更证据 |

原则：先降复杂度，再降常数；一次只改一个点，保留优化前基准；收益不显著就回滚并写「放弃」。

## 8. 测量陷阱

| 陷阱 | 现象 | 处理 |
|---|---|---|
| profiler 开销改变相对成本 | 短函数被高估、I/O 被低估 | profiler 只做排序；绝对耗时用独立基准 |
| 调试/断言开启 | 变慢幅度取决于断言密度，可能掩盖真实占比 | 固定是否 `python -O`，报告写明 |
| import 冷启动 | 首次显著偏慢 | 冷/热分开测，`-X importtime` 定位 |
| 缓存与热数据 | 第二遍明显变快 | 声明冷/热口径；统一预热或每轮清缓存 |
| GC 与内存分配 | 抖动、长尾 | `tracemalloc` 记峰值；必要时对比 `gc.disable()` |
| CPU 频率/turbo/降频 | 同代码多次差 10%+ | 固定电源策略，多轮取中位数并看离散度 |
| 虚拟机/容器噪声 | 邻居负载、CPU 配额 | 同机同配额对比，报告声明环境 |
| Windows 计时 | `time.time()` 分辨率粗 | 用 `time.perf_counter()`/`perf_counter_ns()` |
| 后台负载 | 单次不可复现 | 关后台任务；≥5 次取 median，报 IQR |
| 测量本身的开销 | 循环内插桩改变被测代码 | 计时点放循环外，测整段而非单次 |

口径：每个结论至少 5 次重复，给 median 与 IQR（或 min–max）；跨机只做同环境相对结论。

## 9. 决策表

| 场景 | 首选 | 缺工具时降级 |
|---|---|---|
| 可复现脚本变慢 | cProfile：cumtime → tottime → callers | 手工分段 `perf_counter` + 规模增长比 |
| 长驻服务/线上、不能改代码 | py-spy `top` / `record --pid` | 用离线入口跑 cProfile + 日志计时；注明无采样 |
| 进程卡死/挂起 | py-spy `dump` | `faulthandler.dump_traceback_later()` 或信号打印栈 |
| CLI/测试启动慢 | `python -X importtime` | 入口前后 `perf_counter`，二分 import 段 |
| 怀疑某语句/表达式 | `timeit`（固定 setup 与次数） | 循环 N 次 `perf_counter`，扣空循环基线 |
| 内存增长/泄漏 | `tracemalloc` 快照对比 | `sys.getsizeof` + 对象计数、`gc` 统计、RSS |
| 行级热点 | `line_profiler`（`kernprof -l -v`） | 手工二分插桩 + 微基准复现 |
| 多线程是否被 GIL 卡住 | py-spy `--gil` | 单/多线程墙钟对比 + 线程内打点 |
| 多进程 worker 慢 | py-spy `--subprocesses` | 每个 worker 单独 cProfile 落盘 |

## 10. 参考来源

- Python 官方文档 · `profile` / `cProfile` / `pstats`：https://docs.python.org/3/library/profile.html
- Python 官方文档 · `timeit`：https://docs.python.org/3/library/timeit.html
- Python 官方文档 · `tracemalloc`：https://docs.python.org/3/library/tracemalloc.html
- Python 官方文档 · 命令行 `-X`（含 `importtime`、`tracemalloc`）：https://docs.python.org/3/using/cmdline.html#cmdoption-X
- Python 官方文档 · `time.perf_counter`：https://docs.python.org/3/library/time.html#time.perf_counter
- py-spy 官方 README：https://github.com/benfred/py-spy
- Brendan Gregg · Flame Graphs：https://www.brendangregg.com/flamegraphs.html
- line_profiler 官方仓库：https://github.com/pyutils/line_profiler
