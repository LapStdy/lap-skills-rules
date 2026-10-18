> **来源与适用范围**
>
> 本文是准备区的结构规范原文（v1.0.1），约束 D:\lap-backstop-prep。
> 新项目可照这个思路裁剪（顶层目录准入 + 根文件白名单 + 落位顺序 + 变更留痕），不必照搬 6 个目录。
> 执行器 check_structure.py 留在准备区；本仓库只保存规范文本。

# 准备区结构宪法（lap-backstop-prep）

- 版本：**1.0.1**
- 生效日期：**2026-10-18**
- 状态：accepted（目录规则见 [adr/0001-project-structure.md](adr/0001-project-structure.md)；搬迁见 [adr/0002-prep-workspace-move.md](adr/0002-prep-workspace-move.md)）
- 适用范围：本规范只约束准备区 `D:\lap-backstop-prep`；长期项目根 `D:\lap-backstop` 尚未启动，不适用。
- 唯一真源：本文件。`AGENTS.md` 是摘要，`scripts/check_structure.py` 是执行器；两者与本文冲突时以本文为准。

## 一句话

顶层只允许 **6 个目录 + 3 个说明文件**，以及白名单内的 Python 项目配置；任何新目录都是一次显式决策，不是顺手创建。

## 这条宪法解决什么问题

准备区里，模型（和人）最常发生的结构腐化不是“写错代码”，而是：

1. 临时资料随手新建一个顶层文件夹，三个月后没人知道该不该删；
2. 同一个东西放两处（`notes/`、`docs/`、`research/` 各一份），后面不知道哪份是真的；
3. 早期没有约定，后期每来一个任务就多一种目录命名。

这套规范用三个机制压住它：

| 机制 | 文件 | 作用 | 生效时机 |
|---|---|---|---|
| 宪法 | `docs/PROJECT-STRUCTURE.md`（本文件） | 定义唯一合法的目录集合、落位规则、变更流程 | 做结构决策时查 |
| 常驻提示 | `AGENTS.md` | 每次会话都提醒模型「先落位、再动手」 | 每次会话首次请求 |
| 机器检查 | `scripts/check_structure.py` | 把规则变成 0/1 可执行判据，拦住手滑 | 任务结束前 |

这三层分别对应 GitHub Spec Kit 的“宪法 + 计划前检查”、AGENTS.md 格式的“根目录常驻说明”、ADR 社区的“fitness function（把决策变成自动检查）”。来源见文末。

## 顶层地图

```text
D:\lap-backstop-prep\
├─ AGENTS.md                  # 准备区硬约束（摘要）
├─ README.md                  # 人看的总入口
├─ .gitignore
├─ pyproject.toml             # Python 工具配置（可选）
├─ requirements-dev.txt       # 开发/评测依赖（可选）
├─ docs/                      # 稳定文档
│  ├─ PROJECT-STRUCTURE.md    # 本文件（唯一真源）
│  ├─ ENVIRONMENT.md          # 环境/工具链
│  ├─ HANDOFF.md              # 会话交接
│  └─ adr/                    # 架构决策记录
│     ├─ 0000-template.md
│     ├─ 0001-project-structure.md
│     └─ 0002-prep-workspace-move.md
├─ research/                  # 按日期归档的调研
│  ├─ README.md               # 调研索引（每任务一行）
│  ├─ 2026-10-18-函数规范与测试技能/
│  ├─ 2026-10-18-项目架构规范/
│  └─ 2026-10-18-多会话团队编排/
├─ skills/                    # 技能源（可安装）
│  └─ <skill-name>/
│     ├─ SKILL.md
│     ├─ references/          # 可选：按需加载的长文
│     ├─ scripts/             # 可选：技能自带脚本
│     └─ templates/           # 可选：模板
├─ evals/                     # 技能的最小评测
│  └─ <skill-name>/
│     ├─ README.md            # 怎么跑
│     ├─ cases/               # 输入 + 期望
│     └─ fixtures/            # 可选：固定样本
├─ scripts/                   # 零依赖小工具（平铺）
│  ├─ check_structure.py
│  └─ run_evals.py
└─ archive/                   # 冻结快照
   └─ YYYY-MM-DD-<说明>/
```

