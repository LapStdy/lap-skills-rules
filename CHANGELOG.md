# 变更记录

## v0.3.0 — 2026-10-25

- 新增 `skills/first-principles`：第一性原理寻优（真实目标还原、事实基座、假设拆解、最小充分系统、候选解对比、最小验证、决策点），含方法细则、案例走查与决策备忘模板；新增 `evals/first-principles/` 两个 case 与 8 条机械判据。
- 新增 `rules/skills.md`：技能 frontmatter 与 500 字符描述上限、正文结构、路由边界、安装/更新/卸载、版本与评测。
- `rules/project-structure.md` 重写为通用规范：A/B/C 三种 profile、根文件白名单、目录规则与变更流程；移除准备区路径依赖，中文文件名与 ADR 命名统一为「同项目一致」。结构变更记录见 `docs/adr/0001`。
- 新增仓库根 `AGENTS.md`、`docs/`（ADR）、`evals/`。
- 新增 `tools/install_skills.py`：零依赖安装器，支持 `--check` 比对漂移（按行尾归一）、`--dry-run`、`--uninstall`、指定技能与安装目录；校验失败中止。
- `tools/bootstrap.py` 增加 `--check` / `--update`：报告项目侧检查器漂移，按需覆盖。
- `tools/check_artifacts.py`：只有中/低风险时输出 `WARN`（退出码 0），不再与 `FAIL` 混用；豁免目录改为按扫描根相对路径判断，修掉祖先目录同名的整项目误跳过。
- 三个技能脚本（`probe_inputs.py`、`bench_stats.py`、`diff_harness.py`）加载目标模块时注册 `sys.modules`，修复 Python 3.14 下 `@dataclass` 目标无法加载。
- README 更新为四款技能、安装器用法与检查器三种结果；`templates/AGENTS.md` 增加资产仓与技能入口。
- 三款既有技能的路由表接入 `first-principles`，`metadata.version` 升至 0.2.0；`function-spec` 描述补「审函数 / 契约写清楚 / 29 条规则」触发语。

## v0.2.2 — 2026-10-18

## v0.2.2 — 2026-10-18

- 仓库更名为 `lap-skills-rules`（旧地址自动跳转）。
- README、AGENTS 模板、项目根与准备区的引用同步到新地址。
- 内容与 v0.2.1 一致。

## v0.2.1 — 2026-10-18

- 新增 `tools/bootstrap.py`：一键开工，把检查器装进新项目并生成/追加 `AGENTS.md`。
- 新增 `templates/AGENTS.md`：新项目常驻规则模板（含项目名占位）。
- README 增加「怎么下载」「新项目开工（一键）」两节，目录树更新。

## v0.2.0 — 2026-10-18

- 新增 `rules/delivery.md`：交付物通道规范（判据、四条通道、五类症状、豁免、检查方式）。
- 新增 `rules/project-structure.md`：项目结构规范全文（来源：准备区 v1.0.1）。
- 新增 `tools/check_artifacts.py`：零依赖交付物检查器（8 条规则，内置 5 例自检，支持行内豁免标记）。
- `README.md` 改为总入口：规矩与技能一页索引。
- 技能内容未改。

## v0.1.0 — 2026-10-18

- 三款技能首发：`function-spec`、`function-attack`、`perf-evidence`。
