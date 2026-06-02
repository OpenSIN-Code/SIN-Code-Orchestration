"""Main orchestrator managing task submission and workflow execution.

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


class Orchestrator:
    """Central orchestrator for single tasks and DAG-based workflows."""

    def __init__(self, max_concurrent: int = 4, verifier: bool = True):
        if max_concurrent < 1:
            raise ValueError(f"max_concurrent must be >= 1, got {max_concurrent}")
        self.max_concurrent = max_concurrent
        self._use_verifier = verifier
        self._verifier = Verifier(Oracle())
        self._context = Context()
        self._agents: dict[Role, Agent] = {Role.ORCHESTRATOR: EchoAgent()}
        self._results: dict[str, TaskResult] = {}
        self._cancel_events: dict[str, asyncio.Event] = {}
        self._lock = asyncio.Lock()

    def register_agent(self, role: Role, agent: Agent) -> None:
        """Register an agent for a given role."""
        self._agents[role] = agent

    async def _handle_task(self, task: TaskSpec) -> dict[str, Any]:
        """Dispatch task to the appropriate agent."""
        agent = self._agents.get(task.role, self._agents[Role.ORCHESTRATOR])
        # Merge context into input data
        enriched = dict(self._context.snapshot())
        enriched.update(task.input_data)
        task.input_data = enriched
        return agent.execute(task)

    def submit(self, task: TaskSpec) -> TaskResult:
        """Submit a single task and block until it completes."""
        return asyncio.run(self._submit_async(task))

    async def _submit_async(self, task: TaskSpec) -> TaskResult:
        """Async implementation of submit."""
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

    def submit_workflow(self, workflow: Workflow) -> list[TaskResult]:
        """Submit a DAG workflow and return results in topological order."""
        return asyncio.run(self._submit_workflow_async(workflow))

    async def _submit_workflow_async(self, workflow: Workflow) -> list[TaskResult]:
        """Async implementation of submit_workflow."""
        errors = workflow.validate()
        if errors:
            raise ValueError(f"Workflow validation failed: {errors[0].message}")

        order = workflow.topological_order()
        tasks = [workflow.tasks()[tid] for tid in order]

        # Create a shared cancel event for the workflow
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

    def get_status(self, task_id: str) -> TaskStatus:
        """Return the current status of a task."""
        if task_id not in self._results:
            return TaskStatus.PENDING
        return self._results[task_id].status

    def wait_for(self, task_id: str, timeout: float | None = None) -> TaskResult:
        """Block until a task completes or timeout expires."""
        start = time.monotonic()
        while True:
            if task_id in self._results:
                return self._results[task_id]
            if timeout is not None and (time.monotonic() - start) > timeout:
                raise TimeoutError(f"wait_for {task_id} exceeded {timeout}s")
            time.sleep(0.05)

    def cancel(self, task_id: str) -> None:
        """Cancel a pending or running task."""
        event = self._cancel_events.get(task_id)
        if event:
            event.set()
        if task_id in self._results:
            self._results[task_id].status = TaskStatus.CANCELLED
