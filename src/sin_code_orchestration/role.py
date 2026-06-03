"""Role definitions for task assignment.

Roles are the keys the orchestrator uses to look up the right agent for
a task. They double as `str` values (so they JSON-serialize cleanly),
which is what makes the MCP tools and the JSON workflow format ergonomic.

Docs: role.doc.md
"""

from enum import Enum


# ── Role enum ──────────────────────────────────────────────────────────
class Role(str, Enum):
    """Agent role for task assignment.

    Values:
      - DEVELOPER: writes / edits code.
      - REVIEWER:  reviews code, leaves comments.
      - TESTER:    runs tests, reports pass/fail.
      - ARCHITECT: designs / plans; rarely mutates files.
      - ORCHESTRATOR: default fallback role (EchoAgent is registered here).
    """

    DEVELOPER = "developer"
    REVIEWER = "reviewer"
    TESTER = "tester"
    ARCHITECT = "architect"
    ORCHESTRATOR = "orchestrator"
