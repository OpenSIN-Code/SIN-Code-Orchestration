"""Workflow verification using Oracle patterns.

A two-layer API:
  - `Oracle`: checks one `TaskResult` against three rules (status, keys,
    no-error). Each rule produces a `{"check", "passed", "detail"}` entry.
  - `Verifier`: wraps an `Oracle` and applies it to a list of results
    (one report per result, in the same order).

The `Oracle` is the policy; the `Verifier` is the bulk runner.

Docs: verifier.doc.md
"""

from typing import Any

from .task import TaskResult, TaskStatus
from .workflow import Workflow


# ── Oracle ─────────────────────────────────────────────────────────────
class Oracle:
    """Verifier that checks task results against expected patterns.

    Three checks, all default-on:
      1. `status` — is the result SUCCESS?
      2. `keys`   — does `output` contain the keys listed in `rules[task_id]`?
                     (Skipped if no rules are registered for the task.)
      3. `error`  — is `error` None / empty?

    A task "passes" iff all applicable checks pass.
    """

    def __init__(self, rules: dict[str, Any] | None = None):
        # `rules` maps task_id → list of expected output keys.
        # An empty dict (default) means "don't enforce any key rules".
        self.rules = rules or {}

    def verify(self, result: TaskResult) -> dict[str, Any]:
        """Verify a single task result and return a report dict.

        Report shape:
            {"passed": bool, "checks": [{"check", "passed", "detail"}]}
        """
        report: dict[str, Any] = {"passed": True, "checks": []}

        # ── Check 1: status ──
        if result.status != TaskStatus.SUCCESS:
            report["passed"] = False
            report["checks"].append({"check": "status", "passed": False, "detail": f"status={result.status.name}"})
        else:
            report["checks"].append({"check": "status", "passed": True})

        # ── Check 2: expected output keys ──
        # Skipped entirely when no rules are registered for this task.
        # When rules exist, every listed key MUST be present in `output`.
        expected_keys = self.rules.get(result.task_id, [])
        if expected_keys:
            missing = [k for k in expected_keys if k not in result.output]
            if missing:
                report["passed"] = False
                report["checks"].append({"check": "keys", "passed": False, "detail": f"missing={missing}"})
            else:
                report["checks"].append({"check": "keys", "passed": True})

        # ── Check 3: no error ──
        if result.error:
            report["passed"] = False
            report["checks"].append({"check": "error", "passed": False, "detail": result.error})
        else:
            report["checks"].append({"check": "error", "passed": True})

        return report


# ── Verifier ───────────────────────────────────────────────────────────
class Verifier:
    """Workflow verifier that verifies each task result in a workflow."""

    def __init__(self, oracle: Oracle | None = None):
        # Default Oracle = "no key rules" (status + error only).
        # Pass a configured Oracle for stricter verification.
        self.oracle = oracle or Oracle()

    def verify(self, results: list[TaskResult]) -> list[dict[str, Any]]:
        """Verify a list of task results and return verification reports.

        Returns one report per result, in the same order. Empty input → empty output.
        """
        return [self.oracle.verify(r) for r in results]
