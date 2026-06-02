"""SIN-Code-Orchestration: DAG-based multi-agent orchestration engine.

Docs: orchestrator.doc.md
"""

from .role import Role
from .task import TaskSpec, TaskResult, TaskStatus
from .workflow import Workflow
from .orchestrator import Orchestrator

__all__ = [
    "Orchestrator",
    "TaskSpec",
    "TaskResult",
    "TaskStatus",
    "Role",
    "Workflow",
]
