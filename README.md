# LapStdy 工作规范与技能总库

> 一句话：规矩让每次会话都守底线，技能让某类活有工序书，工具把「完成」变成 0/1。

本仓库是规范、技能与检查工具的唯一源。项目侧只留操作版摘要（项目根 `AGENTS.md`），全文在这里；找东西从本页开始。

## 一页看懂

| 东西 | 管什么 | 位置 | 什么时候用 |
|---|---|---|---|
| 交付物通道 | 交付物只写「此刻为真」；过程与历史走别的通道 | `rules/delivery.md` | 每次写文档、文案、注释 |
| 改动范围 | 每行改动指向本次请求；范围外的问题进收件箱 | `rules/change-scope.md` | 写代码、评审 diff |
| 项目结构 | 顶层目录与根文件白名单、三种 profile、落位决策表 | `rules/project-structure.md` | 新项目开工、新增目录 |
| 门禁 | 完成由一条命令判定；合并判据与假红判据 | `rules/gates.md` | 定「做完」、判门禁红 |
| 测试可重复性 | 假件注入、断言不变量、禁止逐字节比对含时间的产物 | `rules/testing.md` | 写或改测试 |
| Windows 进程红线 | 存活探测不用信号、强杀先隔离、信号只在主线程 | `rules/windows-process.md` | 起进程、杀进程、测试宿主 |
| 账本与欠账 | TASKS、DEBT、交接账本三者的分工与字段 | `rules/ledger.md` | 记账、交接、还债 |
| 技能规范 | 技能怎么写、怎么装、怎么评测 | `rules/skills.md` | 写技能、换电脑 |

## 技能

| 技能 | 用途 | 典型触发语 |
|---|---|---|
| `first-principles` | 第一性原理寻优：还原目标与约束、拆假设、最小充分系统、候选对比、最小验证 | 「有没有更优解」「方向对不对」「该不该做」 |
| `function-spec` | 单个函数的规范检查：命名、参数、职责、错误契约、docstring、长度 | 「按规范审这个函数」「契约写清楚」 |
| `function-attack` | 函数级攻击：边界、错误契约、属性测试、变异、按需 fuzz | 「找未知 bug」「测试没测到」「变异测试」 |
| `perf-evidence` | 性能取证：基线、热点、最小改动、正确性四件套、回归门禁 | 「这个函数慢」「加个 benchmark 防回归」 |
| `project-gate` | 给项目搭一条可机械验证的门禁：选检查、生成 gate.py、造红验证 | 「搭门禁」「一条命令验完」「新项目开工」 |
| `zcode-auto-workflow` | ZCode 自动工作流：写卡、派卡、盯到终态、复核、串行门禁、合并、清理 | 「派卡」「盯 ZCode 到早上」「无人值守」 |
| `memory-curation` | 记忆分层整理：该不该留、放哪一层、执行后校验 | 「记忆太乱」「整理记忆」 |

路由：先判「该不该做 / 有没有更优解」用 `first-principles`；决定做之后，写代码按 `function-spec`，找未知缺陷按 `function-attack`，性能值不值得按 `perf-evidence`；要落实「完成」的判定用 `project-gate`，要按任务卡循环推进用 `zcode-auto-workflow`，整理记忆用 `memory-curation`。

## 工具（零第三方依赖，只用标准库）

| 工具 | 作用 | 命令 |
|---|---|---|
| `tools/check_artifacts.py` | 交付物文字检查：历史渗入、施工字、聊天腔 | `python tools/check_artifacts.py .` |
| `tools/check_structure.py` | 结构上限：函数 50 行、参数 4 个、类 300 行、模块 500 行；允许清单只缩不涨 | `python tools/check_structure.py . --allow structure-allow.txt` |
| `tools/check_repo.py` | 资产仓自洽：README 索引、技能 frontmatter、评测同名、版本一致 | `python tools/check_repo.py --check-tools` |
| `tools/bootstrap.py` | 一键开工：把两个检查器、门禁骨架与 `AGENTS.md` 装进新项目 | `python tools/bootstrap.py <项目目录>` |
| `tools/install_skills.py` | 技能安装器：装到 `~/.dsh/skills`，可 `--check` 比对漂移 | `python tools/install_skills.py --check` |

