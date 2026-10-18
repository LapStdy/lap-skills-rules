# 复杂度与回归门禁（complexity-and-gates）

本文件回答两件事：**复杂度怎么用数据判定**，以及**性能基线怎么变成可持续的门禁**。配套脚本：`scripts/bench_stats.py`；模板：`templates/bench.py`。

## 1. 规模曲线：用数据判复杂度

### 1.1 取点

- 至少 4 个规模点，按 **n 翻倍**取：`100 / 200 / 400 / 800`（或真实调用分布附近的点）。
- 每个规模点重复 ≥5 次（建议 10 次），丢 warmup，取 **median**；同时记 IQR。
- 输入必须由同一构造器生成，只变规模，不变数据形状（例如同时有随机/有序/全重复三种形状时分开测）。
- 计时范围只包含被测逻辑：排除数据构造、import、打印、磁盘 I/O；构造放计时外。

### 1.2 读曲线

n 翻倍时的时间比：

| 时间比 t(2n)/t(n) | 结论 | 备注 |
|---|---|---|
| ≈1 | O(1) 或常数主导 | 小 n 常被解释器开销淹没 |
| ≈2 | O(n) | 最常见的线性 |
| ≈2.1–2.5 | O(n log n) 或线性 + 高常数 | 在常见 n 下 log 项不显著，别过度解读 |
| ≈4 | O(n²) | 隐藏平方的典型信号 |
| ≈8 | O(n³) | 三重循环 |

辅助斜率：`k = log(t2 / t1) / log(n2 / n1)`，对每对相邻点算一次，看 k 是否稳定。k 随 n 增大而趋近理论值；前几个点偏小通常是常数项，别用它们下结论。

**结论写法**：`n=100/200/400/800 → median 1.2/4.9/20.1/81.4 ms，翻倍比≈4，斜率 k≈2.0 → O(n²)`。只写「O(n²)」而没有数据，不算完成。

### 1.3 拟合与陷阱

- 两参数模型 `t = a·n^k + b` 比单看最后两点稳；至少要求 k 在相邻点间同号且量级一致。
- 拟合质量差（R² 低）先查：缓存效应、GC、输入形状变化、超时/限流、后台负载。
- **不要**用 profiler 的累计时间代替规模曲线：profiler 开销会改变相对成本。
- 小 n 的固定开销（函数调用、属性查找、异常）会掩盖渐近项；结论要写清适用区间。
- 复杂度是上界描述，不是性能结论：同是 O(n log n)，常数差 10 倍也常见；先定复杂度，再谈优化收益。
- 算法有分支时按分支分别画曲线（如「全部唯一 / 全部重复」），不要混在一起求平均。

### 1.4 内存复杂度

- 用 `tracemalloc`：`start()` → 调用 → `get_traced_memory()[1]`（peak）→ `stop()`；同样画 peak 随 n 的曲线。
- 优化常把 CPU 换成内存（缓存、索引、预计算），必须同时报 peak 变化；内存涨 10 倍换 20% 提速通常不接受。
- 区分「峰值」与「稳态」：缓存类改动看稳态，批处理看峰值。

## 2. 基线：什么才算证据

一条基线至少包含：**环境 + 命令 + 输入 + 样本数 + median + IQR**。

```text
env: CPython 3.14.3 / Windows-11 / <CPU> / pytest-benchmark 5.3.0
cmd: python -m pytest tests/bench_find_duplicates.py --benchmark-only
input: n=400, random ints in [0, 200)
n=30  median=18.42 ms  IQR=0.61 ms  rel-IQR=3.3%
```

- 单次 `time.time()`、不写样本数、只报最好一次，都不算基线。
- 相对 IQR（`IQR/median`）>10% 说明噪声大：先查后台负载/GC/热降频，或增加样本；不要直接下结论。
- warmup 必须丢弃：首次调用包含 import、缓存冷、解释器预热。
- A/B 要**交错**执行（A,B,A,B…）再各自取 median，避免机器随时间的漂移被误判成改动效果。

## 3. 回归门禁：把基线变成 0/1

### 3.1 判定规则

默认规则（与 `scripts/bench_stats.py compare` 一致）：

```text
delta = candidate.median / baseline.median - 1
regression = (delta > threshold) AND (candidate.median - baseline.median > baseline.iqr)
threshold 默认 0.10（10%）
```

