"""Main orchestrator managing task submission and workflow execution.

The `Orchestrator` is the public entry point. It owns:
  - the agent registry (role → Agent)
  - the shared `Context` (KV store across tasks)
  - the cancel-event map (per-task and per-workflow)
  - the result cache (so `get_status` / `wait_for` work)

Both single-task (`submit`) and whole-workflow (`submit_workflow`) APIs
go through the same `executor.execute_tasks` machinery under the hood.

Docs: orchestrator.doc.md
"""

import asyncio
import time
from typing import Any

from .role import Role
from .task import TaskSpec, TaskResult, TaskStatus
from .workflow import Workflow
from .agent import Agent, EchoAgent
from .context import Context
from .executor import execute_tasks
from .verifier import Verifier, Oracle


# ── Orchestrator ───────────────────────────────────────────────────────
class Orchestrator:
    """Central orchestrator for single tasks and DAG-based workflows.

    Concurrency: `max_concurrent` is a hard cap on simultaneously-running
    tasks. Verification: when `verifier=True` (the default), every result
    is passed through the `Verifier` and the resulting report is attached
    as `result.verification`.
    """

    def __init__(self, max_concurrent: int = 4, verifier: bool = True):
        if max_concurrent < 1:
            raise ValueError(f"max_concurrent must be >= 1, got {max_concurrent}")
        self.max_concurrent = max_concurrent
        self._use_verifier = verifier
        self._verifier = Verifier(Oracle())
        self._context = Context()
        # Default agent: EchoAgent on the ORCHESTRATOR role. Any task
        # whose role has no registered agent falls back to this.
        self._agents: dict[Role, Agent] = {Role.ORCHESTRATOR: EchoAgent()}
        self._results: dict[str, TaskResult] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}
        # Lock protects the cancel-event map and result cache from
        # concurrent submission on the same Orchestrator instance.
        self._lock = asyncio.Lock()

    # ── Agent registry ─────────────────────────────────────────────────
    def register_agent(self, role: Role, agent: Agent) -> None:
        """Register an agent for a given role.

        Overwrites any previously-registered agent for that role. The
        ORCHESTRATOR role is registered with `EchoAgent` by default;
        override it to add custom dispatch logic.
        """
        self._agents[role] = agent

    # ── Internal: dispatch + context merge ─────────────────────────────
    async def _handle_task(self, task: TaskSpec) -> dict[str, Any]:
        """Resolve the agent for `task.role` and execute, with context merged in.

        Context merge is LAST-WRITER-WINS: explicit `task.input_data`
        keys override context keys with the same name. The original
        `task` object is mutated (input_data is replaced) so downstream
        consumers see the merged view.
        """
        agent = self._agents.get(task.role, self._agents[Role.ORCHESTRATOR])
        # Merge context into input data
        enriched = dict(self._context.snapshot())
        enriched.update(task.input_data)
        task.input_data = enriched
        return agent.execute(task)

    # ── Single-task submission ─────────────────────────────────────────
    def submit(self, task: TaskSpec) -> TaskResult:
        """Submit a single task and block until it completes.

        Synchronous wrapper around `_submit_async` — uses `asyncio.run`
        to drive the coroutine. Do NOT call from inside an existing
        event loop; use `_submit_async` directly in that case.
        """
        return asyncio.run(self._submit_async(task))

    async def _submit_async(self, task: TaskSpec) -> TaskResult:
        """Async implementation of `submit`."""
        # Per-task cancel event (single-task path: workflow shares one event).
        async with self._lock:
            self._cancel_events[task.task_id] = asyncio.Event()
        results = await execute_tasks(
            [task],
            self._handle_task,
            max_concurrent=self.max_concurrent,
            cancel_event=self._cancel_events.get(task.task_id),
        )
        result = results[0]
        if self._use_verifier:
            result.verification = self._verifier.verify([result])[0]
        self._results[task.task_id] = result
        return result

    # ── Workflow submission ────────────────────────────────────────────
    def submit_workflow(self, workflow: Workflow) -> list[TaskResult]:
        """Submit a DAG workflow and return results in topological order.

        Validates the workflow (cycle detection, missing deps) before
        scheduling; raises `ValueError` on the first error.
        """
        return asyncio.run(self._submit_workflow_async(workflow))

    async def _submit_workflow_async(self, workflow: Workflow) -> list[TaskResult]:
        """Async implementation of `submit_workflow`."""
        errors = workflow.validate()
        if errors:
            # Surface the first error so the user knows where to look.
            raise ValueError(f"Workflow validation failed: {errors[0].message}")

        order = workflow.topological_order()
        tasks = [workflow.tasks()[tid] for tid in order]

        # All tasks in a workflow share one cancel event so calling
        # `cancel(any_task_id)` cancels the whole workflow.
        cancel_event = asyncio.Event()
        async with self._lock:
            for t in tasks:
                self._cancel_events[t.task_id] = cancel_event

        results = await execute_tasks(
            tasks,
            self._handle_task,
            max_concurrent=self.max_concurrent,
            cancel_event=cancel_event,
        )

        if self._use_verifier:
            verifications = self._verifier.verify(results)
            for r, v in zip(results, verifications):
                r.verification = v

        for r in results:
            self._results[r.task_id] = r

        return results

    # ── Status / wait / cancel ─────────────────────────────────────────
    def get_status(self, task_id: str) -> TaskStatus:
        """Return the current status of a task.

        Returns `PENDING` for unknown task IDs. After `submit` returns,
        the status is one of SUCCESS / FAILED / TIMEOUT / CANCELLED.
        """
        if task_id not in self._results:
            return TaskStatus.PENDING
        return self._results[task_id].status

    def wait_for(self, task_id: str, timeout: float = 30) -> TaskResult:
        """Block until a task completes or `timeout` expires.

        Polls every 50ms — adequate for human-driven waits, but if you
        need to coordinate many waiters on the same task, switch to
        asyncio primitives and use `_submit_async` directly.
        """
        start = time.monotonic()
        while True:
            if task_id in self._results:
                return self._results[task_id]
            if timeout is not None and (time.monotonic() - start) > timeout:
                raise TimeoutError(f"wait_for {task_id} exceeded {timeout}s")
            time.sleep(0.05)

    def cancel(self, task_id: str) -> None:
        """Cancel a pending or running task.

        For single-task submission, this cancels only that task. For
        workflow submission, it cancels the entire workflow (since all
        tasks share one cancel event).
        """
        event = self._cancel_events.get(task_id)
        if event:
            event.set()
        if task_id in self._results:
            self._results[task_id].status = TaskStatus.CANCELLED
