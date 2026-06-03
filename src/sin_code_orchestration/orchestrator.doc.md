# `orchestrator.py` — Main Orchestrator

What this file does: the public entry point. The `Orchestrator` class owns the agent registry, shared context, cancel events, and result cache. Both `submit` (single task) and `submit_workflow` (DAG) go through the same `executor.execute_tasks` machinery.

## Dependency map

- Imports: `.role` (Role), `.task` (TaskSpec, TaskResult, TaskStatus), `.workflow` (Workflow), `.agent` (Agent, EchoAgent), `.context` (Context), `.executor` (execute_tasks), `.verifier` (Verifier, Oracle)
- Imported by: `__init__.py` (re-exported as `Orchestrator`), the MCP server.

## Public API

| Method                                         | Purpose                                                              |
|------------------------------------------------|----------------------------------------------------------------------|
| `Orchestrator(max_concurrent=4, verifier=True)` | Construct. `max_concurrent` is a hard cap; `verifier` toggles auto-verification. |
| `.register_agent(role, agent)`                 | Add or replace the agent for a role.                                 |
| `.submit(task)`                                | Run a single task synchronously, return its `TaskResult`.            |
| `.submit_workflow(workflow)`                   | Run a DAG; returns results in topological order.                     |
| `.get_status(task_id)`                         | Return current status; `PENDING` for unknown tasks.                  |
| `.wait_for(task_id, timeout=30)`               | Block until the task is done or timeout expires.                     |
| `.cancel(task_id)`                             | Cooperative cancel. Cancels the whole workflow if task is part of one. |

## Important config / limits

- **Default `max_concurrent=4`**, must be `>= 1`.
- **`verifier=True` (default)** runs the `Verifier` on every result; the report is attached as `result.verification`.
- **`submit` uses `asyncio.run`** — don't call it from inside an existing event loop. Use `_submit_async` directly instead.
- **A single cancel event per workflow.** Cancelling any task in a workflow cancels the whole workflow. This is intentional (workflows are conceptually one unit) but worth knowing.
- **`wait_for` polls every 50ms** — adequate for human-driven waits, not for high-frequency coordination.

## Design decisions

- **Why an agent registry keyed by `Role`?** Decouples task definitions from agent implementations. A task says "I need a DEVELOPER"; the orchestrator looks up which agent fills that role.
- **Why a shared `Context` and not per-task state?** Workflows are commonly a pipeline: task A's output is task B's input. A shared context with snapshot-per-task is the simplest way to express that.
- **Why a default `EchoAgent` on the ORCHESTRATOR role?** It lets the orchestrator run end-to-end without any user-registered agents. Production code should always register at least one DEVELOPER agent.
- **Why an `asyncio.Lock` on `_cancel_events` and `_results`?** Concurrent submissions to the same orchestrator (rare but possible) can race on the dict. The lock is cheap and correct.

## Usage example

```python
import asyncio
from sin_code_orchestration import Orchestrator, Workflow
from sin_code_orchestration.task import TaskSpec
from sin_code_orchestration.role import Role

orch = Orchestrator(max_concurrent=4)
t = TaskSpec(task_id="t1", description="echo", role=Role.ORCHESTRATOR, input_data={"hi": 1})
result = orch.submit(t)
print(result.status)  # TaskStatus.SUCCESS
```

## Caveats / footguns

- **`submit` is synchronous and runs the event loop.** If you call it from a Jupyter notebook (or any context with a running loop), use `_submit_async` with `await` instead.
- **Workflow validation errors raise `ValueError` with only the first message.** To see ALL problems, call `workflow.validate()` directly before submitting.
- **`cancel` is best-effort.** It only affects tasks that haven't finished yet. A task that just completed is not rolled back.
- **Results in the cache are not thread-safe across `Orchestrator` instances.** Each orchestrator has its own cache; sharing results across orchestrators is the caller's job.
