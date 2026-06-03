"""Agent base class and built-in agents.

Defines the `Agent` ABC plus three reference implementations: `EchoAgent`
(passes input through unchanged), `TransformAgent` (applies a callable),
and `FileAgent` (read/write a file inside a workspace boundary). Use the
base class to plug in your own agent (LLM-backed, tool-using, etc.).

Docs: agent.doc.md
"""

import os
from abc import ABC, abstractmethod
from typing import Any

from .role import Role
from .task import TaskSpec


# ── Base class ─────────────────────────────────────────────────────────
class Agent(ABC):
    """Base class for task-executing agents.

    Subclasses must implement `execute()`. The orchestrator looks up the
    right agent for a task via `task.role → agent`.
    """

    def __init__(self, role: Role):
        self.role = role

    @abstractmethod
    def execute(self, task: TaskSpec) -> dict[str, Any]:
        """Execute the given task and return a dictionary of outputs.

        Implementations may be sync or async (the orchestrator awaits
        their coroutine). The returned dict becomes `TaskResult.output`.
        """
        raise NotImplementedError


# ── Built-in agents ────────────────────────────────────────────────────
class EchoAgent(Agent):
    """Agent that returns the input data unchanged.

    Useful as a default placeholder or for testing the orchestrator wiring
    without spinning up a real agent.
    """

    def __init__(self):
        # EchoAgent plays the ORCHESTRATOR role by default — it's the
        # "no-op dispatch" agent when no role-specific agent is registered.
        super().__init__(Role.ORCHESTRATOR)

    def execute(self, task: TaskSpec) -> dict[str, Any]:
        return {"echo": task.input_data}


class TransformAgent(Agent):
    """Agent that applies a callable to the input data.

    `func` is called with the raw `task.input_data` and its return value
    is wrapped in `{"transformed": ...}`. The callable should be pure
    (no side effects) — use a different agent if you need I/O.
    """

    def __init__(self, func: Any):
        super().__init__(Role.DEVELOPER)
        self.func = func

    def execute(self, task: TaskSpec) -> dict[str, Any]:
        return {"transformed": self.func(task.input_data)}


class FileAgent(Agent):
    """Agent that reads from or writes to a file inside a workspace boundary.

    `mode` is `"read"` (returns `{"content": ...}`) or `"write"` (returns
    `{"written": True, "path": ...}`). Path traversal protection: the
    resolved path MUST start with one of the safe prefixes below.
    """

    def __init__(self, mode: str = "read"):
        super().__init__(Role.DEVELOPER)
        self.mode = mode

    def execute(self, task: TaskSpec) -> dict[str, Any]:
        path = task.input_data.get("path")
        content = task.input_data.get("content")

        # ── Path-traversal guard ──
        # `realpath` resolves symlinks, so `~/../../etc/passwd` becomes
        # `/etc/passwd` and gets caught by the safe_prefix check below.
        real_path = os.path.realpath(path)
        # Safe roots: the user's home dir + the standard temp dirs.
        # Anything outside these (e.g. /etc, /var/log) is rejected. macOS
        # uses /private/tmp as the canonical /tmp — we include both forms.
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
