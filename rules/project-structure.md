# 项目结构规范

> 一句话：顶层目录是显式决策，不是顺手创建；根文件只放白名单。

## 适用范围

- 本规范约束长期项目根与资产仓；唯一真源是本文件。
- 项目根 `AGENTS.md` 是摘要；项目内的结构检查脚本（如有）是执行器。两者与本文冲突时以本文为准。
- 新项目不要求目录全建；按规模与用途选下面的 A/B/C 三种 profile，只建真用到的。

## 这条规范解决什么问题

结构腐化通常不是「写错代码」，而是三件小事：

1. 临时资料随手新建一个顶层文件夹，三个月后没人知道该不该删；
2. 同一个东西放两处，后面不知道哪份是真的；
3. 早期没有约定，每来一个任务就多一种目录命名。

用三层机制压住它：

| 机制 | 载体 | 作用 | 生效时机 |
|---|---|---|---|
| 宪法 | 本文件 | 定义合法目录集合、落位、变更流程 | 做结构决策时查 |
| 常驻提示 | 项目根 `AGENTS.md` | 每次会话提醒「先落位、再动手」 | 每次会话 |
| 机器检查 | 项目内检查脚本（如有） | 把规则变成 0/1 判据 | 交付前 |

## 三种 profile

| | A · 小型项目 | B · 平台 / 应用项目 | C · 资产仓 |
|---|---|---|---|
| 适用 | 工具、文档、一次性研究 | 有运行时代码、插件、持久化、部署 | 规范、技能、模板、检查器的唯一起源 |
| 顶层目录 | `docs/`、`research/`、`scripts/`、`archive/`（按需） | A 的全部，加 `core/`、`plugins/`、`storage/`、`contracts/`、`tests/`、`config/` 中真用到的 | `rules/`、`tools/`、`templates/`、`skills/`、`evals/`、`docs/`（按需）、`scripts/`、`archive/` |
| 根文件 | `README.md`、`AGENTS.md`、`.gitignore` + Python 配置 | 同 A；可按需加 `TASKS.md`、`DEBT.md`、`CHANGELOG.md` | 同 A；加 `CHANGELOG.md`、`.gitattributes` |
| 升级 | 出现第二个可部署单元或插件时升 B | — | 技能超过 1 个或开始对外分发时用 C |

升级或新增目录走「变更流程」，在 `docs/adr/` 留一条决策；日常任务（在已有目录下新建文件）不算结构变更。

## 顶层地图

### Profile A

```text
<项目根>\
├─ AGENTS.md            # 常驻硬约束（摘要）
├─ README.md            # 人看的总入口
├─ .gitignore
├─ pyproject.toml       # Python 工具配置（可选）
├─ docs/                # 稳定文档 + adr/
├─ research/            # 按日期归档的调研
├─ scripts/             # 零依赖小工具（平铺）
└─ archive/             # 冻结快照
```

### Profile B

```text
<项目根>\
├─ AGENTS.md / README.md / TASKS.md / DEBT.md / .gitignore / pyproject.toml
├─ contracts/           # 契约：接口、schema、错误码（唯一真源）
├─ core/                # 运行时核心
├─ plugins/             # 插件实现
├─ storage/             # 持久化与迁移
├─ config/              # 默认值与运行配置
├─ tests/               # 测试（含 scenarios/）
├─ docs/                # 稳定文档 + adr/
├─ scripts/             # 门禁与零依赖小工具
└─ archive/             # 冻结快照
```

### Profile C

```text
<资产仓根>\
├─ AGENTS.md / README.md / CHANGELOG.md / .gitignore / .gitattributes
├─ rules/               # 规范全文（唯一真源）
├─ tools/               # 检查器、安装器、一键开工（零依赖）
├─ templates/           # 新项目模板
├─ skills/<name>/       # 可安装技能
├─ evals/<name>/        # 技能最小评测
├─ docs/                # 稳定文档 + adr/
├─ scripts/             # 仓库自用零依赖小工具（按需）
└─ archive/             # 冻结快照
```

