# 变更记录

## v0.7.0 — 2026-11-01

- `skills/zcode-auto-workflow` 升 2.1.0：把「派卡」与「接续」拆成两条流程。`references/session-handoff.md` 首屏给出对照表（要达成 / 应用 / 点哪里 / 完成后必须看到）、两个应用的三处硬区别与误点后果；判据压成一句「卡永远在 ZCode，会话永远在 DSH」。补会话命名约定 `接续#N · 项目 · 日期`。
- `SKILL.md`：`description` 与路由表补「接续」「换个会话接着盯」「上下文满了」，并写明两条流程分属两个应用；第 0 步 ZCode 侧栏术语改为「任务列表 / 项目」；停止规则补两条串台借口；完成自检补接续项；资源清单同步。
- `references/zcode-ui.md`、`references/boundary-facts.md`：各自标明只讲 ZCode 窗口内的点击，补两个应用侧栏的对照判据；ZCode 折叠项术语由「会话 / 工作区」改为「任务 / 项目」。
- `references/project-profile.md`：会话级限制点名「DSH 会话」。
- `evals/zcode-auto-workflow`：机械判据补第 9 条（接续走 DSH 新会话、派卡走 ZCode 新建任务，不串台）。

## v0.6.0 — 2026-11-01

- `skills/zcode-auto-workflow` 升 2.0.0，按 2026-11-01 首个完整值守夜的事实基座重排：主流程由 8 步压到 6 步；唤醒改为事件优先（watcher 四条件退出），定时只留给到点收尾与降级，并加「一夜空转超 2 次即删定时」判据；新增 watcher 基线盲区硬规则（启动前先看状态，已无在跑任务就直接处理）。
- 新增 `references/boundary-facts.md`：界面与真源的十类实测判据（权限查 `session.permission`、思考强度查 `model_usage.variant`、`tasks-index` 的 `mode` 列不可作判据、取帧只用窗口帧、左侧列表折叠、Esc 被占用、门禁假红、卡文不能放仓库内）。
- 变更预算改写：产品代码 ≤400 行，测试与文档不设固定上限但须在交付说明报出规模（原「单卡总 diff ≤400 行」在实测中 12/12 次被违反，规则失效）。
- 新增 `references/project-profile.md`：项目常量与首个值守夜的实测基准（单卡 30–80 分钟、一夜 12 张、派卡失败率 20%、单夜水位 +8%）。
- 接续降级为兜底并给重建清单；新增「门禁假红」判定口径。

## v0.5.0 — 2026-10-31

- 新增 `skills/zcode-auto-workflow`：ZCode 专用自动工作流（单卡派发 + 无人看管夜班），覆盖写卡、界面派卡五动作、任务状态库盯卡、复核三红线、串行门禁、合并清理、额度检查、到点收尾与会话轮换；含 5 篇 references。
- 新增 `evals/zcode-auto-workflow/`：两个 case 与机械判据。
- README 技能表、互斥路由与安装清单更新为五款技能。

## v0.4.0 — 2026-10-30

- 新增 `rules/change-scope.md`：改动范围规范（判据、四条不许、只清自己的孤儿、收件箱、人工与机械检查、为什么放在常驻层）。
- `templates/AGENTS.md` 增加「改动范围（硬规则）」三行操作版。
- README「一页看懂」增加改动范围一行；仓库根 `AGENTS.md` 的规范清单同步。

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
