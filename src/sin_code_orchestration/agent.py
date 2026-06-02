"""Agent base class and built-in agents.

Docs: agent.doc.md
"""

from abc import ABC, abstractmethod
from typing import Any

from .role import Role
from .task import TaskSpec


class Agent(ABC):
    """Base class for task-executing agents."""

    def __init__(self, role: Role):
        self.role = role

    @abstractmethod
    def execute(self, task: TaskSpec) -> dict[str, Any]:
        """Execute the given task and return a dictionary of outputs."""


class EchoAgent(Agent):
    """Agent that returns the input data unchanged."""

    def __init__(self):
        super().__init__(Role.ORCHESTRATOR)

    def execute(self, task: TaskSpec) -> dict[str, Any]:
        return {"echo": task.input_data}


class TransformAgent(Agent):
    """Agent that applies a transformation function to input data."""

    def __init__(self, func: Any):
        super().__init__(Role.DEVELOPER)
        self.func = func

    def execute(self, task: TaskSpec) -> dict[str, Any]:
        return {"transformed": self.func(task.input_data)}


class FileAgent(Agent):
    """Agent that reads from or writes to a file."""

    def __init__(self, mode: str = "read"):
        super().__init__(Role.DEVELOPER)
        self.mode = mode

    def execute(self, task: TaskSpec) -> dict[str, Any]:
        path = task.input_data.get("path")
        content = task.input_data.get("content")
        if self.mode == "read":
            with open(path, "r", encoding="utf-8") as f:
                return {"content": f.read()}
        elif self.mode == "write":
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"written": True, "path": path}
        raise ValueError(f"Unsupported mode: {self.mode}")
