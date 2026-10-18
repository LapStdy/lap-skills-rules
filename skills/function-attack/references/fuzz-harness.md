# fuzz harness 与降级 smoke

> 用途：步骤 5。只在**解析/解码/协议/安全边界**上做；纯业务函数用属性测试更划算。

## 1. 何时做、何时不做

**值得**：外部输入解析（JSON/CSV/配置/协议/文件格式）、编解码、网络边界、原生扩展/FFI、安全敏感路径。
**不值得**：纯算术、纯业务规则、薄封装、每次要起服务的函数（先把边界切出来）。

## 2. Atheris harness 模板（Linux/macOS）

```python
import sys
import atheris

with atheris.instrument_imports():
    import target_module

def test_one_input(data: bytes) -> None:
    try:
        target_module.parse(data.decode("utf-8", errors="replace"))
    except (ValueError, TypeError):
        pass  # 契约内的失败，不算崩溃

atheris.Setup(sys.argv, test_one_input)
atheris.Fuzz()
```

运行：`python harness.py -max_total_time=120 -dict=dict.txt corpus/`

要点：

- **只捕获契约内的异常**；未捕获异常/崩溃才是信号。
- harness 必须确定性（不依赖时间/随机/网络），否则崩溃不可复现。
- 先跑 corpus 确认 harness 正常，再开始 fuzz。
- 输入用 `FuzzedDataProvider` 拆成结构化参数（多参数函数）。

## 3. 种子、字典、覆盖率

- **种子 corpus**：放「有效 + 无效 + 边界」样本；corpus 同时是回归集。
- **字典**：魔法字节/关键字/协议头（单位、分隔符、关键字）能显著提速。
- **覆盖率引导**：没有插桩的 fuzz 等于瞎撞；Atheris 需 `instrument_imports`，Go/Rust 原生支持。
- 失败输入会落盘（崩溃/hang），把它加入 corpus 防止复发。

## 4. sanitizer

- 原生扩展：ASAN/UBSAN（Atheris 可配合）；Rust unsafe 用 cargo-fuzz + sanitizer。
- 解释型语言：未捕获异常、panic、超时就是信号；内存错误由运行时兜底。
- 判据：崩溃必须稳定复现；不能复现先查 harness 非确定性。

## 5. 崩溃去重与最小化

- 按「异常类型 + 栈顶函数 + 输入结构」聚类；同栈不同输入视为同一缺陷。
- 取最小输入做回归；用工具自带最小化或 `scripts/probe_inputs.py --minimize`（仅单参数）。
- 修复后把最小输入加入 corpus 与示例测试。

## 6. 无 Atheris 的降级（Windows 常见）

| 替代 | 做法 | 边界 |
|---|---|---|
| 边界 smoke | `python scripts/probe_inputs.py --module m.py --function f --minimize` | 固定语料，不是覆盖率引导 |
| 手写随机 | 固定种子生成器 + 参数化（见 property-patterns 降级写法） | 覆盖弱、需手工最小化 |
| Go 原生 fuzz | `go test -fuzz=FuzzX`（Go 项目） | 仅 Go |
| WSL | 在 WSL 里装 Atheris | 需要团队允许 WSL |

**必须写**：「未做 fuzz / 降级为边界 smoke，缺失覆盖率引导与崩溃自动最小化」。

## 7. CI 策略

| 阶段 | 做法 | 预算 |
|---|---|---|
| PR | corpus 回归或 60–120 秒短 fuzz | 1–3 分钟 |
| 夜间 | 每 target 10–30 分钟，多 worker | 机器时间 |
| 连续多日无新覆盖 | 停，换 target 或换手段 | — |

## 8. 安全边界

- fuzz 在进程内跑不可信输入有风险；原生/不可信代码用子进程/容器隔离。
- 无超时保护时，死循环会挂住整个会话；用外部 timeout（`timeout`/PowerShell `Start-Process` + 等待）兜底。
- 不要对生产数据库/真实网络 fuzz。

## 9. 报告格式

```text
fuzz：工具/target/harness 路径
种子：N 条；字典：有/无；时长：N 秒
结果：执行 N 次；新覆盖 <有/无>；崩溃 <数量与类型>
最小化：<输入>（或「未做，原因」）
未做说明：<Atheris 不可用/纯函数不适用等>
```
