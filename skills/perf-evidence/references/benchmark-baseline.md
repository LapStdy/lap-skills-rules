# Benchmark 基线与回归门禁

> 用途：步骤 5–6。回答「改动是快了、慢了，还是噪声」，并据此设 CI 门禁。
> 前提：已有单函数级、输入固定、无网络的基准。没有可复现基线就不设门禁。

## 1. 什么算证据

单次 `time.time()` 差值不算证据：它混入进程启动、解释器热态、页缓存、调度与频率漂移，一次采样既没有离散度也无法排除偶然，无法区分「快了 8%」与「机器恰好在抖」。合格证据的最低要求：

| 要求 | 最低线 | 原因 |
|---|---|---|
| warmup 丢弃 | 显式预热，预热不计入统计 | 首次调用含导入、缓存填充、分支预测未热 |
| 同进程、同环境 | 同一 venv、同一机器、同一电源/性能策略 | 跨环境差异通常远大于被测改动 |
| 重复次数 | ≥5，建议 10–30 | 5 次才看得出离散度；>30 收益饱和 |
| 采样方式 | 交错 A/B（A,B,A,B…） | 漂移同时污染两边，差值抵消 |
| 输入 | 固定、可复现、规模接近真实 | 规模变化会改变复杂度项 |
| 后台负载 | 关闭浏览器/同步盘/杀软/CI 同机其他 job | 抢占直接抬高尾延迟 |

顺序执行（跑完 A 再跑 B）是把漂移全算进 B 的典型错误：热降频、缓存冷热、系统更新都会让后跑者更差。交错执行把漂移转成两边共有的噪声。

## 2. 统计口径

一次基准产出一组 round 时长，报告其分布，不要只报一个数。

| 指标 | 计算 | 用途 |
|---|---|---|
| median | 中位数 | **主指标**：抗离群点，代表典型耗时 |
| IQR | Q3 − Q1 | 离散宽度；同时是回归判定的第二条件 |
| Q1 / Q3 | 25% / 75% 分位 | 判断新值是否落在基线常态区间外 |
| min / max | 极值 | min≈无干扰最好情况；max 暴露抖动与 stop-the-world |
| CV | stddev / mean × 100% | 跨量级比噪声；>10% 先治噪声再谈优化 |

- **均值陷阱**：均值被右尾拉高，几条 GC 长尾就能翻倍；用均值定门禁会把噪声当回归。
- **离群点**：先查原因（GC、后台进程、首次分配），能解释就记录并保留原数据；不能解释才按 IQR 规则剔除，报告写明剔除条数与规则。禁止为好看静默删除。
- **相对变化**：Δ% = (after − before) / before × 100；报告同时给绝对值与 Δ%。
- **噪声地板**：同一份代码、同一环境跑两轮会差多少，就是这个环境的可检测下限。校准：同一版本跑 5 组，两两比较 median，取 |Δ%| 最大值记为 N。报告表的 median/IQR 取跨组汇总（先算每组 median，再取中位数与 IQR），与 pytest-benchmark 单组内输出不混用。
- **MDE（最小可检测效应）**：改动量小于 N 时，任何方向都不可声称。重复次数加倍只把随机噪声降到约 1/√2，降不了热降频与共享机噪声。
- **显著性**：判定 = 变化量超过噪声地板 **且** 超出基线 IQR；两条都不满足就写「无可检测变化」，不写「略有提升」。

## 3. pytest-benchmark

本机 venv 已装 pytest-benchmark 5.3.0；参数名经 `pytest --help` 与源码核对，保存/对比/门禁三条流程在临时目录实测过。

最小骨架（正确性断言写在 benchmark 调用**之后**、拿返回值断言，不污染计时）：

```python
import pytest

@pytest.mark.benchmark(group="parse", min_rounds=10, warmup=True)
def test_parse_json(benchmark):
    result = benchmark(parse_json, {"a": 1, "b": 2})   # 固定输入
    assert result["ok"] is True   # 行为不变是性能结论的前提
```

- `@pytest.mark.benchmark(...)`：同名 `group` 在同表对比。marker 只接受关键字参数，合法键：`group`、`min_time`、`max_time`、`min_rounds`、`warmup`、`warmup_iterations`、`timer`、`disable_gc`、`precision`、`confidence`、`calibration_precision`、`cprofile`。
- `benchmark(func, *args, **kwargs)`：自动校准循环与轮数，返回被测函数返回值。
- `benchmark.pedantic(target, args=(), kwargs=None, setup=None, teardown=None, rounds=1, warmup_rounds=0, iterations=1)`：手动定轮数（取证时给 `rounds≥10`、`warmup_rounds≥2`）；setup/teardown 不在计时区间内；`iterations > 1` 时不能再给 setup。

