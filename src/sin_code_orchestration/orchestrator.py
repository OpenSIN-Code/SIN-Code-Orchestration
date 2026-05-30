"""Haupt-Orchestrator für Multi-Agenten-Workflows."""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import structlog
import yaml

from .shared_context import SharedContextStore, ContextEntry, ContextStatus
from .roles import AgentConfig, Role, ToolPermission
from .verifier import VerificationLoop, VerificationResult, VerificationStep


logger = structlog.get_logger()


@dataclass
class TaskSpec:
    """Spezifikation einer Agenten-Aufgabe."""
    task_id: str
    description: str
    role: Role
    input_data: dict[str, Any]
    dependencies: list[str] = field(default_factory=list)
    timeout_seconds: int = 300
    require_verification: bool = True


@dataclass
class TaskResult:
    """Ergebnis einer ausgeführten Aufgabe."""
    task_id: str
    success: bool
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    verification_passed: bool = False


class Orchestrator:
    """Koordiniert Multi-Agenten-Workflows mit Verification."""

    def __init__(self, config_path: Optional[str] = "config.yaml"):
        self.config = {}
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                self.config = yaml.safe_load(f) or {}

        ctx_cfg = self.config.get("context_store", {})
        self.ctx_store = SharedContextStore(
            backend=ctx_cfg.get("backend", "memory"),
            redis_url=ctx_cfg.get("redis_url"),
            namespace=ctx_cfg.get("namespace"),
        )
        self.verifier = VerificationLoop(
            self.ctx_store,
            max_retries=self.config.get("verification", {}).get("max_retries", 3),
            escalate_on_failure=self.config.get("verification", {}).get("escalate_on_failure", True),
        )
        self._agent_configs: dict[str, AgentConfig] = {}
        self._init_agent_configs()

    def _init_agent_configs(self):
        roles_cfg = self.config.get("roles", {})
        for role_name, role_cfg in roles_cfg.items():
            tools = [ToolPermission(name=t) for t in role_cfg.get("tools", [])]
            self._agent_configs[role_name] = AgentConfig(
                agent_id=f"{role_name}-default",
                role=Role(role_name),
                model=role_cfg.get("model", "gpt-4o"),
                tools=tools,
                max_iterations=role_cfg.get("max_iterations", 10),
                timeout_seconds=role_cfg.get("timeout_seconds", 300),
                sandbox=role_cfg.get("sandbox", False),
                require_approval=role_cfg.get("require_approval", False),
            )

    def submit_task(self, spec: TaskSpec) -> ContextEntry:
        """Reicht eine neue Aufgabe ein."""
        entry = self.ctx_store.create_entry(
            task_id=spec.task_id,
            agent_id=f"{spec.role.value}-default",
            role=spec.role.value,
            input_data=spec.input_data,
            dependencies=spec.dependencies,
        )
        logger.info("Task submitted", task_id=spec.task_id, entry_id=entry.id)
        return entry

    def execute_task(
        self,
        entry_id: str,
        execute_fn,
        verify_fn=None,
    ) -> TaskResult:
        """Führt eine Aufgabe mit optionaler Verifikation aus."""
        entry = self.ctx_store.get(entry_id)
        if not entry:
            return TaskResult(task_id="", success=False, error="Entry not found")

        start = time.time()

        def default_verify(ctx: dict) -> VerificationResult:
            return VerificationResult(
                step=VerificationStep.VERIFY,
                success=True,
                confidence=0.9,
            )

        result = self.verifier.run(
            entry_id=entry_id,
            plan_fn=lambda inp: {"plan": "execute", "input": inp},
            execute_fn=lambda plan: execute_fn(plan["input"]),
            verify_fn=verify_fn or default_verify,
        )

        duration = time.time() - start
        return TaskResult(
            task_id=entry.task_id,
            success=result.success,
            output=result.output,
            error=result.error,
            duration_seconds=round(duration, 2),
            verification_passed=result.step == VerificationStep.COMPLETE,
        )

    def run_workflow(self, tasks: list[TaskSpec]) -> dict[str, TaskResult]:
        """Führt einen Workflow mit mehreren abhängigen Aufgaben aus."""
        results: dict[str, TaskResult] = {}

        # Topologische Sortierung der Tasks nach Dependencies
        pending = {t.task_id: t for t in tasks}
        completed = set()

        while pending:
            ready = [
                tid for tid, task in pending.items()
                if all(dep in completed for dep in task.dependencies)
            ]
            if not ready:
                # Deadlock oder fehlende Dependency
                for tid, task in pending.items():
                    results[tid] = TaskResult(
                        task_id=tid,
                        success=False,
                        error=f"Unresolved dependencies: {task.dependencies}"
                    )
                break

            for task_id in ready:
                task = pending.pop(task_id)
                entry = self.submit_task(task)

                # Placeholder-Execute-Funktion (wird durch Agent ersetzt)
                def execute_fn(input_data: dict, _tid=task_id) -> dict:
                    return {"status": "executed", "task": _tid}

                result = self.execute_task(entry.id, execute_fn)
                results[task_id] = result

                if result.success:
                    completed.add(task_id)
                else:
                    logger.error("Task failed", task_id=task_id, error=result.error)
                    if task.require_verification:
                        # Abbruch bei kritischen Tasks
                        break

            time.sleep(0.1)

        return results

    def status(self, task_id: Optional[str] = None) -> dict:
        """Gibt den Status von Tasks zurück."""
        entries = self.ctx_store.query(task_id=task_id)
        return {
            "total": len(entries),
            "by_status": {
                s.value: sum(1 for e in entries if e.status == s)
                for s in ContextStatus
            },
            "entries": [
                {
                    "id": e.id,
                    "task_id": e.task_id,
                    "role": e.role,
                    "status": e.status.value,
                    "created_at": e.created_at,
                }
                for e in entries
            ],
        }