## 根文件

必需：`README.md`（总入口）、`AGENTS.md`（常驻硬约束）、`.gitignore`。

按需：`pyproject.toml`、`requirements*.txt`、`*.lock`、`.python-version`、`.importlinter`、`.gitattributes`；说明类只允许 `TASKS.md`、`DEBT.md`、`CHANGELOG.md`。

- 工具配置写进 `pyproject.toml` 的 `[tool.*]`，不在根目录散落 `pytest.ini`、`ruff.toml`、`mypy.ini`。
- 同一信息只有一份：任务进 `TASKS.md`，债务进 `DEBT.md`，变化进 `CHANGELOG.md`，不要三处各写。
- 新增其他根文件类型走变更流程。

隐藏/工具元数据目录不参与结构检查：`.git/`、`.github/`、`.dsh/`、`.dsh-memory/`、`.agents/`、`.venv/`、`.tmp/`、`.research/`、`.import_linter_cache/`、`__pycache__/`、`.pytest_cache/`、`.ruff_cache/`、`.mypy_cache/`。

## 各目录规则

### `docs/`：稳定文档

- 放：结论已稳定、需要反复引用或作为决策依据的内容。
- 不放：调研过程、草稿、一次性输出、技能正文。
- 根目录只允许 `.md`；子目录按主题命名，`adr/` 为固定目录；新增主题子目录在 `docs/` 索引或 README 登记，不散落并行副本。
- ADR：模板 `0000-template.md`；正式记录 `NNNN-<短名>.md`，四位编号从 `0001` 递增；短名中文或英文 kebab 均可，同一项目保持一致；一个 ADR 只记一个决策；已接受的 ADR 不改正文，结论变化时新建并标 `Superseded by ...`；编号不重复。
- 术语一旦有歧义，写进 `docs/GLOSSARY.md`。

### `research/`：按日期归档的调研

- 放：一次信息收集任务的原始证据、分析稿、来源、核验记录。
- 不放：已稳定的结论（提炼后进 `docs/` 或 `skills/`）。
- 一次任务一个目录：`YYYY-MM-DD-主题/`；目录内固定入口 `00-README.md`（问题、范围、结论摘要，必须），明细 `01-…` 按编号排，核验 `98-verify.md`，来源 `sources.md`，附件只放 `assets/`。
- 完成后在 `research/README.md` 索引表加一行；不移动、不覆盖旧任务；要保留旧版就整目录复制进 `archive/`。

### `skills/` 与 `evals/`：仅技能仓库

- `skills/<name>/SKILL.md` 是技能唯一来源；写法、安装、更新见 `rules/skills.md`。
- 目录名小写 kebab-case；`SKILL.md` 文件名固定大写；子目录只允许 `references/`、`scripts/`、`templates/`、`assets/`。
- `evals/<name>/` 与技能同名，放可重跑的评测材料；没有对应技能的 eval 目录不允许存在。
- 版本号不进目录名；旧版本进 `archive/`。

### `scripts/`：零依赖小工具

- 放：单文件、可独立运行、零第三方依赖的工具。
- 不放：业务代码、依赖包、需要多文件模块的工程。
- 只允许平铺文件，扩展名限 `.py`、`.ps1`、`.sh`、`.md`；每个脚本能用 `--help` 说明用法。
- 脚本不往项目根写日志/临时文件，临时输出写 `.tmp/`。

### `archive/`：冻结快照

- 放：被取代的旧技能版本、旧调研、旧文档、需要留痕的整目录快照。
- 不放：还在修改的东西。
- 一个快照一个目录：`YYYY-MM-DD-<说明>/`；目录内保持原样；建议带 `README.md` 写清冻结了什么、为什么、替代品在哪。
- 删除任何东西前，确认 `archive/` 里已有可用副本。

### Profile B 的代码目录

- `contracts/` 是接口/schema/错误码的唯一真源；`core/`、`plugins/` 只能引用，不能各写一份。
- `core/` 按能力分模块，不按技术层堆文件；`plugins/` 一个插件一个目录。
- `tests/` 与源码目录结构对应；跨模块场景测试放 `tests/scenarios/`。
- `config/` 只放默认值与配置 schema，不放密钥。

