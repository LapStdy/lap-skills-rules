# LapStdy 工作规范与技能总库

本仓库放两类东西：**规矩**（AI 必须遵守）和**技能**（AI 可安装）。仓库名 `lap-skills-rules`，内容涵盖全部工作资产，找东西从本页开始。

## 一页看懂

| 东西 | 一句话 | 位置 | 什么时候用 |
|---|---|---|---|
| 交付物通道 | 文档、界面文案、注释只写「此刻为真」 | `rules/delivery.md` | 每次写文件；说「查交付物」 |
| 项目结构 | 顶层放什么、根文件只许哪些、两个 profile | `rules/project-structure.md` | 新项目开工、新建或移动目录 |
| 技能规范 | 技能怎么写、怎么装、怎么更新 | `rules/skills.md` | 写技能、改装技能、换电脑 |
| 四款技能 | 方案寻优 → 函数规范 → 攻击测试 → 性能取证 | `skills/` | 说「有没有更优解」「审函数」「找 bug」「要性能证据」 |
| 交付物检查器 | 自动扫不该写进交付物的字 | `tools/check_artifacts.py` | 交付前 |
| 技能安装器 | 把仓库技能同步到 `~/.dsh/skills` | `tools/install_skills.py` | 安装、更新、比对漂移 |

## 规矩怎么落地

1. 每个项目根的 `AGENTS.md` 放十几行硬规则；本仓库 `rules/` 是全文，仓库根也有 `AGENTS.md`。
2. 交付前跑检查器，输出 `PASS` 才算干净；`WARN` 不阻断但交付前要清零。
3. 改规矩：先改本仓库，再同步项目 `AGENTS.md`；只改一头会漂。
4. 技能只从本仓库装；先改仓库，再跑安装器。

## 检查器

```bash
python tools/check_artifacts.py <目录>
python tools/check_artifacts.py --strict      # 中/低风险也返回 1
python tools/check_artifacts.py --selftest    # 内置样例自检
```

- `PASS` + 退出码 0：干净。
- `WARN` + 退出码 0：只有中/低风险，不阻断；交付前按「改法」清零，或加 `--strict` 纳入门禁。
- `FAIL` + 退出码 1：有高风险文字，必须改。
- 豁免：CHANGELOG、交接账本、`archive/`、迁移说明、测试冻结证据。
- 真误报：那一行加 `artifact-check: ignore`；整文件误报加 `artifact-check: off`。

## 技能

| 技能 | 用途 | 典型触发语 |
|---|---|---|
| `first-principles` | 第一性原理寻优：还原真实目标与约束 → 事实基座 → 拆假设 → 最小充分系统 → 候选解对比 → 最小验证 | 「有没有更优解」「从第一性原理看」「方向对不对」「该不该做」「值不值得」 |
| `function-spec` | 函数规范：29 条规则、契约（输入/输出/错误/副作用）、逐函数审计 | 「按规范审一下这个函数」「契约写清楚」「29 条规则」 |
| `function-attack` | 函数攻击：边界/错误契约、属性测试、抽样变异、按需 fuzz/差分，产出最小反例 | 「找未知 bug」「测试没测到」「属性测试」「变异测试」「fuzz」 |
| `perf-evidence` | 性能取证：基线、复杂度、cProfile 热点、最小改动、正确性四件套、benchmark 回归门禁 | 「这个函数慢」「怎么优化」「复杂度是多少」「加个 benchmark 防回归」 |

技能互斥路由：先判断「该不该做/有没有更优解」用 `first-principles`；决定做之后，函数怎么写用 `function-spec`、找未知缺陷用 `function-attack`、性能值不值得改用 `perf-evidence`。已知 bug 根因用 `diagnosing-bugs`，从零 TDD 用 `tdd`，PR 评审用 `code-review`，架构问题用 `codebase-design`（这些是 DSH 自带/其他来源技能，不在本仓库）。

`first-principles` 的最小评测见 `evals/first-principles/`：两个 case + 8 条机械判据，可重跑。

## 安装技能

DSH 的用户级技能目录是 `~/.dsh/skills/<name>/SKILL.md`（Windows 即 `C:\Users\<你>\.dsh\skills\`）。

```powershell
# 1) 克隆仓库
git clone https://github.com/LapStdy/lap-skills-rules.git
cd lap-skills-rules

# 2) 安装/更新全部技能（零依赖，Python 3.11+）
python tools/install_skills.py

# 3) 核对安装副本与仓库是否一致
python tools/install_skills.py --check
```

- 只装某一个：`python tools/install_skills.py first-principles`
- 换安装目录：`python tools/install_skills.py --dest <目录>`
- 卸载：`python tools/install_skills.py --uninstall <名字>`
- 装完确认四个目录都在：`~/.dsh/skills/first-principles/`、`function-spec/`、`function-attack/`、`perf-evidence/`。DSH 下次会话即可按 `description` 自动触发，也可手动调用对应技能。
- 手写复制也可以：把 `skills/<name>/` 整个目录复制到 `~/.dsh/skills/`；但更新时请用安装器，避免漏文件。

> 仓库可见性以 GitHub Settings 为准：若为私有，新设备需先登录 GitHub，或改用 SSH：`git clone git@github.com:LapStdy/lap-skills-rules.git`。

**更新**：`git pull` 后重跑 `python tools/install_skills.py`。**卸载**：删 `~/.dsh/skills/` 下对应目录即可。

## 怎么下载

- 只要文件：本页右上 **Code → Download ZIP**。
- 换电脑后接着用：`git clone https://github.com/LapStdy/lap-skills-rules.git`（私有仓需要登录；也可用 SSH `git@github.com:LapStdy/lap-skills-rules.git`，新电脑先把公钥加到 GitHub）。
- 只想要某一个技能：进 `skills/<名字>/` 复制整个目录到 `~/.dsh/skills/`。

## 新项目开工（一键）

对新项目说一句：

> 按 https://github.com/LapStdy/lap-skills-rules 的开工说明，给这个项目装规矩。

AI 会生成 `AGENTS.md`、装好检查器，并跑一次自检。也可以手动：

```bash
python tools/bootstrap.py <项目目录>
```

装完的效果：新项目一开会话就带着交付物硬规则，交付前自动跑检查。结构规范按 `rules/project-structure.md` 的 A/B profile 选，不默认建满目录。

## 依赖与降级

- 技能、检查器与安装器都**零第三方运行时依赖**，只用 Python 标准库。
- 可选工具缺失时技能会显式降级并写明少了什么证据：`hypothesis`、`mutmut`、`pytest-benchmark`、`py-spy`、`asv` 都不是必需。
- 需要 Python 3.11+（本仓库在 3.14 上验证）。

## 目录

```text
rules/       # 规范全文：交付物通道、项目结构、技能规范
tools/       # check_artifacts.py（检查器）+ bootstrap.py（一键开工）+ install_skills.py（技能安装）
templates/   # 新项目用的 AGENTS.md 模板
skills/      # 可安装的四款技能
evals/       # 技能最小评测（当前含 first-principles 两个 case）
docs/        # ADR 与仓库稳定文档
```

## 版本

当前 `v0.3.0`；版本记录见 [CHANGELOG.md](CHANGELOG.md)。

## 一句话

规矩管「写出来干不干净」，技能管「做出来对不对」。
