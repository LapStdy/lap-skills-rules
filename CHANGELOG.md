# 变更记录

## v0.14.1 — 2026-11-02

- 新增 `LICENSE`（MIT，`Copyright (c) 2026 LapStdy`），仓库转为公开；README 加「许可证」一节，只放链接不复述条款。
- `rules/project-structure.md`：根文件白名单补 `LICENSE`（公开仓必需，私有仓可不放），Profile C 目录树同步。
- 新增 `docs/adr/0002-MIT许可证与根文件白名单.md`：记录许可证选择与白名单变更（Apache-2.0 与不放许可证两个备选的取舍）。

## v0.14.0 — 2026-11-02

- 新增四条规范，来自长期项目全量门禁与值守的实测：
  - `rules/gates.md`：完成由一条命令判定；七类检查按依赖顺序；合并前后按树判据决定门禁跑几次；假红判据（单例复跑 + 整包复跑全绿，判并行抢资源）。
  - `rules/testing.md`：四条硬规则（假件注入、断言不变量、禁逐字节比对含时间产物、新行为必须有测试），加进程/端口/文件/时间/文档即契约。
  - `rules/windows-process.md`：实测红线——Windows 上 `os.kill(pid, 0)` 的 `0` 是 `CTRL_C_EVENT`，会误杀目标并打断同一控制台的进程；测试进程内 `taskkill /T /F` 会连带结束调用者。给出内核句柄探测代码与排障判据。
  - `rules/ledger.md`：TASKS、DEBT、交接账本的分工与字段；DEBT 已还即删、未还 ≤20 笔、每月复审。
- 新增工具：
  - `tools/check_structure.py`：AST 扫函数行数、参数个数、类行数、模块行数，带允许清单（`--allow`）与 `--selftest`。
  - `tools/check_repo.py`：资产仓自洽（README 索引路径、技能 frontmatter 与目录名、评测同名、README 与 CHANGELOG 版本一致），`--check-tools` 一并跑三个检查。
  - `templates/gate.py`：项目门禁骨架（七类检查、必需与可选、失败即停、固定报告行）。
- `tools/bootstrap.py` 重写安装内容：两个检查器 + 门禁骨架 + 四段 `AGENTS.md`；`--check` 比对三类文件与三个章节的漂移。
- `templates/AGENTS.md` 增「完成判据」与「账本」两段。
- 新增技能 `skills/project-gate`（1.0.0）与评测 `evals/project-gate`（10 条机械判据）。
- `skills/zcode-auto-workflow` 升 2.8.0：卡文必查由九项升**十项**（新增「用例不打掉宿主」）；复核明确「执行者自述不算证据，主控亲自串行跑全量门禁」；回执第 7 项定夺项合并前必须答复；门禁假红补「用例把宿主打掉」一类；`references/boundary-facts.md` 工程侧边界由三条升四条；评测判据由 15 条升 18 条，判据 6 的额度检查改为对齐当日额度窗口。
- `rules/project-structure.md`：机器检查一节改为三个检查器加门禁骨架；根文件按需项加 `structure-allow.txt`。
- `rules/skills.md`：写作规则补两条——示例命令不得打掉宿主进程；引用规则只指过去、不复制正文。
- `README.md` 重写：规矩、技能、工具三分，门禁骨架与新项目三步，自检命令，目录；版本号只留 CHANGELOG 一处。
- 新增 `structure-allow.txt`：资产仓既有 11 项超限入清单（技能脚本与工具脚本），每条对应拆分工作，清单只缩不涨。

## v0.13.0 — 2026-11-02

- `skills/zcode-auto-workflow` 升 2.7.0：派卡并发上限由 2 提到 **3**（`references/project-profile.md` 的「并发上限」、`SKILL.md` 输入缺省与「并发与变更预算」同口径，含子智能体）。理由：用户 2026-11-02 决定放宽到三张，额度窗口内可多推一条独立支线。
- 额度窗口与到期收尾改为「以当日可用额度为准」：profile 不再写死 `00:00–10:00` 与 `10:00` 收尾，当日到期时刻由交接账本记录（本日为 09:00），窗口外不派新卡。
- `evals/zcode-auto-workflow`：判据 5 改为「并发上限按 profile（现为 3）与当日额度到期时刻，并声明窗口外停派」。

## v0.12.0 — 2026-11-02

- `skills/zcode-auto-workflow` 升 2.6.0：卡文「质量审查要求」新增第 5 条——**审查只能由执行者本人完成**，不得开子智能体、不得另起代理或外部会话代审、不得转交；审查账目只写本人逐条读本次 diff 与代码得出的结论，转述别人的判断不算审查。理由：审查交给子智能体或外部代理，主控只拿到二手结论，红线判断（交付物只写现状、无调试残留、新行为有测试）会失真。
- `SKILL.md`：停止规则补一条（「让子智能体先审一遍更省事」）；完成自检补一项（卡文必须写明该约束）。
- `references/card-template.md`：模板「质量审查要求」补第 5 条。
- `evals/zcode-auto-workflow`：机械判据补第 15 条与不合格特征一条，总数 15 条。

## v0.11.0 — 2026-11-02

