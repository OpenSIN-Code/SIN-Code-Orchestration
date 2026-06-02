"""Task data structures.

Docs: task.doc.md
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from .role import Role


class TaskStatus(Enum):
    """Lifecycle states of a task."""

    PENDING = auto()
    RUNNING = auto()
    SUCCESS = auto()
    FAILED = auto()
    TIMEOUT = auto()
    CANCELLED = auto()


@dataclass
class TaskSpec:
    """Specification for a task to be executed."""

    task_id: str
    description: str
    role: Role
    input_data: dict[str, Any]
    dependencies: list[str] = field(default_factory=list)
    timeout: float = 300.0
    retry_count: int = 3

    def __post_init__(self):
        if self.timeout < 0:
            raise ValueError(
                f"timeout must be >= 0, got {self.timeout}"
            )


@dataclass
class TaskResult:
    """Result of a task execution."""

    task_id: str
    status: TaskStatus
    output: dict[str, Any]
    error: str | None
    duration_seconds: float
    verification: dict[str, Any] | None = None