| 目的 | 命令 |
|---|---|
| 跑并保存基线 | `pytest bench/ --benchmark-save=baseline-2026-10-18` |
| 与指定基线比 | `pytest bench/ --benchmark-compare=0001`（也可直接给已保存 json 路径） |
| 只跑基准 | `pytest bench/ --benchmark-only` |
| 门禁失败退出 | `pytest bench/ --benchmark-compare=0001 --benchmark-compare-fail=median:10%` |
| 机器可读产物 | `pytest bench/ --benchmark-json=out/bench.json` |
| 精简列 | `pytest bench/ --benchmark-columns=min,median,iqr,ops` |
| 固定轮数 | `pytest bench/ --benchmark-min-rounds=10` |
| 显式预热 | `pytest bench/ --benchmark-warmup=on --benchmark-warmup-iterations=50` |

`--benchmark-compare-fail` 接受 `字段:百分比%` 或 `字段:绝对秒数`，字段限 `min|max|mean|median|stddev|iqr`，可重复给多个表达式；它只做阈值比较，不做统计检验，也不做多重比较校正。`--benchmark-save` 默认写入 `./.benchmarks/<machine>/counter_NAME.json`，目录用 `--benchmark-storage` 改。实测注意：`--benchmark-json=out/bench.json` 不会自动建父目录，目录不存在会在 sessionfinish 抛 `FileNotFoundError`；`--benchmark-compare-fail` 触发时退出码为 1 并打印 `Performance has regressed`。

## 4. asv（多版本趋势）

- 何时用：要跨多个提交、多个参数（如 n=10³/10⁴/10⁵）看历史趋势与自动回归检测，而不是单次前后对比。
- 常用命令：`asv run`（跑当前提交）、`asv continuous main HEAD --factor 1.1`（两版本对比并标出超过阈值的回归）、`asv compare <a> <b>`（只比已有结果）、`asv publish`（生成站点）。
- 基准放 `benchmarks/`，配置写 `asv.conf.json`，结果落 `results/`；跨机器比较前先核对 machine 配置。
- 本机未安装 asv（`pip show asv` 无结果），本项目**未做** asv；需要时先装、再补「已做」与命令输出。

## 5. 基线 JSON 与版本化

`--benchmark-json` 顶层字段：`machine_info`、`commit_info`、`benchmarks`、`datetime`、`version`。`benchmarks[]` 每项含 `name`、`fullname`、`group`、`params`、`options`、`stats`；`stats` 含 `min,max,mean,stddev,rounds,iterations,median,iqr,q1,q3,outliers,ld15iqr,hd15iqr,ops,total`，`--benchmark-json` 还额外保留 `data`（全部采样，时长单位秒）。

入库的是摘要而不是原始 JSON（原始文件含全部采样，体积大、diff 噪声多）：

```json
{
  "schema": 1,
  "label": "parse_json",
  "group": "parse",
  "median_s": 0.000412, "iqr_s": 0.000036,
  "q1_s": 0.000398, "q3_s": 0.000434,
  "min_s": 0.000391, "max_s": 0.000611,
  "cv_pct": 6.5, "n": 10, "rounds_per_run": 2348,
  "noise_floor_pct": 3.5,
  "env": {"cpu": "Intel64 Family 6 Model 63", "os": "Windows 11",
          "python": "3.14.3", "pytest_benchmark": "5.3.0", "runner": "local-dev"},
  "commit": "abc1234", "timestamp": "2026-10-18T14:00:00+08:00",
  "command": "pytest bench/ --benchmark-min-rounds=10 --benchmark-json=out/bench.json"
}
```

| 字段 | 必须有 | 作用 |
|---|---|---|
| label / group | 是 | 跨运行匹配的唯一键，改名等于新基线 |
| median / iqr / n | 是 | 主指标、离散度、样本量（n=独立运行组数，组内 rounds 另记） |
| env | 是 | 不同 CPU/OS 的基线不可直接比 |
| commit / 版本 | 是 | 追溯它对应哪份代码 |
| 时间 + command | 是 | 复现入口 |
| noise_floor_pct | 是 | 判定「变化是否可检测」的下限 |