- `skills/zcode-auto-workflow` 升 2.5.0：新增**卡文送达形态**——收件人在电脑旁时，卡文必须整段以 Markdown 代码块贴进对话窗口（可直接复制），落盘路径只作追溯；无人值守或接续换会话时才只给落盘路径与回执路径。理由：用户从窗口整段复制卡文，只给路径要多一次找文件、且容易复制到旧版本。
- `SKILL.md`：主流程第 2 步「派卡」补卡文送达判据；停止规则补一条（「卡文在文件里，你自己打开复制」）；完成自检补一项。
- `references/card-template.md`：使用要点补同口径一条。
- `evals/zcode-auto-workflow`：机械判据补第 14 条（人在电脑旁时整段贴窗口）与不合格特征一条，总数 14 条。

## v0.10.0 — 2026-11-02

- `skills/zcode-auto-workflow` 升 2.4.0：卡文首行改为 `卡<N>-<码>`，名称移到第二行。ZCode 把首句第一行当会话标题，窗口标题栏只显示这一行；码取 2 位、从 32 字符表（去 `0/O/1/I`）生成，整行 ≤7 字符，用于截图识别与多窗对账。发卡必查由八项升到九项。
- 新增收尾回执：卡文「交付纪律」要求执行者把回执落盘到 `<回执目录>\HANDOFF-card<N>-<码>.md`，字段固定七项（提交、七条门禁、PASS 文件数、行数、用例、自检、定夺项）；复核前缺回执按未完成处理。理由：执行者窗口输出主控读不到，提交说明只承载一部分证据。
- `references/project-profile.md`：新增回执目录 `D:\lap-work\.zcode\outbox\`（仓库外、worktree 删除后仍在）。
- `SKILL.md`：主流程写卡/派卡/盯卡/复核/记账五步补首行、对窗、读回执判据；输出模板补码与回执路径；完成自检补两项；停止规则补三条。
- `evals/zcode-auto-workflow`：机械判据补第 12 条（首行唯一码）与第 13 条（回执落盘与字段），总数 13 条。

## v0.9.0 — 2026-11-01

- `skills/zcode-auto-workflow` 升 2.3.0：门禁从「每卡固定两次全量」改为**按证据跑**。新增「门禁跑几次」一节：分支上必须跑一次全量；合并后仅当 `git diff --stat <分支头> <merge 提交>` 非空（主区前进过、解冲突改过内容）才跑，树相同则跳过并在回执写明理由；派卡前只在 `main` 自上次全绿后动过时才跑。
- 依据：一次全量约 210–230 秒，实测前六条合计约 5 秒、pytest（约 1400 用例）占 95%；今日三次合并的 merge 提交树与分支头树 `git diff` 均为 0 行，第二次门禁不新增信息。
- `SKILL.md`：第 0 步第 4 条、主流程第 5 步、完成自检同步改为条件式；停止规则补「合并后跑不跑看心情 → 判据是树」。
- `references/project-profile.md`：门禁说明指向新判据；`evals/zcode-auto-workflow` 补第 11 条判据（门禁按证据跑），总数 11 条。

## v0.8.0 — 2026-11-01

- `skills/zcode-auto-workflow` 升 2.2.0：卡文规范从「三项必查 + 五段」升到「**八项必查 + 七段**」。
- `references/card-template.md` 重写：必查表扩到八项（开工定位含起始 commit 与 main 头一致性、停手、现状可验收、现状→测试映射、竞争与错误语义、文档引用点、边界、预算与审查）；卡文结构定为七段（开工定位 / 现状 / 不做与边界 / 测试映射 / 文档与账目 / 交付纪律 / 质量审查）；新增「设计类卡额外槽位」（前置状态、仲裁规则、对外语义、连接归属、非正常路径、兼容回滚）、「验收判据三条铁律」（能红→绿、只描述外部可观测结果、并发正反成对）与「交接场景核对表」（起始 commit、文件路径、欠账编号、测试文件名四项实核）。
- `SKILL.md`：写卡判据改为七段齐全 + 八项全过；停止规则补四条（设计文档≠卡文、执行者不会自己补测试与账、不边跑边改卡、小卡同样适用）；完成自检补卡文必查与「卡文引用物真实存在」两项；资源清单同步。
- `evals/zcode-auto-workflow`：机械判据补第 10 条（七段 + 八项必查），总数 10 条。

## v0.7.1 — 2026-11-01

- 五个技能的 `description` 按 `rules/skills.md`（≤500 字符、触发词前置、相邻技能一行路由）重写，去掉超长描述与自我介绍式措辞：`first-principles` 305→197、`perf-evidence` 289→237、`function-attack` 243→194、`function-spec` 201→167、`memory-curation` 124→115。
- 触发词补到用户口语侧（「方案评估」「方向对不对」「加 benchmark 防回归」「返回 None 还是抛异常」「记忆太乱」等），路由边界改写成「不负责 X（技能名）」，与 `rules/skills.md` 的「同一触发词只归一个技能」对齐。
- 版本：`first-principles` 0.1.1、`function-attack`/`function-spec`/`perf-evidence` 0.2.1、`memory-curation` 1.0.1。
- `skills/memory-curation` 首次纳入版本库：此前只存在于安装副本，仓库侧无历史；本次按仓库→安装单向流程补齐。

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