## 各目录规则

### 根文件

根目录只允许 3 个说明文件：

- `AGENTS.md`：常驻硬约束（本文件的摘要）；
- `README.md`：人看的总入口；
- `.gitignore`：生成物与系统垃圾。

以及以下 Python 项目配置（Phase 2 起按需出现）：

- `pyproject.toml`：项目元数据、依赖、所有工具配置（`[tool.pytest]`、`[tool.ruff]` 等）；
- `requirements*.txt`：不用 `pyproject.toml` 时的依赖清单；
- `*.lock`：包管理器锁文件；
- `.python-version`：Python 版本锁定。

其他工具配置写进 `pyproject.toml` 的 `[tool.*]`，不在根目录散落 `pytest.ini`、`ruff.toml`、`mypy.ini`。新增根文件类型走变更流程。

隐藏/工具元数据目录（结构检查跳过）：`.git/`、`.github/`、`.dsh/`、`.dsh-memory/`、`.agents/`、`.venv/`、`.tmp/`、`__pycache__/`、`.pytest_cache/`。

### `docs/`：稳定文档

- **放**：结论已经稳定、需要被反复引用或作为决策依据的内容。
- **不放**：调研过程、草稿、一次性输出、技能正文（技能在 `skills/`）。
- `docs/` 根目录只允许 `.md` 文件；`PROJECT-STRUCTURE.md` 必须存在。
- 子目录只允许 `adr/`。需要新的文档子目录时，走变更流程。
- 根目录的 `GLOSSARY.md`（术语表）按需创建；术语一旦有歧义就写进去。
- ADR 文件：
  - 模板固定为 `0000-template.md`；
  - 正式记录命名为 `NNNN-<kebab-slug>.md`，四位编号，从 `0001` 递增；
  - 一个 ADR 只记一个决策；
  - 已接受的 ADR 不修改正文；结论变化时新建 ADR，并在旧 ADR 标 `Superseded by ...`。
- 编号不允许重复；检查脚本会查。

### `research/`：按日期归档的调研

- **放**：一次信息收集任务的原始证据、分析稿、来源、核验记录。
- **不放**：已稳定的结论（提炼后进 `docs/` 或 `skills/`）、技能正文。
- 一次任务一个目录：`YYYY-MM-DD-主题/`；主题可用中文，日期前缀必须是 `YYYY-MM-DD`。
- 任务目录内固定入口与命名：
  - `00-README.md`：问题、范围、结论摘要（**必须**）；
  - `01-…`、`02-…`：研究明细，按编号排；
  - `98-verify.md`：独立核验记录；
  - `sources.md`：来源清单；
  - `assets/`：图片、PDF 等附件（唯一允许的子目录）。
- 任务完成后，在 `research/README.md` 的索引表追加一行；不移动、不覆盖旧任务。
- 已完成任务不删除。需要保留旧版本时，把整个任务目录复制到 `archive/`，不要原地改历史。

### `skills/`：技能源

- **放**：可安装技能的唯一源文件。技能目录名用小写 kebab-case，功能名要具体。
- **不放**：已安装副本、评测用例（在 `evals/`）、临时脚本。
- 每个技能必须有 `skills/<name>/SKILL.md`；frontmatter 至少包含 `name` 和 `description`，且 `name` 与目录名一致。
- 可选子目录只有：`references/`、`scripts/`、`templates/`、`assets/`。
- DSH 的用户级技能路径是 `~/.dsh/skills/<name>/SKILL.md` 或 `<name>.md`，**不递归扫描嵌套的 `SKILL.md`**；项目级 `.dsh/skills/` 也能被识别，但本准备区**不建**项目级技能目录，避免同一技能两套真源。本准备区的 `skills/<name>/` 安装时必须拍平到 `~/.dsh/skills/<name>/`。
- 安装方式：复制目录到 `~/.dsh/skills/<name>/`；仓库始终是源，安装副本不反向复制回来。
- 命名禁区：`my-skill`、`test`、`new`、`temp` 这类泛名；版本号不进目录名（旧版本进 `archive/`）。