- **双条件**：只超 10% 但差异还在基线 IQR 内 → 证据不足，不失败；只超 IQR 但幅度 <10% → 视为噪声内的小漂移。
- 阈值按函数成本与业务敏感度调整：热路径 5–10%，冷路径不设硬门禁。
- 判定要写清用的是哪个基线文件、哪台机器、哪个输入规模。

### 3.2 噪声地板与最小可检测效应

- 先做「同一份代码跑两次」的对照：两次 median 的差异就是噪声地板。门禁阈值必须大于噪声地板。
- 最小可检测效应（MDE）≈ 噪声地板 × 2；比 MDE 小的改动不值得声称有收益。
- 噪声大的环境（共享 CI、笔记本省电模式、虚拟化）只出趋势，不设硬门禁。
- 连续多轮都朝同一方向偏移才叫趋势；单轮波动不叫回归。

### 3.3 CI 设计

| 场景 | 做法 |
|---|---|
| 专用性能 runner（固定机器） | 可设硬门禁：`--benchmark-compare-fail=median:10%` 或 `bench_stats.py compare` |
| 共享 CI runner | 只采集、出趋势；硬门禁会因邻居负载误报 |
| 本地开发 | 只做前后对比，不阻塞合并 |
| 跨机器 | 不直接比绝对时间；比同机相对变化、或按机器分基线文件 |

- 基线文件按「机器 + Python 版本 + 关键依赖」分文件，例如 `.benchmarks/baseline-win11-py314.json`。
- 候选与基线必须同环境；环境不一致时 `bench_stats.py compare` 会警告，结论降级为「参考」。
- flaky 处理：同一提交重跑 2–3 次取中位数再判；仍抖动则降低门禁严格度并记录原因。
- 绝对耗时阈值（如「必须 <10 ms」）不进 CI：换机器就失效；它属于 SLO/产品指标，不属于代码门禁。

## 4. 基线生命周期

1. **建立**：优化完成且证据齐全后，保存基线（`pytest-benchmark --benchmark-save` 或 `bench_stats.py --json-out`）。
2. **入库**：基线文件进仓库（或专用存储），带环境字段与生成命令。
3. **更新**：只在显式动作里更新（依赖升级、算法替换、机器更换），并在 changelog 写日期、原因、前后 median。
4. **退役**：环境不再维护时删除或归档；不保留无法复现的旧基线。
5. **所有权**：基线属于代码库，不属于某个人；PR 里改基线必须单独说明理由。

## 5. 什么时候不要设门禁

- 函数不在热路径、调用频次低、总耗时占比 <1%：优化收益小于维护成本。
- 输入分布不稳定、依赖外部服务/磁盘：先解决可复现性，再谈门禁。
- 团队还没有稳定 runner：先积累 2–4 周趋势数据，再定阈值。
- 门禁引发频繁误报且无法解释：退化为「提醒」而不是「失败」。

## 6. 与工具的分工

| 工具 | 用途 | 注意 |
|---|---|---|
| `scripts/bench_stats.py` | 无 pytest-benchmark 时的采样 + JSON 基线 + compare | 子进程/进程内计时，噪声大于专用 benchmark 插件 |
| `pytest-benchmark` | 回归测试内的基准、校准、保存/对比 | 仍需正确性断言；不要只跑基准不跑功能测试 |
| `asv` | 多版本/多参数历史趋势 | 重；本机未装时写「未做」 |
| `tracemalloc` | 内存 peak 曲线 | 只测 Python 对象分配，不含 C 扩展内部内存 |

## 7. 最小交付清单

- [ ] 规模点表（n、median、IQR、样本数）与斜率结论
- [ ] 基线 JSON 或 pytest-benchmark 存储路径，含环境字段
- [ ] 门禁规则写清（阈值 + IQR 双条件、适用机器、输入规模）
- [ ] 噪声地板/MDE 的实测值或明确「未做」
- [ ] 基线更新策略与 changelog 位置

## 参考来源

- Python `time.perf_counter` / `tracemalloc` 文档：https://docs.python.org/3/library/time.html 、https://docs.python.org/3/library/tracemalloc.html
- pytest-benchmark 文档：https://pytest-benchmark.readthedocs.io/
- asv 文档：https://asv.readthedocs.io/
- Brendan Gregg, «Flame Graphs»：https://www.brendangregg.com/flamegraphs.html
- Nickolas Means 等关于微基准噪声的讨论仅作背景，不引用具体数字；所有阈值以本机实测噪声地板为准。
