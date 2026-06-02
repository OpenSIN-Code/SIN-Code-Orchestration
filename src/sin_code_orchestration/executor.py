"""Parallel task executor with semaphore and dependency tracking.

Docs: executor.doc.md
"""

import asyncio
import time
from typing import Any, Awaitable, Callable

from .task import TaskSpec, TaskResult, TaskStatus


async def _run_with_timeout(
    coro: Awaitable[Any],
    timeout: float,
    task_id: str,
) -> tuple[Any, float]:
    """Run a coroutine with timeout, return (result, duration)."""
    start = time.monotonic()
    try:
        result = await asyncio.wait_for(coro, timeout=timeout)
        duration = time.monotonic() - start
        return result, duration
    except asyncio.TimeoutError:
        duration = time.monotonic() - start
        raise TimeoutError(f"Task {task_id} timed out after {timeout}s")


async def _execute_task(
    task: TaskSpec,
    handler: Callable[[TaskSpec], Awaitable[dict[str, Any]]],
    retry_count: int,
) -> tuple[dict[str, Any], float]:
    """Execute a task with retries and timeout."""
    last_error: Exception | None = None
    for attempt in range(retry_count + 1):
        try:
            start = time.monotonic()
            result = await asyncio.wait_for(handler(task), timeout=task.timeout)
            duration = time.monotonic() - start
            return result, duration
        except asyncio.TimeoutError:
            raise TimeoutError(f"Task {task.task_id} timed out after {task.timeout}s")
        except Exception as exc:
            last_error = exc
            if attempt < retry_count:
                await asyncio.sleep(0.1 * (attempt + 1))
    raise last_error or RuntimeError(f"Task {task.task_id} failed after {retry_count} retries")


async def execute_tasks(
    tasks: list[TaskSpec],
    handler: Callable[[TaskSpec], Awaitable[dict[str, Any]]],
    max_concurrent: int = 4,
    cancel_event: asyncio.Event | None = None,
) -> list[TaskResult]:
    """Execute a list of tasks in parallel honoring dependencies.

    Returns a list of TaskResult in the same order as input.
    """
    semaphore = asyncio.Semaphore(max_concurrent)
    task_map = {t.task_id: t for t in tasks}
    results: dict[str, TaskResult] = {}
    pending = {t.task_id for t in tasks}
    finished = set()
    cancelled = set()

    async def _wrap(task: TaskSpec) -> None:
        async with semaphore:
            if cancel_event and cancel_event.is_set():
                cancelled.add(task.task_id)
                results[task.task_id] = TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.CANCELLED,
                    output={},
                    error="Cancelled",
                    duration_seconds=0.0,
                )
                finished.add(task.task_id)
                return

            try:
                out, dur = await _execute_task(task, handler, task.retry_count)
                results[task.task_id] = TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.SUCCESS,
                    output=out,
                    error=None,
                    duration_seconds=dur,
                )
            except TimeoutError as exc:
                results[task.task_id] = TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.TIMEOUT,
                    output={},
                    error=str(exc),
                    duration_seconds=task.timeout,
                )
            except Exception as exc:
                results[task.task_id] = TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    output={},
                    error=str(exc),
                    duration_seconds=0.0,
                )
            finally:
                finished.add(task.task_id)

    # Wait for dependencies to finish
    running_tasks: list[asyncio.Task] = []
    while pending:
        ready = [
            tid for tid in pending
            if all(d in finished for d in task_map[tid].dependencies)
            and tid not in cancelled
        ]

        if not ready:
            if all(tid in cancelled for tid in pending):
                break
            await asyncio.sleep(0.01)
            continue

        for tid in ready:
            pending.remove(tid)
            running_tasks.append(asyncio.create_task(_wrap(task_map[tid])))

    # Wait for all running tasks to finish
    if running_tasks:
        await asyncio.gather(*running_tasks, return_exceptions=True)

    return [results[t.task_id] for t in tasks]