### `evals/`：最小评测

- **放**：证明技能有效/无效的可重跑材料。
- 目录名必须与 `skills/` 下的技能同名；没有对应技能的 eval 目录会被检查脚本拦下。
- 建议结构：`README.md`（怎么跑、判据）、`cases/`（prompt + 好例/坏例）、`fixtures/`（固定输入）。`expected/` 可作为 `cases/` 的补充。
- 一个技能至少有一个 case，才能称为“可交付”。Phase 2 会在这里落第一个最小 eval。
- eval 只依赖标准库或项目虚拟环境；不把外部服务写进必需路径。

### `scripts/`：零依赖小工具

- **放**：单文件、可独立运行、零第三方依赖的工具。
- **不放**：业务代码、依赖包、需要多文件模块的工程。
- 只允许平铺文件；扩展名限 `.py`、`.ps1`、`.sh`、`.md`。多文件工具需要新目录时走变更流程。
- 每个脚本要能用 `--help` 说明用法；`check_structure.py` 必须存在。
- 脚本不写准备区根目录以外的位置（日志/临时文件写 `.tmp/`）。

### `archive/`：冻结快照

- **放**：被取代的旧技能版本、旧调研、旧文档、需要留痕的整目录快照。
- **不放**：还在修改的东西。
- 一个快照一个目录：`YYYY-MM-DD-<说明>/`；目录内保持原样，不再修改。
- 快照目录建议带 `README.md`，写清“冻结了什么、为什么冻结、替代品在哪”。
- 删除任何东西前，先确认 `archive/` 里已有可用副本。

## 新东西放哪：决策表

| 你要放的东西 | 落位 | 例子 |
|---|---|---|
| 一次新的信息收集 | `research/YYYY-MM-DD-主题/` | `research/2026-10-18-项目架构规范/` |
| 稳定的规范/结论 | `docs/` | `docs/PROJECT-STRUCTURE.md` |
| 改变结构的决定 | `docs/adr/NNNN-<slug>.md` | `docs/adr/0001-project-structure.md` |
| 技能正文 | `skills/<name>/SKILL.md` | `skills/function-spec/SKILL.md` |
| 技能评测 | `evals/<name>/` | `evals/function-spec/cases/` |
| 小工具 | `scripts/` | `scripts/check_structure.py` |
| 临时文件 | `.tmp/` | `.tmp/scratch.md` |
| 旧版本/冻结物 | `archive/YYYY-MM-DD-说明/` | `archive/2026-11-01-旧版规范/` |
| 上表都不合适 | **停**：写 ADR，问用户 | 不要先建目录 |

## 命名规则

| 对象 | 规则 | 正例 | 反例 |
|---|---|---|---|
| 顶层目录 | 小写英文，固定 6 个 | `research` | `Research`、`资料` |
| 根说明文件 | 固定 3 个 | `README.md` | `NOTES.md`、`todo.txt` |
| 根配置文件 | 仅 `pyproject.toml`、`requirements*.txt`、`*.lock`、`.python-version` | `pyproject.toml` | `pytest.ini`、`ruff.toml`（写进 pyproject 的 `[tool.*]`） |
| 技能目录 | 小写 kebab-case | `function-attack` | `FunctionAttack`、`func_attack` |
| 技能文件 | `SKILL.md` 固定大写 | `SKILL.md` | `skill.md`、`README.md` |
| 调研目录 | 日期 + 主题 | `2026-10-18-项目架构规范` | `项目架构`、`new-research` |
| ADR | 四位编号 + 英文 kebab | `0002-add-perf-evidence-skill.md` | `ADR-2.md`、`决策2.md` |
| 普通文档 | 小写 kebab 或固定大写入口 | `GLOSSARY.md` | `最终版.md`、`v2.md` |

补充：

