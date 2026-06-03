"""Task data structures — the core data model of the orchestrator.

`TaskStatus` is the lifecycle enum, `TaskSpec` is the input to the
executor, and `TaskResult` is its output. These three classes are
intentionally minimal — anything more complex belongs in a wrapper.

Docs: task.doc.md
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .role import Role


# ── Status enum ────────────────────────────────────────────────────────
class TaskStatus(Enum):
    """Lifecycle states of a task.

    Note: `RUNNING` is reserved but the current executor doesn't surface
    it (it goes straight from `PENDING` to a terminal state). The value
    exists for future observability work.
    """

    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    TIMEOUT = auto()
    CANCELLED = auto()


# ── Spec (input) ───────────────────────────────────────────────────────
@dataclass
class TaskSpec:
    """Specification for a task to be executed.

    Defaults:
      - `timeout=300.0` (5 minutes): long enough for most LLM calls,
        short enough to fail fast on a hung subprocess.
      - `retry_count=3`: gives the executor 4 total attempts (initial + 3 retries).
    """

    task_id: str
    description: str
    role: Role
    input_data: dict[str, Any]
    dependencies: list[str] = field(default_factory=list)
    timeout: float = 300.0
    retry_count: int = 3

    def __post_init__(self):
        # Reject negative timeouts at construction time so the executor
        # doesn't have to. `timeout=0` is allowed (means "no time to run") —
        # the executor will TIMEOUT immediately. Only `< 0` is invalid.
        if self.timeout < 0:
            raise ValueError(
                f"timeout must be >= 0, got {self.timeout}"
            )


# ── Result (output) ────────────────────────────────────────────────────
@dataclass
class TaskResult:
    """Result of a task execution.

    `verification` is `None` unless the orchestrator was created with
    `verifier=True` (the default) AND the result was verified.
    """

    task_id: str
    status: TaskStatus
    output: dict[str, Any]
    error: str | None
    duration_seconds: float
    verification: dict[str, Any] | None = None
