"""SIN-Code-Orchestration: DAG-based multi-agent orchestration engine.

Re-exports the public API: `Orchestrator`, `TaskSpec`, `TaskResult`,
`TaskStatus`, `Role`, `Workflow`. See `orchestrator.doc.md` for the big
picture and the per-module docs for details.

Docs: __init__.doc.md
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
