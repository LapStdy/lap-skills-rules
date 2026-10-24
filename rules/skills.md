# 技能规范（skills）

> 一句话：仓库是技能的唯一起源，安装副本只是拷贝；技能是写给模型的工序书，不是给人看的介绍。

## 技能是什么

技能是一份按需加载的工序：触发条件、步骤、完成判据、产物。它和规范的分工是：

| | 规范 | 技能 |
|---|---|---|
| 加载方式 | 常驻（`AGENTS.md` + `rules/`） | 按 `description` 触发，正文按需读取 |
| 保证 | 每次会话生效 | 只在相关任务加载 |
| 放什么 | 不许做什么、交付物长什么样 | 这类任务怎么做才算做完 |

不能保证每次生效的规则不要做成技能（理由见 `rules/delivery.md` 末节）。

## 放哪

- 源：仓库 `skills/<name>/SKILL.md`，仓库是唯一真源。
- 安装：用户级 `~/.dsh/skills/<name>/SKILL.md`（Windows 即 `C:\Users\<用户>\.dsh\skills\<name>\`）。
- 项目级 `.dsh/skills/` 也能被识别，但同一技能不要在两处各存一份；本仓库技能统一装用户级。
- 方向固定：仓库 → 安装副本，单向。安装副本不反向复制回仓库。

## frontmatter（硬要求）

- `name`：小写 kebab-case，与目录名一致。
- `description`：≤500 字符。DSH 技能目录每会话只注入 `name` + `description`，正文不进目录；`whenToUse` 不渲染给模型，不要依赖它。
- `description` 必须含触发词：用户会怎么说这件事（口语与术语各写几个），不要写自我介绍。
- 可选 `metadata.version`、`metadata.phase`。
- 不要写 `disable-model-invocation: true`：它会让技能同时退出目录与 `skill` 工具，模型彻底不可达，只剩用户手打 `/名字` 能调。
- 目录每会话只注入一次，digest 变化时整份目录替换追加；不要设计「会话中途反复开关技能组」的用法。

## 正文结构（按顺序，缺项不算完整）

1. 一句话定义 + 默认产出。
2. 何时用 / 何时不用：路由表（用户意图 → 本技能 / 相邻技能），末尾一行判据。
3. 输入与缺省：必填项、默认值、缺了怎么问（一次只问一个）。
4. 第 0 步：工具/环境检测与降级路径；缺工具时写明「降级/未做」及少了什么证据，不假装跑过。
5. 主流程：8 步以内，每步有可机械判定的完成判据；必要时给时间盒。超过 8 步拆成「主流程 + references 细则」。
6. 输出模板：缺项不算完成。
7. 停止规则与反合理化表（常见借口 → 驳回）。
8. 完成自检：勾选式，逐条可判。
9. 资源清单：`references/`、`scripts/`、`templates/` 的相对路径 + 一句话用途。

## 写作规则

- 只写可执行指令：每条判据都要能回答「怎么算完成、怎么算不合格」。
- 默认零第三方依赖；需要外部工具时给降级路径，并写明降级后少了什么证据。
- 长内容进 `references/`（按需读），正文只留路由与判据；单篇 `references/` 建议 ≤320 行，超出就拆分。
- 不复制相邻技能的正文，只用一句路由指过去；同一触发词只归一个技能。
- 正文中文；目录名、文件名、命令、代码标识符用英文。
- 不写历史：不写「上一版」「已改为」「本次新增」；变化进 `CHANGELOG.md`。
- 技能目录只允许 `SKILL.md`、`references/`、`scripts/`、`templates/`、`assets/`；评测材料不放进技能目录。

## 安装、更新、卸载

```powershell
python tools/install_skills.py              # 装全部技能到 ~/.dsh/skills
python tools/install_skills.py --check      # 只比对仓库与安装副本，不写
python tools/install_skills.py --dry-run    # 打印计划，不写盘
python tools/install_skills.py first-principles   # 只装指定技能（可多个）
```

- 先改仓库，再装；顺序反过来会丢改动。
- 安装器默认覆盖同名文件；校验失败的技能不安装，命令返回 1。
- 装完重开一个会话，再用 `skill` 工具按 `name` 加载一次验证；技能目录只在会话开始时注入，本会话看不到新技能属正常。
- 卸载：删 `~/.dsh/skills/<name>/`（或 `python tools/install_skills.py --uninstall <name>`）。回滚：`git checkout` 仓库到旧提交后重装。
- 换电脑：克隆仓库后跑一次 `install_skills.py`，不手工复制。

## 版本与评测

- 内容变更改 `metadata.version`：MAJOR 触发条件或输出契约变化；MINOR 步骤/判据增删；PATCH 措辞与示例。
- 新技能或大改先做最小评测：输入 prompt、合格输出、不合格输出，结果可重跑；评测材料放 `evals/<name>/`，不混进技能目录。
- 发布前跑 `python tools/check_artifacts.py .` 与 `python tools/install_skills.py --check`。

## 检查清单

- [ ] `SKILL.md` 有 `name` 与 `description`，`name` 与目录名一致，`description` ≤500 字符且含触发词。
- [ ] 路由表覆盖相邻技能，判据只需一行。
- [ ] 每步有完成判据；输出模板缺项不算完成。
- [ ] 缺工具时的降级路径写明，没有假装跑过工具。
- [ ] 资源路径相对技能目录，且文件真实存在。
- [ ] 安装后能被 `skill` 工具加载；`install_skills.py --check` 无差异。
