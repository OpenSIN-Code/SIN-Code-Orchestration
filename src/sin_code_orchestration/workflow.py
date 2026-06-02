"""DAG-based workflow engine with cycle detection and topological ordering.

Docs: workflow.doc.md
"""

from dataclasses import dataclass
from typing import Any

from .task import TaskSpec


@dataclass
class Error:
    """Validation error for workflow tasks."""

    task_id: str
    message: str


class Workflow:
    """Directed acyclic graph of tasks with dependencies."""

    def __init__(self):
        self._tasks: dict[str, TaskSpec] = {}
        self._deps: dict[str, set[str]] = {}
        self._dependents: dict[str, set[str]] = {}

    def add_task(self, task: TaskSpec) -> None:
        """Add a task to the workflow."""
        self._tasks[task.task_id] = task
        self._deps.setdefault(task.task_id, set())
        self._dependents.setdefault(task.task_id, set())
        for dep in task.dependencies:
            self._deps[task.task_id].add(dep)
            self._dependents.setdefault(dep, set()).add(task.task_id)

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add a manual dependency between two tasks."""
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        if depends_on not in self._tasks:
            raise ValueError(f"Dependency {depends_on} not found")
        self._deps[task_id].add(depends_on)
        self._dependents.setdefault(depends_on, set()).add(task_id)

    def validate(self) -> list[Error]:
        """Check for cycles and missing dependencies."""
        errors: list[Error] = []

        # Check missing deps
        for task_id, deps in self._deps.items():
            for dep in deps:
                if dep not in self._tasks:
                    errors.append(Error(task_id, f"Missing dependency: {dep}"))

        # Cycle detection using DFS
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {tid: WHITE for tid in self._tasks}
        stack: list[str] = []

        def dfs(node: str) -> bool:
            color[node] = GRAY
            stack.append(node)
            for neighbor in self._deps.get(node, set()):
                if neighbor not in self._tasks:
                    continue
                if color[neighbor] == GRAY:
                    # Cycle detected
                    cycle_start = stack.index(neighbor)
                    cycle = " → ".join(stack[cycle_start:] + [neighbor])
                    errors.append(Error(node, f"Cycle detected: {cycle}"))
                    return True
                if color[neighbor] == WHITE:
                    if dfs(neighbor):
                        return True
            stack.pop()
            color[node] = BLACK
            return False

        for tid in self._tasks:
            if color[tid] == WHITE:
                dfs(tid)

        return errors

    def topological_order(self) -> list[str]:
        """Return a valid execution order using Kahn's algorithm."""
        errors = self.validate()
        if errors:
            raise ValueError(f"Workflow invalid: {errors[0].message}")

        in_degree = {tid: 0 for tid in self._tasks}
        for tid, deps in self._deps.items():
            in_degree[tid] = len(deps)

        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        order: list[str] = []

        while queue:
            node = queue.pop(0)
            order.append(node)
            for dependent in self._dependents.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(order) != len(self._tasks):
            raise ValueError("Workflow contains a cycle")

        return order

    def tasks(self) -> dict[str, TaskSpec]:
        """Return a copy of the task mapping."""
        return dict(self._tasks)
