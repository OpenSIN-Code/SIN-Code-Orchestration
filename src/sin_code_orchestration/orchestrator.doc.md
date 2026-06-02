# `orchestrator.py` — Main Orchestrator

What this file does: central orchestrator for single tasks and DAG-based workflows with parallel execution, retry, and verification.

## Dependencies

- Imported by: `__init__.py`, tests, MCP server
- Imports: `role`, `task`, `workflow`, `agent`, `context`, `executor`, `verifier`

## Public API

- `Orchestrator(max_concurrent=4, verifier=True)` — submit tasks and workflows
- `submit(task)` — block until a single task completes
- `submit_workflow(workflow)` — run a DAG and return results in topological order
- `get_status(task_id)` — current status of a task
- `wait_for(task_id, timeout)` — block until a task completes
- `cancel(task_id)` — cancel a pending or running task
- `register_agent(role, agent)` — register a custom agent for a role

## Usage

```python
from sin_code_orchestration import Orchestrator, TaskSpec, Role
orch = Orchestrator()
result = orch.submit(TaskSpec(task_id="t1", description="Build", role=Role.DEVELOPER, input_data={}))
```

## Notes

All public methods are synchronous wrappers around async implementations. The verifier runs after each task if enabled.
