# AGENTS.md · lap-skills-rules

本仓库是规范与技能的唯一源。改规矩先改 `rules/`，再同步项目侧；技能只从 `skills/` 装，安装副本只读。

## 交付物通道（硬规则）

交付物 ＝ 文档正文、界面文案、代码注释。它只回答「此刻为真」。

1. 只写「现在是什么」；「原来是什么」「改了什么」「下一步做什么」进聊天、提交说明、`CHANGELOG.md`。
2. 改 ＝ 整段替换，不是追加。允许删旧版；不允许在旧句后面补一句新的。
3. 界面文案给没参与施工的陌生人看：不许出现「占位」「待定」「此处」「TODO」这类施工字。
4. 代码注释只写「为什么」，不写「改了什么」；改了什么由版本历史回答。
5. 本来就记历史的东西豁免：CHANGELOG、交接账本、archive/、迁移说明、测试冻结证据。

## 本仓库的规矩

- 规范全文在 `rules/`：交付物通道、改动范围、项目结构、门禁、测试可重复性、Windows 进程红线、账本、技能规范；`AGENTS.md` 只是操作版。
- 技能写法与安装见 `rules/skills.md`；新技能或大改先按 `evals/<name>/` 做最小评测。
- 技能里的示例命令不得打掉宿主进程或向共享控制台发信号（见 `rules/windows-process.md`）。

## 收尾自检

```bash
python tools/check_repo.py --check-tools
python tools/check_artifacts.py --selftest
python tools/check_structure.py --selftest
```

- 输出 `PASS` 才算干净；`WARN`（只有中/低风险）不阻断，但交付前清零。
- `install_skills.py --check` 显示差异时，先提交仓库再重装，不要手改安装副本。
- `structure-allow.txt` 是既有超限清单：新增条目先记账，清单只缩不涨。