## 新东西放哪：决策表

| 要放的东西 | 落位 | 例子 |
|---|---|---|
| 一次信息收集 | `research/YYYY-MM-DD-主题/` | `research/2026-10-18-项目架构规范/` |
| 稳定规范/结论 | `docs/` | `docs/10-工程宪法.md` |
| 改变结构的决定 | `docs/adr/NNNN-<slug>.md` | `docs/adr/0001-分层与目录结构.md` |
| 技能正文 | `skills/<name>/SKILL.md` | `skills/function-spec/SKILL.md` |
| 技能评测 | `evals/<name>/` | `evals/function-spec/cases/` |
| 小工具 | `scripts/` | `scripts/gate.py` |
| 临时文件 | `.tmp/` | `.tmp/scratch.md` |
| 旧版本/冻结物 | `archive/YYYY-MM-DD-说明/` | `archive/docs-v1-2026-10-23/` |
| 上表都不合适 | **停**：写 ADR，问用户 | 不要先建目录 |

## 命名规则

| 对象 | 规则 | 正例 | 反例 |
|---|---|---|---|
| 顶层目录 | 小写英文 | `research` | `Research`、`资料` |
| 根说明文件 | 白名单内 | `README.md` | `NOTES.md`、`todo.txt` |
| Python 配置 | 根只放 `pyproject.toml` 等白名单 | `pyproject.toml` | `pytest.ini`、`ruff.toml` |
| 技能目录 | 小写 kebab-case | `function-attack` | `FunctionAttack`、`func_attack` |
| 技能文件 | `SKILL.md` 固定大写 | `SKILL.md` | `skill.md`、`README.md` |
| 调研目录 | 日期 + 主题 | `2026-10-18-项目架构规范` | `项目架构`、`new-research` |
| ADR | 四位编号 + 中文或英文短名，项目内统一 | `0002-add-health-endpoint.md`、`0002-健康检查接口.md` | `ADR-2.md`、`决策2.md` |
| 普通文档 | 入口固定大写；编号文档 `NN-标题.md`，项目内统一 | `GLOSSARY.md`、`10-工程宪法.md` | `最终版.md`、`v2.md` |

- 文件名里的空格、`final`/`new`/`副本` 会让引用不稳定；版本变化进 `archive/`。
- 一个文件只做一件事；不建 `misc/`、`other/`、`temp/` 这类兜底目录。
- 目录名与代码文件名用英文；文档文件名与正文可用中文，同一项目保持一致。

## 生命周期

### 调研

1. 建 `research/YYYY-MM-DD-主题/`，写 `00-README.md`。
2. 边写明细边记 `sources.md`。
3. 独立核验，写 `98-verify.md`。
4. 在 `research/README.md` 加索引行。
5. 结论稳定后提炼进 `docs/` 或 `skills/`；调研目录保留作证据。

### 技能

1. 在 `skills/<name>/` 写 `SKILL.md`（触发条件、步骤、完成判据），按 `rules/skills.md` 执行。
2. 长内容放 `references/`，脚本放 `scripts/`，骨架放 `templates/`。
3. 在 `evals/<name>/` 建最小评测。
4. 评测通过后运行 `python tools/install_skills.py` 安装。
5. 大改前把旧版复制到 `archive/YYYY-MM-DD-<name>-vN/`。

### 归档

1. 复制要冻结的整个目录到 `archive/YYYY-MM-DD-<说明>/`。
2. 在快照里写 `README.md`：冻结原因、替代品路径、日期。
3. 原位置继续演进或删除；历史只读。

## 变更流程

### 什么算结构变更

满足任一条即算，必须走 ADR：

- 新增/删除顶层目录或根文件；
- 新增一种第二层目录类型（例如在 `docs/` 下加 `design/`）；
- 移动、重命名已有目录；
- 修改命名规则、目录准入条件、检查脚本的强制项；
- 引入新依赖/工具，导致需要新的顶层目录；
- 在 A/B/C 三种 profile 之间切换。

