# Windows 进程与控制台红线

> 一句话：探测进程与发送信号是两件会误杀的事；先隔离，再动手。

## 它挡住什么（实测）

| 写法 | 实际发生 | 后果 |
|---|---|---|
| 用 `os.kill(pid, 0)` 当存活探测 | Windows 上 `0` 就是 `CTRL_C_EVENT`，调用会向目标的控制台组发控制台事件，并结束目标进程 | 目标被误杀；同一控制台里的测试进程或宿主收到 `KeyboardInterrupt`，整条门禁在测试中途终止 |
| 在测试进程内直接 `taskkill /PID <子进程> /T /F` | 强杀与调用者共享控制台的子进程树 | 实测调用进程被连带结束：隔离控制台探针在命令返回后不再执行后续打印 |
| 在非主线程注册信号处理器 | `signal.signal` 只能在主线程调用 | 抛 `ValueError`，或收尾路径静默走偏 |
| 按 pid 结束进程、不校验身份 | pid 被系统复用 | 误杀无关进程 |

## 四条硬规则

1. **存活探测不用信号**：Windows 用 kernel32 `OpenProcess(SYNCHRONIZE)` + `WaitForSingleObject(handle, 0)`；手上已有 `Popen` 对象时直接用 `poll()`。
2. **强杀先隔离**：需要结束整个进程树的子进程用独立控制台或独立进程组启动（`CREATE_NO_WINDOW`、`DETACHED_PROCESS`）；确认目标身份（pid + 启动时间）后再动手。
3. **信号只在主线程**：服务循环跑在线程里时，测试用注入的停机事件驱动，不调用 `signal.signal`、不向控制台发事件。
4. **结束整棵树并回收**：记录 pid 与启动时间；先结束树，再用 `Popen.kill()` 与 `wait(timeout)` 兜底；管道与句柄收干净。

## 代码：Windows 进程存活探测

```python
import ctypes

_SYNCHRONIZE = 0x00100000
_WAIT_TIMEOUT = 0x00000102


def process_alive(pid: int) -> bool:
    """进程是否仍在运行；Windows 用内核句柄查询，不向目标发任何信号。"""
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(_SYNCHRONIZE, False, pid)
    if not handle:
        return False
    try:
        return kernel32.WaitForSingleObject(handle, 0) == _WAIT_TIMEOUT
    finally:
        kernel32.CloseHandle(handle)
```

非 Windows 平台才用 `os.kill(pid, 0)`，并捕获 `ProcessLookupError` 与 `PermissionError`。

## 排障判据

- 测试进程突然 `KeyboardInterrupt`、堆栈停在 `Thread.join` 或 `subprocess._communicate`：先查同一用例里有没有 `os.kill(..., 0)`、`taskkill`、控制台事件。
- 宿主 shell 一起退出且没有输出：同上。用隔离控制台重跑一次，能把「测试把宿主打掉」与「测试真失败」分开。
- 强杀后目标仍存活：pid 可能已结束或被复用，改为句柄探测加有限重试。

## 检查清单

- [ ] 没有把 `os.kill(pid, 0)` 当存活探测
- [ ] 需要强杀的子进程有独立控制台或独立进程组
- [ ] 信号处理器只在主线程注册；线程路径用注入的停机事件
- [ ] 结束进程树前后都有身份校验与句柄回收
- [ ] 门禁红时能分清「测试打掉宿主」与「测试真失败」