检查器输出三种结论：`PASS`（退出码 0）、`WARN`（只有中/低风险，退出码 0，交付前清零）、`FAIL`（退出码 1）。真误报用行内 `artifact-check: ignore`，整文件误报用 `artifact-check: off`，不要拿豁免绕规则。

## 门禁骨架

`templates/gate.py` 是项目门禁的起点：七类检查按依赖顺序串行跑，失败即停，必需项缺工具按 `FAIL`，可选项缺工具报 `SKIP` 并列出证据缺口。

```bash
python scripts/gate.py            # 跑到第一条失败
python scripts/gate.py --keep-going
python scripts/gate.py --list
```

把 `tools/check_artifacts.py` 与 `tools/check_structure.py` 复制到项目 `scripts/`，再按项目实际删改 `CHECKS`；判据与假红处置见 `rules/gates.md`。

## 新项目开工（一键）

对新项目说一句「按 https://github.com/LapStdy/lap-skills-rules 的开工说明，给这个项目装规矩」，或手动：

```bash
python tools/bootstrap.py <项目目录>
```

装完得到 `scripts/` 下三个文件：`check_artifacts.py`、`check_structure.py`、`gate.py`，以及带「交付物通道、改动范围、完成判据、账本」四段的 `AGENTS.md`。之后：

1. 把项目目标、技术栈、首个里程碑写进 README；
2. `python scripts/gate.py` 首次会红，按输出逐条补齐；
3. 既有超限写进 `structure-allow.txt` 并在 `DEBT.md` 记账。

## 本仓库自检

```bash
python tools/check_repo.py --check-tools        # 自洽 + 三个工具一起跑
python tools/check_artifacts.py --selftest      # 检查器自检
python tools/check_structure.py --selftest      # 结构检查器自检
python tools/install_skills.py --check          # 安装副本与仓库比对
```

`structure-allow.txt` 记录资产仓自身脚本的既有超限；每条都对应拆分工作，清单只缩不涨。

## 安装技能

用户级技能目录是 `~/.dsh/skills/<name>/SKILL.md`（Windows 即 `C:\Users\<你>\.dsh\skills\`）。

```powershell
git clone https://github.com/LapStdy/lap-skills-rules.git
cd lap-skills-rules
python tools/install_skills.py          # 装全部技能
python tools/install_skills.py --check  # 只比对，不写盘
python tools/install_skills.py first-principles   # 只装指定技能
python tools/install_skills.py --uninstall <名字>
```

- 先改仓库，再装；顺序反过来会丢改动。
- 安装副本只读：更新一律 `git pull` 后重跑安装器。
- 装完重开一个会话，技能目录才会重新注入。
- 手写复制也可以，但更新时用安装器，避免漏文件。

## 目录

```text
rules/              # 规范全文（唯一真源）
tools/              # 检查器、门禁骨架来源、一键开工、技能安装
templates/          # 新项目模板：AGENTS.md、gate.py
skills/<name>/      # 可安装技能（SKILL.md + references/scripts/templates）
evals/<name>/       # 技能最小评测（可重跑）
docs/               # ADR 与仓库稳定文档
structure-allow.txt # 资产仓结构上限允许清单（只缩不涨）
```

## 依赖与降级

- 技能、检查器与安装器零第三方运行时依赖，只用 Python 标准库，需要 Python 3.11+。
- 可选工具缺失时技能显式降级并写明少了什么证据：`hypothesis`、`mutmut`、`pytest-benchmark`、`py-spy`、`asv` 都不是必需。
- `ruff`、`mypy`、`pytest`、`import-linter` 属项目栈；门禁里必需项缺工具按失败处理，可选项才允许跳过。

## 版本

当前版本见 [CHANGELOG.md](CHANGELOG.md)；本页不写版本号，版本只有一处真源。

## 一句话

规矩管「写出来干不干净」，技能管「这类活怎么做才对」，工具管「做完没做完」。