日常任务不算：在已有 `research/` 下建日期目录、在 `skills/` 下建新技能、在 `evals/` 下建同名评测、在 `scripts/` 加单文件工具。

### 步骤

1. 判断是否结构变更。
2. 写 ADR：复制模板，编号取当前最大号 +1；写背景、决策、备选、后果。
3. 问用户：一次只问这一个决策点；同意后状态改 `accepted`。
4. 改三处：本文件（版本号 + 对应章节）、项目 `AGENTS.md` 摘要、项目内结构检查脚本。
5. 验证：跑检查脚本；再用 `.tmp/` 造一个违规样例确认返回非 0，然后删掉样例。
6. 留痕：更新 `README.md` 目录树（如果变了），在项目记忆里记一条决策。

### 版本规则

- MAJOR：顶层目录集合变化（增删根目录/根文件）。
- MINOR：新增第二层类型、命名规则或检查项。
- PATCH：措辞、示例、链接修正。

版本历史见仓库 `CHANGELOG.md`，本文件只描述当前规则。

## 机器检查

- 本仓库随附 `tools/check_artifacts.py`（交付物检查），不随附结构检查器。
- 结构检查由项目自建并接入项目门禁；检查项至少覆盖：顶层目录/根文件白名单、ADR 命名与编号、`research/` 入口文件、`skills/` 的 `SKILL.md` 与目录名一致、`evals/` 同名约束、`scripts/` 平铺。
- 退出码 0 = 通过；非 0 = 按输出「改法」处理，不绕过脚本。结构检查不判断内容质量，内容靠评审与交付物检查。

## 为什么不是别的方案

| 方案 | 为什么不选 |
|---|---|
| 照搬 GitHub Spec Kit 全套 | 面向「功能开发 + 规格驱动」，会引入 `.specify/`、命令模板、多阶段工作流；本工作流用不上，只借「宪法 + 计划前检查」的思路。 |
| 只写 `AGENTS.md` | 常驻提醒能降低概率，但没有历史与机器判据，模型仍可能「这次特殊」就新建目录。 |
| 只写一份 `README` | 纯说明，无约束力，也无人检查。 |
| 做成一个 DSH 技能 | 技能靠 `description` 触发，只在相关任务加载；结构规则需要每个任务都生效，必须常驻。 |
| 什么都不加，靠自觉 | 这正是要解决的问题。 |

## 上游来源

本规范是改写，不是复制；只借结构与方法，正文按本工作流重写。来源与借用边界见 `CHANGELOG.md` 的版本记录。

| 上游 | 许可 | 借了什么 | 没借什么 |
|---|---|---|---|
| [github/spec-kit · constitution](https://github.com/github/spec-kit/blob/main/.specify/memory/constitution.md) | MIT | 「宪法 + 计划前检查」的治理思路 | 具体条文、`.specify/` 工作流 |
| [agentsmd/agents.md](https://github.com/agentsmd/agents.md) | MIT | 根目录 `AGENTS.md` 作为智能体入口 | 网站与示例正文 |
| [architecture-decision-record](https://github.com/architecture-decision-record/architecture-decision-record) | NOASSERTION（只借概念） | ADR 的目的、Nygard 结构、一决策一记录、supersede 而非改写 | 模板原文 |
| [anthropics/skills](https://github.com/anthropics/skills) | 混合（各技能自带许可） | `skills/<name>/SKILL.md` 的平铺布局先例 | 任何技能内容 |

## 已知边界

- 不强制所有项目建满目录；目录越少越好，缺的按 profile 升级。
- 没有统一 CI；结构检查在任务结束前手动跑，或在项目门禁里复用。
- 中文主题名只允许在 `research/` 目录名；文档文件名与正文可用中文，同一项目保持一致。
- 本文件不是法律；出现「这次情况特殊」时，先走 ADR，再改规范。规范的价值是变更可见，不是永不变化。
