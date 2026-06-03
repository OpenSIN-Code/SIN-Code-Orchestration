"""Agent base class and built-in agents.

Docs: agent.doc.md
"""

import os
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

        # Resolve realpath and enforce workspace boundary
        real_path = os.path.realpath(path)
        home = os.path.expanduser("~")
        safe_prefixes = [home, "/tmp", "/private/tmp", "/var/tmp", "/private/var"]
        if not any(real_path.startswith(p) for p in safe_prefixes):
            raise ValueError(f"Path traversal detected: {path} resolves outside workspace")

        if self.mode == "read":
            with open(real_path, "r", encoding="utf-8") as f:
                return {"content": f.read()}
        elif self.mode == "write":
            with open(real_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"written": True, "path": real_path}
        raise ValueError(f"Unsupported mode: {self.mode}")
