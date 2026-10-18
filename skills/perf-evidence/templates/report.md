# 性能取证报告 · <函数/入口>

> 模板：复制后把尖括号 `<...>` 全部替换；没有测量的结论不写；无收益就写「无可证收益，放弃」。
> 证据口径：同环境、≥5 次、median/IQR/样本数齐全，单次 `time.time()` 不算通过。

- 日期：<YYYY-MM-DD>
- 负责人：<name>
- 目标函数/入口：`<module.py>::<function>`（commit `<sha>`）
- 触发场景：<用户原话 / issue / PR 链接>
- 结论摘要：<达标 -x% / 未达标 / 放弃>

## 1. 目标

- 可测目标：<例如 find_duplicates 在 n=400 时 median 从 12 ms 降到 ≤ 2 ms>
- 非目标（明确排除）：<例如 不改变返回顺序、不改公共签名、不动调用方>
- 成功判据：<median 降幅 ≥ x% 且正确性四件套齐全；写不出可测判据就说明还不该开工>

## 2. 环境

| 项 | 值 |
|---|---|
| 机器 / CPU | <...> |
| 内存 / 核心数 | <...> / <n> |
| OS / 平台 | <...> |
| Python | <3.14.x> |
| 关键依赖版本 | <零依赖 / pytest-benchmark x.y> |
| 测量时间（UTC） | <...> |
| 同环境声明 | <前后数据在同一机器、同一解释器、同一负载下采；差异项显式列出> |

## 3. 复现命令

```bash
# 基线（exec：进程内单次调用；也可换 run 跑子进程）
python skills/perf-evidence/scripts/bench_stats.py exec \
  --target <path.py>:<func> --args-json '[[400]]' --warmup 2 --repeat 10 \
  --label before --json-out <evidence-dir>/before.json

# 新旧实现正确性差分
python skills/perf-evidence/scripts/diff_harness.py \
  --old <path.py> --new <path.py> --function <func> --inputs <cases.json> \
  --json <evidence-dir>/diff.json

# 前后对比（退出码 0 未回归 / 1 回归）
python skills/perf-evidence/scripts/bench_stats.py compare \
  --baseline <evidence-dir>/before.json --candidate <evidence-dir>/after.json \
  --threshold 0.10
```

- 输入语料：<生成方式 / cases.json 路径 / seed；diff_harness 不给 --inputs 时只适用单参函数>
- 原始数据：<before.json / after.json / diff.json 路径>
- 重跑约定：<例如 固定机器、关闭后台任务、每点 3 轮取中位>

## 4. 基线表

| 规模 n | 样本数 | median (ms) | IQR (ms) | min (ms) | max (ms) |
|---|---|---|---|---|---|
| <100> | <10> | <...> | <...> | <...> | <...> |
| <200> | <10> | <...> | <...> | <...> | <...> |
| <400> | <10> | <...> | <...> | <...> | <...> |

> 每个规模单独一份 JSON；n ≥ 5，注明 warmup 次数；IQR 必须给出（离散度是可信度的一部分）。

## 5. 复杂度

| n | median (ms) | 相邻 n 翻倍的时间比 | 推断 |
|---|---|---|---|
| 100 | <...> | - | |
| 200 | <...> | <2.0x / 4.0x> | <O(n) / O(n log n) / O(n²)> |
| 400 | <...> | <...> | |
| 800 | <...> | <...> | |

- 斜率/拟合：<log-log 斜率 ≈ ...；n 翻倍时间约 ... 倍>
- 结论：<例如 find_duplicates 在 n≥200 呈 O(n²)（时间约 4x/翻倍），与双循环 + list 成员线性查一致>
- 结论来源：<规模曲线优先，读代码只用于解释，不作为唯一证据>

## 6. 热点证据

- 工具：<cProfile / py-spy / 无第三方，降级说明>
- 命令：`<profiling command>`
- 证据（cumtime/tottime/ncalls 或火焰图路径）：

```text
<粘贴 Top 10 调用或文件路径>
```

- 热点定位：<例如 find_duplicates 内层 `value not in duplicates` 与双循环比较>
- 与复杂度结论互相印证：<是 / 否 + 解释>

## 7. 假设与最小改动（1–3 个）

### 假设 1：<例：内层线性查 duplicates 让本已 O(n²) 的循环多一个 O(n) 因子>

- 依据：<热点证据 / 规模曲线 / 具体代码行>
- 最小改动（只动热点，不夹带重构）：

```diff
<diff>
```

- 单独测量：<before/after JSON，median/IQR/n；其他假设未动，保证归因>

### 假设 2：<...>

- 依据：<...>
- 最小改动：

```diff
<diff>
```

- 单独测量：<...>

> 1–3 个假设各自独立测量；改动超出热点就拆出去，别混在一个 diff 里。

## 8. 前后对比

| 指标 | 改动前 | 改动后 | 变化 |
|---|---|---|---|
| median (ms) | <...> | <...> | <±x%> |
| IQR (ms) | <...> | <...> | <...> |
| n | <...> | <...> | - |

- 门禁判定：delta = <+x%>，阈值 <10%>；绝对增量 <...> ms vs 基线 IQR <...> ms → <未回归 / 回归>
- 对比命令与退出码：`bench_stats.py compare ...` → <0 / 1>

## 9. 正确性四件套

| 证据 | 方式 | 结果 |
|---|---|---|
| 签名不变 | `inspect.signature(<func>)` 前后对比 | <一致 / 不一致> |
| 单测先绿 | `<pytest command>` | <N passed> |
| 新旧差分逐条一致（返回值/异常） | `diff_harness.py --old ... --new ...` | <total=N identical=N mismatched=0 errored=0，退出 0> |
| 契约/属性测试重跑 | <hypothesis / 契约测试命令> | <通过> |

> 任一不满足→回滚；性能改动不允许夹带行为变化。差分有差异时逐条说明「是否预期」。

## 10. 门禁建议

- 判定阈值：median 回归 > 10% **且** 绝对增量 > 基线 IQR 才失败（`bench_stats.py compare` 默认口径）。
- 基线入库：`before.json` 与生成命令一起提交（含环境、样本数、warmup）。
- CI 接入：<pytest-benchmark `--benchmark-compare-fail=median:10%` / `bench_stats.py compare` / 只报告不门禁>。
- 噪声处理：<固定机器 / ≥5 次 / warmup 2 / 屏蔽 CI 抖动 / 取多轮中位>。
- 降级路径（无 pytest-benchmark 等）：<手写 `time.perf_counter` 采样，median/IQR/n/环境照留；噪声更大，不进硬门禁，只做趋势>。

## 11. 未做与风险

- 未做：<未覆盖的规模 / 未压测的边界 / 未测的并发与内存>
- 风险：<数据分布依赖 / GC 与内存 / 平台差异 / 微基准不代表真实负载>
- 回滚方式：<git revert <sha> / 保留旧实现路径>

## 12. 结论

- <达标：median 从 X ms 降到 Y ms（-Z%），正确性四件套齐全，建议合入并把基线入库>
- 或：**无可证收益，放弃**——<测量显示改动在噪声内 / 假设被数据否定 / 维护成本大于收益>，保留原实现并记录原因。
