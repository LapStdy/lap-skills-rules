# 盯卡：任务状态、完成检测与唤醒

目标：任务卡到终态时把监管会话叫醒，不靠定时空转。

## 任务状态库

- 位置：`%USERPROFILE%\.zcode\v2\tasks-index.sqlite`（Windows）。
- 表 `tasks` 关键列：`task_id`、`title`、`task_status`、`workspace_path`、`created_at`、`updated_at`（毫秒）。
- 状态枚举以实际数据为准：运行中常见为空，终态常见 `completed` / `error` / `interrupted`；先 `SELECT DISTINCT task_status` 核对，再写判定。
- 只读打开：`sqlite3.connect("file:<path>?mode=ro", uri=True)`；查完立即关。

## 判断「真的在干活」

状态库只说明任务在跑，不说明有没有进展。配合三条证据：

1. 该卡 worktree 里 `git log` 有没有新提交。
2. worktree 有没有未提交改动（`git status --short`）；有改动说明在改代码。
3. ZCode 会话文件最近修改时间（`%USERPROFILE%\.zcode\cli\rollout\*.jsonl`）是否在更新。

三条都静止超过阈值才判疑似卡死。

## 唤醒策略：被动为主，定时只留给时间判据

定时器是用时间去代理事件。ZCode 的事件密度极不均匀（5 分钟完成 vs 两小时不动），固定周期必然不是过密就是过疏。所以：

- **被动唤醒**（默认）：只读 watcher 后台作业，满足任一退出条件即退出，作业结束叫醒会话。等待期零 token，延迟只有轮询间隔。
- **主动唤醒**：只在时间本身是判据时用——到点收尾、额度检查。

### watcher 四条退出条件（先到先退，缺一不可）

| 条件 | 判定 | 覆盖 |
|---|---|---|
| 终态转移 | 基线里非终态 → 现为 `completed` / `error` / `interrupted` | 正常完成或失败 |
| 疑似卡死 | 运行中，且 worktree 无新提交、无未提交改动、会话文件 mtime 均静止 ≥ 阈值（默认 40 分钟） | 卡死 |
| 阻塞态 | 状态或会话末尾出现等审批 / 等输入 | 不处理会一直卡着 |
| 活性兜底 | 距开始超过兜底时长（默认 90 分钟）且上述均未发生 | watcher 或任务本身出了问题 |

退出码要能区分「事件退出」与「兜底退出」，方便播报时判断是正常进展还是异常。

### 为什么不要两层都设定时

若既设 40 分钟卡死阈值又设 2 小时定时巡检，等于对同一过程采样两次，浪费的那一路永远是白醒。兜底时长应按「一夜最多醒几次」定，默认 90 分钟。

## 取完成报告

- 会话末尾通常有「分支 / 提交清单 / 门禁结论 / 交付物检查」；四项缺一就回会话补问。
- 报告里的数字（提交数、文件数、门禁项数）要与 worktree 实际核对，不一致以实际为准并记录差异。

## 轮询脚本骨架（按项目替换路径与状态枚举）

```python
"""任务到终态即退出；作业结束会唤醒监管会话。"""
import sqlite3, sys, time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
DB = Path.home() / ".zcode" / "v2" / "tasks-index.sqlite"   # 按软件实际位置改
WORKSPACE = r"D:\<项目>"                                     # 按项目改
TERMINAL = {"completed", "error", "interrupted"}
POLL, DEADLINE = 45, datetime.now().replace(hour=8, minute=30)

def snapshot(con):
    rows = con.execute(
        "SELECT task_id, title, task_status, updated_at FROM tasks"
        " WHERE workspace_path = ? AND deleted = 0 ORDER BY updated_at DESC LIMIT 12",
        (WORKSPACE,),
    ).fetchall()
    return [(str(r[0]), str(r[1]), str(r[2] or "running"), int(r[3])) for r in rows]

baseline = {}
while datetime.now() < DEADLINE:
    con = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    rows = snapshot(con); con.close()
    current = {tid: st for tid, _t, st, _u in rows}
    if not baseline:
        baseline = dict(current)
        print("监视：", [(t[:24], s) for _i, t, s, _u in rows[:4]])
    done = [(tid, st) for tid, st in current.items()
            if baseline.get(tid) not in TERMINAL and st in TERMINAL]
    if done:
        print("终态：", done)
        for tid, title, st, ts in rows[:6]:
            print(f"{st:12} {title[:60]}")
        raise SystemExit(0)
    time.sleep(POLL)
print("到截止时刻仍未结束")
raise SystemExit(2)
```

要点：只读连接、基线对比、终态集合以实际枚举为准、退出码区分「完成 / 超时」。

## 常见坑

| 现象 | 原因 | 改法 |
|---|---|---|
| 作业一直不结束 | 轮询把历史终态任务也算进基线 | 只认基线非终态的变化 |
| 唤醒太频繁 | 截止前把「运行中」误判成终态 | 核对状态枚举，别用模糊匹配 |
| 读库报锁 | 用了读写连接 | URI 加 `mode=ro`，查完即关 |
| 脚本退出码非 0 | 编码问题（中文标题） | 标准输出显式 UTF-8，异常字符替换 |
| 会话没被叫醒 | 会话已关闭或作业未挂住 | 改用定时唤醒兜底，并调整轮询间隔 |

## 防卡死巡检（无人看管时两小时一次）

每次醒来只做四件事：

1. 查任务状态与各 worktree 最近提交时间。
2. 没有任务在跑：一行说明，结束。
3. 有任务在跑且最近提交超过阈值（如 40 分钟）：先看是否停在「等审批 / 等输入」，是就处理；不是就停掉任务、保留 worktree、重派。
4. 正常推进：只报一行。

不审查、不合并——合并只在卡片完成后按正常流程做。
