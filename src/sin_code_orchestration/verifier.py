"""VMAO-style Verification Loop für Agenten-Arbeitsabläufe."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

import structlog

from .shared_context import SharedContextStore, ContextEntry, ContextStatus


logger = structlog.get_logger()


class VerificationStep(str, Enum):
    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    REPLAN = "replan"
    COMPLETE = "complete"
    ESCALATE = "escalate"


@dataclass
class VerificationResult:
    step: VerificationStep
    success: bool
    output: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    next_step: Optional[VerificationStep] = None
    confidence: float = 0.0


class VerificationLoop:
    """Plan-Ausführen-Verifizieren-Replan-Zyklus für zuverlässige Agenten-Abläufe."""

    def __init__(
        self,
        ctx_store: SharedContextStore,
        max_retries: int = 3,
        escalate_on_failure: bool = True,
        min_confidence: float = 0.8,
    ):
        self.ctx_store = ctx_store
        self.max_retries = max_retries
        self.escalate_on_failure = escalate_on_failure
        self.min_confidence = min_confidence
        self._callbacks: dict[VerificationStep, list[Callable]] = {
            VerificationStep.PLAN: [],
            VerificationStep.EXECUTE: [],
            VerificationStep.VERIFY: [],
            VerificationStep.REPLAN: [],
        }

    def register_callback(self, step: VerificationStep, callback: Callable):
        """Registriert eine Callback-Funktion für einen Verification-Step."""
        self._callbacks[step].append(callback)

    def _run_callbacks(self, step: VerificationStep, context: dict) -> dict:
        for cb in self._callbacks.get(step, []):
            try:
                result = cb(context)
                if result:
                    context.update(result)
            except Exception as e:
                logger.warning("Callback failed", step=step.value, error=str(e))
        return context

    def run(
        self,
        entry_id: str,
        plan_fn: Callable[[dict], dict],
        execute_fn: Callable[[dict], dict],
        verify_fn: Callable[[dict], VerificationResult],
        replan_fn: Optional[Callable[[dict, str], dict]] = None,
    ) -> VerificationResult:
        """Führt den vollständigen Verification-Zyklus aus."""
        entry = self.ctx_store.get(entry_id)
        if not entry:
            return VerificationResult(
                step=VerificationStep.PLAN,
                success=False,
                error="Entry not found",
            )

        context = {"entry": entry, "input": entry.input_data, "attempts": 0}
        current_step = VerificationStep.PLAN
        last_error = None

        while current_step != VerificationStep.COMPLETE:
            context = self._run_callbacks(current_step, context)

            if current_step == VerificationStep.PLAN:
                try:
                    plan = plan_fn(context["input"])
                    context["plan"] = plan
                    self.ctx_store.update_status(entry_id, ContextStatus.IN_PROGRESS)
                    current_step = VerificationStep.EXECUTE
                except Exception as e:
                    last_error = str(e)
                    current_step = VerificationStep.ESCALATE if self.escalate_on_failure else VerificationStep.REPLAN

            elif current_step == VerificationStep.EXECUTE:
                try:
                    output = execute_fn(context["plan"])
                    context["output"] = output
                    current_step = VerificationStep.VERIFY
                except Exception as e:
                    last_error = str(e)
                    context["attempts"] += 1
                    if context["attempts"] >= self.max_retries:
                        current_step = VerificationStep.ESCALATE if self.escalate_on_failure else VerificationStep.REPLAN
                    else:
                        current_step = VerificationStep.REPLAN

            elif current_step == VerificationStep.VERIFY:
                result = verify_fn(context)
                if result.success and result.confidence >= self.min_confidence:
                    self.ctx_store.update_status(
                        entry_id, ContextStatus.VERIFIED, output_data=context.get("output")
                    )
                    return VerificationResult(
                        step=VerificationStep.COMPLETE,
                        success=True,
                        output=context.get("output"),
                        confidence=result.confidence,
                    )
                else:
                    last_error = result.error or "Verification failed"
                    context["attempts"] += 1
                    if context["attempts"] >= self.max_retries:
                        current_step = VerificationStep.ESCALATE if self.escalate_on_failure else VerificationStep.REPLAN
                    else:
                        current_step = VerificationStep.REPLAN

            elif current_step == VerificationStep.REPLAN:
                if replan_fn:
                    try:
                        new_plan = replan_fn(context, last_error)
                        context["plan"] = new_plan
                        current_step = VerificationStep.EXECUTE
                    except Exception as e:
                        last_error = str(e)
                        current_step = VerificationStep.ESCALATE if self.escalate_on_failure else VerificationStep.COMPLETE
                else:
                    current_step = VerificationStep.ESCALATE

            elif current_step == VerificationStep.ESCALATE:
                self.ctx_store.update_status(entry_id, ContextStatus.FAILED, error=last_error)
                return VerificationResult(
                    step=VerificationStep.ESCALATE,
                    success=False,
                    error=last_error,
                )

            time.sleep(0.1)  # Prevent tight loops

        # Fallback completion
        self.ctx_store.update_status(entry_id, ContextStatus.COMPLETED, output_data=context.get("output"))
        return VerificationResult(
            step=VerificationStep.COMPLETE,
            success=True,
            output=context.get("output"),
        )
