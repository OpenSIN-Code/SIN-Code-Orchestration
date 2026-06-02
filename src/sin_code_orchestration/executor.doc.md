# `executor.py` — Task Executor

What this file does: parallel task executor with configurable concurrency and cancellation support.

## Dependencies

- Imported by: `orchestrator.py`, tests

## Public API

- `execute_tasks(tasks, handler, max_concurrent, cancel_event)` → list[TaskResult]

## Notes

Respects task dependencies: a task is only started after all its dependencies have succeeded.
