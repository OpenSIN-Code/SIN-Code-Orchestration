"""DAG-based workflow engine with cycle detection and topological ordering.

A `Workflow` is a directed acyclic graph of `TaskSpec` nodes. Two
operations are essential:
  - `validate`: catches missing dependencies and cycles.
  - `topological_order`: returns a valid execution order (Kahn's algorithm).

The orchestrator calls these before scheduling; a `ValueError` from either
aborts the workflow.

Docs: workflow.doc.md
"""

from dataclasses import dataclass
from typing import Any

from .task import TaskSpec


# ── Data model ─────────────────────────────────────────────────────────
@dataclass
class Error:
    """Validation error for workflow tasks."""

    task_id: str
    message: str


# ── Workflow ───────────────────────────────────────────────────────────
class Workflow:
    """Directed acyclic graph of tasks with dependencies.

    Internal storage:
      - `_tasks`: task_id → TaskSpec
      - `_deps`: task_id → set of dependency task_ids
      - `_dependents`: task_id → set of task_ids that depend on it
        (the reverse index is used by Kahn's algorithm).
    """

    def __init__(self):
        self._tasks: dict[str, TaskSpec] = {}
        self._deps: dict[str, set[str]] = {}
        self._dependents: dict[str, set[str]] = {}

    # ── Mutation ───────────────────────────────────────────────────────
    def add_task(self, task: TaskSpec) -> None:
        """Add a task to the workflow (with its declared dependencies).

        Both forward (`_deps`) and reverse (`_dependents`) indexes are
        updated so `topological_order` doesn't need a second pass.
        """
        self._tasks[task.task_id] = task
        self._deps.setdefault(task.task_id, set())
        self._dependents.setdefault(task.task_id, set())
        for dep in task.dependencies:
            self._deps[task.task_id].add(dep)
            self._dependents.setdefault(dep, set()).add(task.task_id)

    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add a manual dependency between two existing tasks.

        Both tasks must already be in the workflow; otherwise ValueError.
        """
        if task_id not in self._tasks:
            raise ValueError(f"Task {task_id} not found")
        if depends_on not in self._tasks:
            raise ValueError(f"Dependency {depends_on} not found")
        self._deps[task_id].add(depends_on)
        self._dependents.setdefault(depends_on, set()).add(task_id)

    # ── Validation ─────────────────────────────────────────────────────
    def validate(self) -> list[Error]:
        """Check for missing dependencies and cycles. Returns all errors (empty list = valid)."""
        errors: list[Error] = []

        # Check missing deps
        for task_id, deps in self._deps.items():
            for dep in deps:
                if dep not in self._tasks:
                    errors.append(Error(task_id, f"Missing dependency: {dep}"))

        # ── Cycle detection (DFS with 3-coloring) ──
        # WHITE = unvisited, GRAY = on current DFS path, BLACK = fully processed.
        # A GRAY neighbor = back-edge = cycle.
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {tid: WHITE for tid in self._tasks}
        # `stack` tracks the current DFS path so we can format the cycle
        # in human-readable form when we find one.
        stack: list[str] = []

        def dfs(node: str) -> bool:
            color[node] = GRAY
            stack.append(node)
            for neighbor in self._deps.get(node, set()):
                if neighbor not in self._tasks:
                    # Missing dep — already reported above; skip here.
                    continue
                if color[neighbor] == GRAY:
                    # Cycle detected — extract the cycle from the stack and
                    # format it as `a → b → c → a` for the error message.
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

        # Run DFS from every unvisited root. We don't bail on the first
        # error — we want to find ALL cycles so the user can fix them in
        # one pass.
        for tid in self._tasks:
            if color[tid] == WHITE:
                dfs(tid)

        return errors

    # ── Scheduling ─────────────────────────────────────────────────────
    def topological_order(self) -> list[str]:
        """Return a valid execution order using Kahn's algorithm.

        Raises:
            ValueError: if the workflow is invalid (cycles or missing deps).
                       Only the first error is surfaced; run `validate()`
                       directly to see all of them.
        """
        errors = self.validate()
        if errors:
            raise ValueError(f"Workflow invalid: {errors[0].message}")

        in_degree = {tid: 0 for tid in self._tasks}
        for tid, deps in self._deps.items():
            in_degree[tid] = len(deps)

        # Start with all roots (in-degree 0). Order within a level is
        # not guaranteed — use a list, not a set, for stable iteration.
        queue = [tid for tid, deg in in_degree.items() if deg == 0]
        order: list[str] = []

        while queue:
            # `pop(0)` is O(n) but `n` is the number of tasks, and the
            # overall algorithm is O(V + E) — a `deque` wouldn't change
            # asymptotic complexity for our typical workflow sizes.
            node = queue.pop(0)
            order.append(node)
            for dependent in self._dependents.get(node, set()):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # If we didn't visit every node, there's a cycle — `validate()`
        # should have caught it, but defense-in-depth.
        if len(order) != len(self._tasks):
            raise ValueError("Workflow contains a cycle")

        return order

    # ── Access ─────────────────────────────────────────────────────────
    def tasks(self) -> dict[str, TaskSpec]:
        """Return a copy of the task mapping.

        Returns a copy so callers can mutate the dict without affecting
        the workflow's internal state.
        """
        return dict(self._tasks)
