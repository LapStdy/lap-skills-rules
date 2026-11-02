# 七类检查的落地与踩坑

按依赖顺序排；前一类失败时后面结论通常不成立。每类给最小命令与真实踩过的坑。

## 1 格式与静态检查

```bash
python -m ruff check .
python -m ruff format --check .
```

- 坑：`ruff format` 会连 Markdown 里的 Python 代码块一起格式化；文档里的示例代码要能被格式化器接受，或者把 `extend-exclude` 配好。
- 坑：`ruff check --fix` 只在本地用，门禁里永远是 `check` 不带 `--fix`。

## 2 类型

```bash
python -m mypy .
```

- 从 `strict` 起；历史代码多的项目用「只对新增模块 strict」的 per-module 覆盖，但门禁必须跑全量。
- 坑：`Any` 逃逸常出现在第三方库边界；用 `object` + `isinstance` 收窄，或写 Protocol，不要加 `# type: ignore` 了事。

## 3 测试

```bash
python -m pytest -q
```

- 用 `-q` 让失败行集中；门禁里不加 `-x` 与 `--maxfail`，一次看到全部失败更省时间。
- 坑：测试碰真实互斥量、固定端口、系统时钟会出间歇红，见 `rules/testing.md`。
- 坑：Windows 上测试进程被 `KeyboardInterrupt` 打断，先查 `os.kill(pid, 0)` 与 `taskkill`，见 `rules/windows-process.md`。

## 4 依赖方向

```bash
lint-imports
```

- 契约写在 `.importlinter`；只覆盖 import 关系，覆盖不了「用 AST 扫出的允许依赖集合」这类更细的约束。
- 坑：契约写错时 import-linter 可能静默跳过该契约；给它配一个「故意违反」的样例，确认能红。
- 更细的边界（某模块只许依赖哪几个模块）用 AST 契约测试兜：解析 import 语句，比对允许集合。

## 5 契约同步

```bash
python scripts/check_contracts.py
```

- 形态：状态机表、事件表、错误码表放 `docs/`，测试解析表格逐行驱动断言；任何一侧改动都会让另一侧红。
- 坑：解析失败必须报错，不静默跳过；否则表被改坏时检查会「全绿」。
- 坑：表格里的中文列名变化会让解析失败；解析器要按表头定位列，不按列序号。

## 6 结构上限

```bash
python scripts/check_structure.py . --allow structure-allow.txt
```

- 上限：函数 50 行、参数 4 个、类 300 行、模块 500 行；`self`/`cls` 不计参数。
- 允许清单按「文件 + 限定名」匹配，只缩不涨；每条都要在 DEBT 记账并写归还期限。
- 坑：清单写太宽（只写文件名）会把新增超限一起放行；按限定名写。

## 7 交付物文字

```bash
python scripts/check_artifacts.py .
```

- 只查「交付物里有没有关于过程、历史、施工的字」；词表规则会误报也会漏报，它是兜底。
- 坑：交接账本、CHANGELOG、`archive/` 本来记历史，必须在豁免名单里；放进仓库的卡文会被误判。
- 坑：真误报用行内豁免 `artifact-check: ignore`，不要整文件关掉。

## 门禁骨架的约定

- 每项一个子进程；失败即停（`--keep-going` 用于排查）。
- 必需项缺工具按 FAIL；可选项缺工具打印 SKIP 并在总结里列出，避免「装不上就算过」。
- 报告行固定：`门禁：PASS（N 项）` 或 `门禁：FAIL（N 项，失败：…）`。
