# 属性模式（写属性时的套路库）

> 用途：步骤 3。属性测试用「一条规则覆盖一片输入」；难点是写出**不是同义反复**的属性。

## 1. 六类属性

| 类型 | 直觉 | 通用示例 | 适用函数 | 判据 |
|---|---|---|---|---|
| 不变量 invariant | 对任意合法输入，输出恒满足某约束 | `len(sort(xs)) == len(xs)`；结果非负 | 排序、规范化、校验、聚合 | 恒真；反例即缺陷 |
| 往返 round-trip | 编码后解码回到原值 | `decode(encode(x)) == x` | 序列化、压缩、单位换算、格式化/解析 | 对定义域内所有 x 成立；有损场景要限定域 |
| 幂等 idempotence | 重复执行结果不变 | `f(f(x)) == f(x)` | 清理、归一化、迁移、重试 | 两次与一次等价；注意副作用 |
| 参考实现 oracle/model | 与更简单可信的实现比较 | `my_sort(xs) == sorted(xs)` | 重写、优化、缓存 | 参考实现必须更简单，不能照抄被测实现 |
| 蜕变 metamorphic | 输入变换后输出满足可预测关系 | `sum(xs + [0]) == sum(xs)`；`sort(reverse(xs)) == sort(xs)` | 无 oracle、科学计算、图形 | 关系由领域知识确认 |
| 错误契约 error contract | 非法输入必须按契约失败且无副作用 | `pytest.raises(ValueError): parse("")` | 解析器、API、边界校验 | 异常类型/消息/清理都要断言 |

## 2. Hypothesis 写法

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1))
def test_round_trip(text: str) -> None:
    assert decode(encode(text)) == text

@given(st.lists(st.integers()))
def test_sort_length(values: list[int]) -> None:
    assert len(my_sort(values)) == len(values)
```

要点：

- 生成器域 = 契约的合法输入域；非法输入用 `with pytest.raises` 或另一组 `@given`；
- 失败后 Hypothesis 自动 shrink，报告里的反例可直接粘贴进回归测试；
- 用 `@settings(max_examples=..., deadline=None)` 控制成本；慢函数先缩小域。

## 3. 无 Hypothesis 的降级写法（属性类型不变）

手写「生成器 + 参数化 + 固定种子」，仍然覆盖同样的属性：

```python
import random
import pytest

def texts(seed: int = 0) -> list[str]:
    rng = random.Random(seed)
    cases = ["", "a", "0", "-1", "1.5", "ms", "9" * 100, "ü"]
    alphabet = "0123456789msh.+- "
    cases += ["".join(rng.choice(alphabet) for _ in range(8)) for _ in range(30)]
    return cases

@pytest.mark.parametrize("text", texts())
def test_round_trip(text: str) -> None:
    assert decode(encode(text)) == text
```

降级代价：没有自动 shrink（失败要手工删减）、随机覆盖弱于 Hypothesis；报告里写明「降级，未用 Hypothesis」。

## 4. 生成器诚实性（避免空转）

- **域要对**：只生成合法输入，避免用 `filter` 大量丢弃；非法输入单独一组。
- **不要抄实现**：oracle 必须是独立来源（更简单的参考实现、规格关系、另一实现），不能 `assert f(x) == f(x)`。
- **不要恒真**：`assert isinstance(result, int)` 这类属性信息量低；换成具体约束。
- **不要过窄**：只生成 0 和 1 测不出边界；至少混入空、极值、随机。
- **记录种子**：手工生成器必须可复现（固定种子/固定用例表）。

## 5. 收缩（shrinking）

- 失败时先看反例是否可读；不可读通常是生成器太宽（复杂 filter）而不是函数错。
- 手写降级路径：对字符串/序列用「块删除」贪心最小化，保留同一异常类型（可用 `scripts/probe_inputs.py --minimize`）。
- 最小反例要能独立复现：输入 + 期望 + 实际 + 命令。

## 6. 状态测试（有状态对象才用）

- 适用：缓存、索引、会话、连接池、事务、协议状态机。
- 做法：定义动作序列 + 每步后检查不变量；与「内存模型」对照。
- 不适用：纯函数不要上状态测试，成本高且没有额外收益。
- 降级：手写固定操作序列（初始化 → 操作 1..N → 校验），至少覆盖「先 A 后 B」的组合。

## 7. 属性反模式

| 反模式 | 问题 | 改法 |
|---|---|---|
| 同义反复 | 用被测实现算期望 | 换独立 oracle 或规格关系 |
| 恒真断言 | 只断言不抛异常/类型对 | 断言具体不变量、往返、错误契约 |
| 空转生成器 | filter 掉 99% 输入 | 缩小域或换生成策略 |
| 过拟合实现 | 断言内部调用顺序 | 断言可观察行为 |
| 只测合法输入 | 错误路径 0 覆盖 | 增加非法输入组 |
| 属性太多太碎 | 维护成本高、噪声大 | 3–5 条高价值属性优先 |

## 8. 选属性速查

1. 有编码/解码或格式化/解析 → round-trip。
2. 有集合/序列处理 → 长度、元素守恒、顺序不变。
3. 有数值计算 → 平移/缩放关系、单调性、非负性。
4. 有规范化/清洗 → 幂等。
5. 有更简单参考实现 → oracle。
6. 什么 oracle 都没有但能变换输入 → 蜕变关系。
7. 解析/API 边界 → 错误契约。
