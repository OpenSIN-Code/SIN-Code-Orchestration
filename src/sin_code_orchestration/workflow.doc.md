# `workflow.py` — DAG Workflow Engine

What this file does: defines a directed acyclic graph of tasks with validation, topological ordering, and dependency management.

## Dependencies

- Imported by: `orchestrator.py`, tests, MCP server
- Imports: `task` (TaskSpec)

## Public API

- `Workflow()` — create an empty workflow
- `add_task(task_spec)` — add a task to the graph
- `add_dependency(task_id, depends_on)` — add a dependency edge
- `validate()` — check for cycles and missing tasks
- `topological_order()` — return task IDs in dependency order
- `tasks()` — dict of all task specs

## Usage

```python
from sin_code_orchestration import Workflow, TaskSpec, Role
wf = Workflow()
wf.add_task(TaskSpec(task_id="build", description="Build", role=Role.DEVELOPER, input_data={}))
wf.add_task(TaskSpec(task_id="test", description="Test", role=Role.TESTER, input_data={}, dependencies=["build"]))
```

## Notes

`validate()` returns a list of errors; empty list means the workflow is valid.
