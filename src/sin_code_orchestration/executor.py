"""Parallel task executor with semaphore and dependency tracking.

The executor turns a list of `TaskSpec` objects (some with `dependencies`)
into a list of `TaskResult` objects. It:
  - Caps concurrency with an `asyncio.Semaphore`.
  - Respects dependencies (a task only starts once all its deps are
    `finished`).
  - Honors a shared `cancel_event` for cooperative cancellation.
  - Retries transient failures with a linear backoff (`0.1 * (attempt+1)`s).

Docs: executor.doc.md
"""

import asyncio
import time
from typing import Any, Awaitable, Callable

from .task import TaskSpec, TaskResult, TaskStatus


# ── Single-task helpers ────────────────────────────────────────────────
async def _run_with_timeout(
    coro: Awaitable[Any],
    timeout: float,
    task_id: str,
) -> tuple[Any, float]:
    """Run a coroutine with a timeout, return `(result, duration_s)`.

    Translates `asyncio.TimeoutError` into a plain `TimeoutError` with a
    helpful message so the caller doesn't need to know about asyncio.
    """
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
    """Execute one task with retry-on-failure (timeouts are NOT retried).

    Backoff: `0.1 * (attempt + 1)` seconds between retries. Retry count
    is the parameter, so the total attempts is `retry_count + 1`.
    """
    last_error: Exception | None = None
    for attempt in range(retry_count + 1):
        try:
            start = time.monotonic()
            result = await asyncio.wait_for(handler(task), timeout=task.timeout)
            duration = time.monotonic() - start
            return result, duration
        except asyncio.TimeoutError:
            # Timeouts are fatal — retrying would just hit the same wall.
            # The orchestrator will mark the task TIMEOUT and skip downstream.
            raise TimeoutError(f"Task {task.task_id} timed out after {task.timeout}s")
        except Exception as exc:
            last_error = exc
            if attempt < retry_count:
                # Linear backoff: 0.1s, 0.2s, 0.3s, ... — gentle enough
                # to not DoS a flaky downstream service.
                await asyncio.sleep(0.1 * (attempt + 1))
    # All retries exhausted; surface the last error (or a generic one).
    raise last_error or RuntimeError(f"Task {task.task_id} failed after {retry_count} retries")


# ── Public API ─────────────────────────────────────────────────────────
async def execute_tasks(
    tasks: list[TaskSpec],
    handler: Callable[[TaskSpec], Awaitable[dict[str, Any]]],
    max_concurrent: int = 4,
    cancel_event: asyncio.Event | None = None,
) -> list[TaskResult]:
    """Execute a list of tasks in parallel, honoring dependencies and the cancellation event.

    Args:
        tasks: TaskSpecs to execute. Order in the result list mirrors this input order.
        handler: Async callable that runs a single task and returns an output dict.
        max_concurrent: Hard cap on tasks running simultaneously. Must be >= 1.
        cancel_event: If provided and set, pending tasks are marked CANCELLED.

    Returns:
        List of TaskResult in the same order as `tasks`.

    Raises:
        ValueError: if `max_concurrent < 1`.
    """
    if max_concurrent < 1:
        raise ValueError(f"max_concurrent must be >= 1, got {max_concurrent}")
    semaphore = asyncio.Semaphore(max_concurrent)
    task_map = {t.task_id: t for t in tasks}
    results: dict[str, TaskResult] = {}
    pending = {t.task_id for t in tasks}
    finished = set()
    cancelled = set()

    async def _wrap(task: TaskSpec) -> None:
        # Acquire the semaphore FIRST so cancelled tasks don't grab a slot.
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
                # `finished` is the signal downstream tasks wait on; we
                # MUST set it in finally so a crashed task unblocks its deps.
                finished.add(task.task_id)

    # ── Dependency-driven scheduling loop ──
    # We re-scan `pending` every iteration: as deps finish, new tasks
    # become ready. The 10ms sleep avoids a tight CPU loop when nothing
    # is ready (e.g. all pending tasks are blocked on long-running deps).
    running_tasks: list[asyncio.Task] = []
    while pending:
        ready = [
            tid for tid in pending
            # Skip already-cancelled tasks so we don't schedule them.
            if all(d in finished for d in task_map[tid].dependencies)
            and tid not in cancelled
        ]

        if not ready:
            # Nothing ready — wait for at least one running task to finish.
            # If all remaining tasks are cancelled, exit the loop.
            if all(tid in cancelled for tid in pending):
                break
            await asyncio.sleep(0.01)
            continue

        for tid in ready:
            pending.remove(tid)
            running_tasks.append(asyncio.create_task(_wrap(task_map[tid])))

    # Wait for all running tasks to finish. `return_exceptions=True` so
    # a stray exception in `_wrap` doesn't kill `gather` — we've already
    # recorded the failure in `results` by that point.
    if running_tasks:
        await asyncio.gather(*running_tasks, return_exceptions=True)

    return [results[t.task_id] for t in tasks]
