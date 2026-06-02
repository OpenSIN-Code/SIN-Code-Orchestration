"""Role definitions for task assignment.

Docs: role.doc.md
"""

from enum import Enum


class Role(str, Enum):
    """Agent role for task assignment."""

    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    TESTER = "tester"
    ARCHITECT = "architect"
    ORCHESTRATOR = "orchestrator"
