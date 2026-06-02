# `role.py` — Role Definitions

What this file does: defines the role enum used for task assignment.

## Dependencies

- Imported by: `task.py`, `orchestrator.py`, `agent.py`, tests, MCP server

## Types

- `Role` — enum: ORCHESTRATOR, DEVELOPER, TESTER, ARCHITECT, REVIEWER

## Usage

```python
from sin_code_orchestration import Role
spec = TaskSpec(task_id="t1", description="Build", role=Role.DEVELOPER, input_data={})
```

## Notes

Roles are used to route tasks to the appropriate agent implementation.
