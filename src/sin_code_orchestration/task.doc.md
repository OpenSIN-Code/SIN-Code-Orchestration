# `task.py` — Task Data Structures

What this file does: the data model of the orchestrator. `TaskStatus` is the lifecycle enum, `TaskSpec` is the input to the executor, and `TaskResult` is its output. Intentionally minimal — anything more complex belongs in a wrapper.

## Dependency map

- Imports: stdlib `dataclasses`, `enum`, `typing`, plus `.role` (Role).
- Imported by: `.executor`, `.workflow`, `.verifier`, `.orchestrator`, `.agent` (TaskSpec type hint).

## Public API

| Symbol         | Purpose                                                          |
|----------------|------------------------------------------------------------------|
| `TaskStatus`   | Enum: PENDING / RUNNING / SUCCESS / FAILED / TIMEOUT / CANCELLED |
| `TaskSpec`     | Dataclass: one task's spec (id, description, role, input, deps, timeout, retry) |
| `TaskResult`   | Dataclass: one task's outcome (status, output, error, duration, verification?) |

## Important config / limits

- **`TaskSpec.timeout` default: 300.0s (5 min).** Long enough for most LLM calls, short enough to fail fast on a hung subprocess. Set to 0 for "no time" (will TIMEOUT immediately).
- **`TaskSpec.retry_count` default: 3.** Total attempts = `retry_count + 1` (so 4 attempts with the default).
- **`TaskResult.verification` is `None` unless** the orchestrator was created with `verifier=True` (default).
- **`TaskStatus.RUNNING` is reserved** for future use; the current executor doesn't surface it (tasks go straight from PENDING to a terminal state).

## Design decisions

- **Why dataclasses and not Pydantic?** Zero dependencies, simpler. The orchestrator doesn't need validation at the data-model boundary.
- **Why free-form `input_data: dict[str, Any]`?** Tasks are dynamic — what the agent receives depends on what the workflow author decided. A typed schema would lock callers in.
- **Why allow `timeout=0`?** "I want this to fail immediately" is a valid test case. The validation is `< 0` (truly invalid), not `== 0`.
- **Why is `RUNNING` in the enum but unused?** It's reserved for future observability work (e.g. a `set_status(RUNNING)` call when the executor dequeues a task).

## Usage example

```python
from sin_code_orchestration.task import TaskSpec, TaskResult, TaskStatus
from sin_code_orchestration.role import Role

spec = TaskSpec(
    task_id="build",
    description="compile the project",
    role=Role.DEVELOPER,
    input_data={"target": "main"},
    dependencies=["test"],
)
result = TaskResult(
    task_id="build",
    status=TaskStatus.SUCCESS,
    output={"artifact": "build/main"},
    error=None,
    duration_seconds=12.3,
)
```

## Caveats / footguns

- **`TaskResult` is a plain dataclass — no equality helpers.** Two `TaskResult`s with the same fields compare by identity. Use `dataclasses.asdict(result)` if you need value equality.
- **`TaskSpec.__post_init__` raises `ValueError` on `timeout < 0`.** It does NOT check `retry_count` — negative retries are allowed (just useless).
- **`output` is a dict**, not a Pydantic model. The orchestrator does not validate the shape; the verifier's `rules[task_id]` is the closest thing to a schema.
