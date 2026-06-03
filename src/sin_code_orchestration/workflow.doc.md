# `workflow.py` — DAG Workflow Engine

What this file does: a `Workflow` is a directed acyclic graph of `TaskSpec` nodes. The module provides `validate` (catches missing deps and cycles) and `topological_order` (Kahn's algorithm) — the two operations the orchestrator needs to schedule a workflow.

## Dependency map

- Imports: stdlib `dataclasses`, `typing`, plus `.task` (TaskSpec).
- Imported by: `.orchestrator` (calls `validate` and `topological_order` before submitting).

## Public API

| Symbol                                       | Purpose                                                              |
|----------------------------------------------|----------------------------------------------------------------------|
| `Error(task_id, message)`                    | One validation finding. Returned as a list from `validate()`.        |
| `Workflow()`                                 | Construct an empty workflow.                                         |
| `.add_task(task)`                            | Add a TaskSpec (with its declared dependencies).                     |
| `.add_dependency(task_id, depends_on)`       | Add a manual dep edge between two existing tasks.                    |
| `.validate()`                                | Return a list of `Error` (empty = valid). Catches missing deps + cycles. |
| `.topological_order()`                       | Return a list of task_ids in valid execution order. Raises on invalid. |
| `.tasks()`                                   | Return a copy of the task-id → TaskSpec mapping.                     |

## Important config / limits

- **`add_dependency` requires both tasks to exist.** A missing task or dep raises `ValueError` at the call site.
- **`validate()` does NOT raise.** It returns all errors. The orchestrator checks `if errors: raise` and surfaces the first.
- **`topological_order()` DOES raise** if the workflow is invalid. Only the first error is included in the message; call `validate()` directly to see them all.
- **Cycle detection uses DFS 3-coloring.** All cycles are reported in a single `validate()` call.
- **Topological order is NOT stable.** Tasks at the same dependency level can come out in any order (dict iteration order). Wrap in a `sorted(...)` if you need determinism.

## Design decisions

- **Why a reverse index (`_dependents`)?** Kahn's algorithm needs to decrement `in_degree` of downstream nodes. The reverse index turns that decrement into O(1) instead of an O(V) scan of all tasks.
- **Why is `pop(0)` used instead of `collections.deque`?** Both are O(n) per operation for `pop(0)`, and our workflows are small. A deque wouldn't change asymptotic complexity and would obscure the algorithm.
- **Why does `validate` not raise?** The orchestrator wants to surface ALL problems to the user in one pass. Raising on the first would force an iterative debug cycle.
- **Why a separate `add_dependency` method when `add_task` already takes `dependencies`?** Workflows are sometimes built incrementally — adding a task first, then wiring up its deps later. The two methods support both styles.

## Usage example

```python
from sin_code_orchestration import Workflow
from sin_code_orchestration.task import TaskSpec
from sin_code_orchestration.role import Role

wf = Workflow()
wf.add_task(TaskSpec(task_id="a", description="x", role=Role.DEVELOPER, input_data={}))
wf.add_task(TaskSpec(task_id="b", description="y", role=Role.DEVELOPER, input_data={}, dependencies=["a"]))
print(wf.topological_order())  # ['a', 'b']
print(wf.validate())           # []
```

## Caveats / footguns

- **`add_task` overwrites silently.** Adding two tasks with the same `task_id` keeps the second and drops the first; the first's edges are NOT migrated.
- **`topological_order` raises `ValueError`, not a typed exception.** Catch `ValueError` in the orchestrator code (it does).
- **Validation is structural only.** It does NOT check that a task's `role` has a registered agent — that's the orchestrator's job at execution time.
