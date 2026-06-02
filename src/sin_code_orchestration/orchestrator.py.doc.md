# orchestrator.py

## Purpose

Central orchestrator for single tasks and DAG-based workflows.

## What it does

Manages task registration, execution, verification, and lifecycle.

## Dependencies

- `role.py`, `task.py`, `workflow.py`, `agent.py`, `context.py`, `executor.py`, `verifier.py`

## Usage

```python
orch = Orchestrator(max_concurrent=4, verifier=True)
result = orch.submit(TaskSpec(...))
results = orch.submit_workflow(Workflow(...))
```

## Known caveats

- `submit()` and `submit_workflow()` block via `asyncio.run()`.
- `cancel()` only affects tasks that have not yet started in the executor.
