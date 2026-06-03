# `executor.py` — Parallel Task Executor

What this file does: turns a list of `TaskSpec` objects (with dependencies) into a list of `TaskResult` objects, running tasks in parallel under a semaphore and honoring a shared cancellation event.

## Dependency map

- Imports: stdlib (`asyncio`, `time`), `.task` (TaskSpec, TaskResult, TaskStatus).
- Imported by: `.orchestrator` (calls `execute_tasks` for both single-task and workflow submission).

## Public API

| Symbol                        | Purpose                                                            |
|-------------------------------|--------------------------------------------------------------------|
| `execute_tasks(tasks, handler, max_concurrent=4, cancel_event=None)` | Schedule and run all tasks, return results in input order. |

`handler` is `Callable[[TaskSpec], Awaitable[dict]]` — it's the bridge to the agent layer (the orchestrator's `_handle_task`).

## Important config / limits

- **`max_concurrent` is a hard cap.** Default 4. Must be `>= 1`; otherwise `ValueError` at entry.
- **Linear backoff on retry: `0.1 * (attempt + 1)` seconds.** Attempts 0→1→2 wait 0.1s, 0.2s, 0.3s.
- **Timeouts are NOT retried.** A timed-out task raises immediately; the orchestrator marks it TIMEOUT and downstream tasks (that depend on it) will be cancelled.
- **Dependency scheduling is a 10ms-poll loop.** When no task is ready, the executor sleeps 10ms. Adequate for human-scale workflows; if you have 10k tasks, consider an event-driven scheduler.
- **Result list mirrors input order.** Always. Even if tasks finish out of order.
- **`return_exceptions=True` on the final `gather`.** An unexpected exception inside `_wrap` is swallowed (it's already recorded in `results` by then).

## Design decisions

- **Why an `asyncio.Semaphore` and not `asyncio.gather` with a count?** `gather` doesn't bound concurrency mid-flight. The semaphore does, which is what lets us promise "no more than N tasks at once".
- **Why a 10ms sleep when nothing is ready?** Without it, the busy-wait would peg a core. 10ms is responsive (most task completions are visible within one frame) and idle-friendly.
- **Why a shared `cancel_event` for workflows vs a per-task event for `submit`?** A workflow is conceptually one unit — if you cancel any task, the whole thing should stop. Single-task submission has no dependents, so a per-task event is fine.

## Usage example

```python
import asyncio
from sin_code_orchestration.executor import execute_tasks
from sin_code_orchestration.task import TaskSpec, TaskStatus, TaskResult

async def handler(task):
    return {"echo": task.input_data}

tasks = [TaskSpec(task_id="a", description="x", role="orchestrator", input_data={})]
results = asyncio.run(execute_tasks(tasks, handler, max_concurrent=2))
print(results[0].status)  # TaskStatus.SUCCESS
```

## Caveats / footguns

- **Dependency cycles are NOT detected here.** Use `workflow.validate()` first; otherwise tasks will wait forever for their (non-existent) deps to finish.
- **The 10ms sleep can mask a bug.** If your task never finishes and has no deps, the executor will poll for 10ms then schedule it. There is no deadlock detection.
- **Cancelled tasks are added to the `cancelled` set** — they're not retried, even if they had `retry_count > 0`. Cancellation is terminal.