- 文件名用空格、大写、`final`/`new`/`副本` 都会让引用不稳定；版本变化用 `archive/`。
- 一个文件只做一件事；不要建 `misc/`、`other/`、`temp/` 这类兜底目录。
- 中文只允许出现在 `research/` 的主题名和文档正文里；代码、技能、ADR 文件名用英文。

## 生命周期

### 调研

1. 建 `research/YYYY-MM-DD-主题/`。
2. 写 `00-README.md`（问题、范围、方法）。
3. 写 `01-…` 等明细，边写边记 `sources.md`。
4. 独立核验，写 `98-verify.md`。
5. 在 `research/README.md` 加索引行。
6. 结论稳定后，把可复用部分提炼进 `docs/` 或 `skills/`；调研目录保留作证据。

### 技能

1. 在 `skills/<name>/` 写 `SKILL.md`（触发条件、步骤、完成判据）。
2. 长内容放 `references/`，按需加载；脚本放 `scripts/`。
3. 在 `evals/<name>/` 建最小 eval，先证明能触发、能产出合格结果。
4. 评测通过后，复制到 `~/.dsh/skills/<name>/` 安装。
5. 技能有大改时，旧版本复制到 `archive/YYYY-MM-DD-<name>-vN/`，再改源。

### 评测

1. 一个技能一个目录，目录名与技能一致。
2. 每个 case 至少写清：输入（prompt/文件）、合格输出、不合格输出。
3. 评测结果可重跑；固定样本进 `fixtures/`，不要依赖外部链接。

### 归档

1. 复制要冻结的整个目录到 `archive/YYYY-MM-DD-<说明>/`。
2. 在快照里写 `README.md`：冻结原因、替代品路径、日期。
3. 原位置继续演进或删除；历史只读。

## 变更流程

### 什么算“结构变更”

满足任一条就是结构变更，必须走 ADR：

- 新增/删除顶层目录或根文件；
- 新增一种第二层目录类型（例如在 `docs/` 下加 `design/`）；
- 移动、重命名已有目录；
- 修改命名规则、目录准入条件、检查脚本的强制项；
- 引入新的依赖/工具，导致需要新的顶层目录。

日常任务不算：在已有 `research/` 下建日期目录、在 `skills/` 下建新技能、在 `evals/` 下建同名评测、在 `scripts/` 加单文件工具。

### 步骤

1. **判断**：按上一节确认是否结构变更。
2. **写 ADR**：复制 `docs/adr/0000-template.md`，编号取当前最大号 +1；写背景、决策、备选方案、后果。
3. **问用户**：一次只问这一个决策点；用户同意后状态改 `accepted`。
4. **改三处**：本文件（版本号 + 对应章节）、`AGENTS.md` 摘要、`scripts/check_structure.py` 规则。三处改完才算完成。
5. **验证**：运行 `python scripts/check_structure.py`；再用 `.tmp/` 造一个违规样例，确认脚本会返回 1，然后删掉样例。
6. **留痕**：更新 `README.md` 的目录树（如果变了）；在项目记忆里记一条决策。

### 版本规则

- **MAJOR**：顶层目录集合变化（增删根目录/根文件）。
- **MINOR**：新增第二层类型、命名规则或检查项。
- **PATCH**：措辞、示例、链接修正。

| 版本 | 日期 | 变更 |
|---|---|---|
| 1.0.0 | 2026-10-18 | 初版：6 目录 + 3 个说明文件 + 预留 Python 配置；ADR 流程；结构检查脚本 |
| 1.0.1 | 2026-10-18 | 准备区迁至 `D:\lap-backstop-prep`（ADR 0002）；适用范围改为准备区；路径与依赖清单名修正 |

## 机器执行：`scripts/check_structure.py`

它只做机械判据，不判断内容质量。检查项：

- 顶层没有未登记目录/文件；
- 根目录只有 3 个说明文件 + 白名单内的 Python 配置；
- `docs/PROJECT-STRUCTURE.md` 与 `docs/adr/0000-template.md` 存在；
- ADR 命名合法、编号不重复；
- `research/` 根只有 `README.md`，任务目录名合法且含 `00-README.md`；
- `skills/` 下每个目录都有 `SKILL.md`，frontmatter 的 `name` 与目录名一致；
- `evals/` 目录都能在 `skills/` 找到同名技能；
- `scripts/` 平铺且扩展名合法；
- 没有 `*.tmp`、`~$*`、`.DS_Store`、`Thumbs.db` 等垃圾文件。