- 入库位置：`benchmarks/baselines/<label>.json`；原始 `out/bench.json` 进 CI artifact，不提交。
- 更新流程：一次独立 PR，说明更新原因（代码改动、环境/runner 变更、噪声地板重测），附 before/after 表与 changelog 行；**同一 PR 内不许既改实现又刷基线**，否则门禁失效。
- 机器差异：换 CPU、换 OS、换电源策略 = 基线失效，必须重测；`env.runner` 与 CI runner 标签要一致。共享云 runner 的绝对值不可跨供应商比。
- changelog：`benchmarks/BASELINE-CHANGELOG.md`，每行写日期、label、旧→新中位数、原因、commit、runner。

## 6. CI 门禁设计

判定用双条件，缺一不判红：

| 条件 | 表达式 | 作用 |
|---|---|---|
| 幅度 | Δmedian > 10% | 相对阈值，可跨量级 |
| 超离散 | after.median > before.q3，或 Δ > baseline.iqr | 排除落在基线常态区间内的抖动 |
| 复跑确认 | 失败项复跑 2 次，3 次里≥2 次成立才判红 | 压 flaky |

- **同一 runner**：门槛只在登记过的 runner 标签上生效；换 runner 时只出趋势、不判红。
- **取中位数**：单次 job 内同一基准跑 3 轮取 median-of-medians，再与基线比。
- **flaky 处理**：连续两次门禁报红但复跑不成立，记为 flaky 条目并修噪声源（GC、并行 job、容器 CPU 限制），不要靠调高阈值掩盖。
- **共享 CI 噪声大**（CV>10%、噪声地板>10%）：不设硬门禁，只出趋势与每周报告；硬门禁的结果必然是被整体忽略。
- **绝对时间阈值为什么不能用**：如「必须 <5 ms」跨机器/跨 Python 版本不可迁移，硬件一升级就全部失效，还会把已经够快的函数判红。
- 只对变更路径相关的基准触发，全量基准放夜间。

## 7. 常见统计陷阱

| 陷阱 | 表现 | 处置 |
|---|---|---|
| 均值 vs 中位数 | 长尾把均值拉高，报告「变慢」实际是抖动 | 主指标用 median，IQR 一并报 |
| p-hacking / 多次比较 | 试 20 个基准总有一个「显著」 | 预先登记基准清单与阈值；失败结果也报 |
| 回归均值 | 挑最差一轮当基线，复测自然「变好」 | 基线取多轮中位数，不取极端轮 |
| 机器漂移/热降频 | 后跑的版本系统性偏慢 | 交错 A/B，同机同环境 |
| 并发负载 | 同机其他 job 抢占 | 独占 runner，或标记「噪声环境不判定」 |
| 缓存预热 | 首次比后续慢数倍 | 显式 warmup 并丢弃 |
| 只报最好一次 | 从 10 次里挑最快那次 | 报 median + IQR + n，保留全部原始数据 |

## 8. 报告格式

```text
标签：parse_json（group=parse）  commit：abc1234 → def5678  runner：local-dev
基线：median 0.412 ms  IQR 0.036 ms  n=10  CV 6.5%  噪声地板 3.5%
结果：median 0.365 ms（−11.4%），IQR 0.031 ms，n=10
判定：变化量 > 噪声地板且越过基线 Q3 → 可声称改善
```

| 指标 | before | after | Δ% | 判定 |
|---|---|---|---|---|
| median | 0.412 ms | 0.365 ms | −11.4% | 改善，可信 |
| IQR | 0.036 ms | 0.031 ms | −13.9% | 离散未变差 |
| Q1 / Q3 | 0.398 / 0.434 ms | 0.352 / 0.383 ms | — | 落在基线区间外 |
| min / max | 0.391 / 0.611 ms | 0.347 / 0.402 ms | — | 尾延迟同时下降 |
| n | 10 | 10 | — | 达标（≥5） |

结论必须三选一：**可声称改善/回归**（双条件成立）、**无可检测变化**（低于噪声地板）、**不可判定**（噪声过大，先修测量）。没有收益时写「放弃」并保留数据。

## 9. 参考来源

- pytest-benchmark 文档：<https://pytest-benchmark.readthedocs.io/>
- asv（airspeed velocity）文档：<https://asv.readthedocs.io/>
- Python `timeit` 文档：<https://docs.python.org/3/library/timeit.html>
- Python `statistics` 文档（中位数/分位数口径）：<https://docs.python.org/3/library/statistics.html>
