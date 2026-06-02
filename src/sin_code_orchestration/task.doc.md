# `task.py` — Task Definitions

What this file does: defines the data structures for tasks, results, and statuses.

## Dependencies

- Imported by: `orchestrator.py`, `workflow.py`, tests, MCP server

## Types

- `TaskSpec` — task_id, description, role, input_data, dependencies, timeout, retry_count
- `TaskResult` — task_id, status, output, error, verification
- `TaskStatus` — enum: PENDING, RUNNING, SUCCESS, FAILED, CANCELLED

## Usage

```python
from sin_code_orchestration import TaskSpec, Role
spec = TaskSpec(task_id="build", description="Build", role=Role.DEVELOPER, input_data={})
```

## Notes

`timeout` is in seconds. `retry_count` includes the initial attempt.
