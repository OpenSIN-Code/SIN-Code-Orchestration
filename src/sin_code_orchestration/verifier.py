"""Workflow verification using Oracle patterns.

Docs: verifier.doc.md
"""

from typing import Any

from .task import TaskResult, TaskStatus
from .workflow import Workflow


class Oracle:
    """Verifier that checks task results against expected patterns."""

    def __init__(self, rules: dict[str, Any] | None = None):
        self.rules = rules or {}

    def verify(self, result: TaskResult) -> dict[str, Any]:
        """Verify a single task result and return a report dict."""
        report: dict[str, Any] = {"passed": True, "checks": []}

        # Check status is SUCCESS
        if result.status != TaskStatus.SUCCESS:
            report["passed"] = False
            report["checks"].append({"check": "status", "passed": False, "detail": f"status={result.status.name}"})
        else:
            report["checks"].append({"check": "status", "passed": True})

        # Check output has expected keys
        expected_keys = self.rules.get(result.task_id, [])
        if expected_keys:
            missing = [k for k in expected_keys if k not in result.output]
            if missing:
                report["passed"] = False
                report["checks"].append({"check": "keys", "passed": False, "detail": f"missing={missing}"})
            else:
                report["checks"].append({"check": "keys", "passed": True})

        # Check no error
        if result.error:
            report["passed"] = False
            report["checks"].append({"check": "error", "passed": False, "detail": result.error})
        else:
            report["checks"].append({"check": "error", "passed": True})

        return report


class Verifier:
    """Workflow verifier that verifies each task result in a workflow."""

    def __init__(self, oracle: Oracle | None = None):
        self.oracle = oracle or Oracle()

    def verify(self, results: list[TaskResult]) -> list[dict[str, Any]]:
        """Verify a list of task results and return verification reports."""
        return [self.oracle.verify(r) for r in results]
