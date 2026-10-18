# lap-skills

面向 **DeepSeek Harness (DSH)** 的函数质量技能包：把「函数规范 → 攻击测试 → 性能取证」做成三款可安装、零第三方运行时依赖的技能。

适用场景：写完或接手一批函数后，想系统检查「写得规不规范、测试有没有漏、性能改没改坏」。

## 包含技能

| 技能 | 用途 | 典型触发语 |
|---|---|---|
| `function-spec` | 函数规范：29 条规则、契约（输入/输出/错误/副作用）、逐函数审计 | 「按规范审一下这个函数」「契约写清楚」「29 条规则」 |
| `function-attack` | 函数攻击：边界/错误契约、属性测试、抽样变异、按需 fuzz/差分，产出最小反例 | 「找未知 bug」「测试没测到」「属性测试」「变异测试」「fuzz」 |
| `perf-evidence` | 性能取证：基线、复杂度、cProfile 热点、最小改动、正确性四件套、benchmark 回归门禁 | 「这个函数慢」「怎么优化」「复杂度是多少」「加个 benchmark 防回归」 |

三款技能互斥路由：已知 bug 根因用 `diagnosing-bugs`，从零 TDD 用 `tdd`，PR 评审用 `code-review`，架构问题用 `codebase-design`（这些是 DSH 自带/其他来源技能，不在本仓库）。

## 安装

DSH 的用户级技能目录是 `~/.dsh/skills/<name>/SKILL.md`（Windows 即 `C:\Users\<你>\.dsh\skills\`）。

```bash
# 1) 克隆仓库
git clone https://github.com/LapStdy/lap-skills.git
cd lap-skills

# 2) 复制到 DSH 技能目录（macOS / Linux / Git Bash）
mkdir -p ~/.dsh/skills
cp -r skills/* ~/.dsh/skills/
```

Windows PowerShell：

```powershell
git clone https://github.com/LapStdy/lap-skills.git
New-Item -ItemType Directory -Force "$HOME\.dsh\skills" | Out-Null
Copy-Item -Recurse -Force ".\lap-skills\skills\*" "$HOME\.dsh\skills\"
```

装完确认三个目录都在：`~/.dsh/skills/function-spec/`、`function-attack/`、`perf-evidence/`。DSH 下次会话即可按 `description` 自动触发；也可手动加载对应技能。

**更新**：`git pull` 后重新执行第 2 步覆盖旧副本。**卸载**：删除 `~/.dsh/skills/` 下对应目录即可。

## 依赖与降级

- 技能本身**零第三方运行时依赖**；自带脚本只用 Python 标准库（`ast`、`cProfile`、`time`、`subprocess`、`importlib` 等）。
- `function-spec` 的 `scripts/metrics.py` 用于 AST 指标；`function-attack` 的 `scripts/probe_inputs.py` 用于边界 smoke；`perf-evidence` 的 `scripts/diff_harness.py`/`bench_stats.py` 用于新旧差分与采样。
- 可选工具缺失时技能会显式降级并写明「未做/少了什么证据」：`hypothesis`、`mutmut`、`pytest-benchmark`、`py-spy`、`asv` 都不是必需。
- 运行自带脚本需要 Python 3.11+（本仓库在 3.14 上验证）；不安装任何包也能用。

## 目录

```text
skills/
├─ function-spec/        # SKILL.md + references/ + scripts/metrics.py
├─ function-attack/      # SKILL.md + references/ + templates/ + scripts/probe_inputs.py
└─ perf-evidence/        # SKILL.md + references/ + templates/ + scripts/diff_harness.py, bench_stats.py
```

每个技能的 `SKILL.md` 只保留触发、路由、流程、停止规则、报告模板与反合理化；长细则放 `references/`，运行时按需加载。

## 质量状态

三款技能在 2026-10-18 各做过 8 条独立回归（4 触发 / 2 不触发 / 1 输出完整 / 1 降级），机械判据与 rubric 全部通过；另有干净对照样本检查误报。回归证据与哈希留在开发准备区，不随本仓库分发。

## 来源与版本

- 版本：2026-10-18（Phase 2D）。
- 本仓库是技能源；`~/.dsh/skills/` 是安装副本，仓库始终为准。
- 暂未附开源许可证；如需公开分享或二次分发，请先选择并添加许可证（如 MIT）。

## 一句话

规范先写契约，攻击再找漏，性能最后拿证据——三款技能各自独立，按需加载。
