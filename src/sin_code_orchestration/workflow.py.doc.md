# workflow.py

## Purpose

DAG-based workflow engine with cycle detection and topological ordering.

## What it does

Validates workflows (cycles, missing deps) and computes execution order.

## Dependencies

- `task.py`

## Usage

```python
wf = Workflow()
wf.add_task(TaskSpec(task_id="t1", ...))
wf.add_dependency("t2", "t1")
order = wf.topological_order()
```

## Known caveats

- `add_dependency` requires both tasks to exist.
- `topological_order()` raises if the workflow is invalid.