它**不检查**：文件内容是否放对语义位置、ADR 质量、eval 是否真的有效。这些靠 ADR 评审和人工复核。

运行：

```bash
python scripts/check_structure.py
```

- 退出码 0：通过。
- 退出码 1：有问题，按每条输出的“改法”处理。
- 失败时不要绕过脚本；修结构或补 ADR，二选一。

## 为什么不是别的方案

| 方案 | 为什么不选 |
|---|---|
| 照搬 GitHub Spec Kit 全套 | 它面向“功能开发 + 规格驱动”，会引入 `.specify/`、命令模板、多阶段工作流；本准备区是技能研究仓，太重。只借“宪法 + 计划前检查”的思路。 |
| 只写 `AGENTS.md` | 常驻提醒能降低概率，但没有历史（为什么这样定）和机器判据，模型仍可能“这次特殊”就新建目录。 |
| 只写一份 `README` | 纯说明，无约束力，也无人检查。 |
| 做成一个 DSH 技能 | 技能靠 `description` 触发，只在相关任务被加载；结构规则需要每个任务都生效，必须常驻。 |
| 什么都不加，靠自觉 | 这正是要解决的问题。 |

## 上游来源与借用边界

本规范是**改写**，不是复制。只借结构与方法；正文按本准备区重写。完整来源清单见 [research/2026-10-18-项目架构规范/sources.md](../research/2026-10-18-项目架构规范/sources.md)。

| 上游 | 许可 | 借了什么 | 没借什么 |
|---|---|---|---|
| [github/spec-kit · constitution](https://github.com/github/spec-kit/blob/main/.specify/memory/constitution.md) | MIT | “宪法”作为绑定原则、治理与版本化、计划前检查的思路 | 具体原则条文、`.specify/` 工作流 |
| [github/spec-kit · AGENTS.md](https://github.com/github/spec-kit/blob/main/AGENTS.md) | MIT | 常驻文件只放“按任务分支指向设计文档”的短指针 | 它的仓库专属规则 |
| [agentsmd/agents.md](https://github.com/agentsmd/agents.md) | MIT | 根目录 `AGENTS.md` 作为智能体可预测的入口 | 网站与示例正文 |
| [architecture-decision-record](https://github.com/architecture-decision-record/architecture-decision-record) | NOASSERTION（只借概念，不复制） | ADR 的目的、Nygard 结构、一决策一记录、supersede 而非改写 | 模板原文 |
| [ADR skill](https://github.com/architecture-decision-record/architecture-decision-record/tree/main/skills/architecture-decision-record-skill) | 同上 | 判断“是否需要 ADR”、命名、7 步流程 | 技能正文 |
| [anthropics/skills](https://github.com/anthropics/skills) | 混合（各技能自带许可） | `skills/<name>/SKILL.md` 的平铺布局先例 | 任何技能内容 |
| 本机 DSH 运行时 | — | 实测确认：DSH 加载准备区根到当前目录的 `AGENTS.md`；技能扫描规则见 `research/2026-10-18-函数规范与测试技能/04-skills.md` | — |

## 已知边界

- 当前不是 git 仓库；`.gitignore` 已准备好，初始化后即可用。检查脚本不依赖 git。
- 还没有 CI；结构检查目前靠任务结束前手动跑。以后可在 git hook 或 CI 里复用同一个脚本。
- `.dsh/`、`.dsh-memory/`、`.agents/`、`.venv/` 等工具/生成目录不在结构讨论范围；检查脚本会跳过。
- 中文主题名只允许在 `research/`；其他位置用英文 kebab，避免跨平台和引用问题。
- 本文件不是法律；出现“这次情况特殊”时，先走 ADR，再改规范。规范的价值在于变更可见，而不是永不变化。
