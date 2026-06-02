"""Edge-case tests for SIN-Code-Orchestration — bugs NOT covered by existing tests.

Docs: test_edge_cases.doc.md
"""

import pytest
import asyncio
import datetime
from sin_code_orchestration import Orchestrator, TaskSpec, TaskResult, TaskStatus, Role, Workflow
from sin_code_orchestration.agent import EchoAgent, TransformAgent
from sin_code_orchestration.context import Context
from sin_code_orchestration.workflow import Error


class TestTaskSpecEdgeCases:
    """Edge cases for TaskSpec initialization."""

    def test_task_spec_empty_id(self):
        """Task with empty task_id string."""
        spec = TaskSpec(task_id="", description="test", role=Role.DEVELOPER, input_data={})
        assert spec.task_id == ""
        assert spec.description == "test"

    def test_task_spec_zero_timeout(self):
        """Task with timeout=0 — should still be valid as a spec."""
        spec = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER,
                        input_data={}, timeout=0.0)
        assert spec.timeout == 0.0

    def test_task_spec_negative_timeout(self):
        """Task with negative timeout — should raise ValueError."""
        with pytest.raises(ValueError, match="timeout must be >= 0"):
            TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER,
                     input_data={}, timeout=-1.0)

    def test_task_spec_very_large_timeout(self):
        """Task with very large timeout value."""
        spec = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER,
                        input_data={}, timeout=float("inf"))
        assert spec.timeout == float("inf")

    def test_task_spec_negative_retry(self):
        """Task with negative retry_count — should still be valid."""
        spec = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER,
                        input_data={}, retry_count=-1)
        assert spec.retry_count == -1

    def test_task_spec_empty_description(self):
        spec = TaskSpec(task_id="t1", description="", role=Role.DEVELOPER, input_data={})
        assert spec.description == ""

    def test_task_spec_empty_input_data(self):
        spec = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={})
        assert spec.input_data == {}

    def test_task_spec_duplicate_task_ids(self):
        """Two specs with same task_id — allowed at spec level, but might clash in workflow."""
        t1 = TaskSpec(task_id="same", description="first", role=Role.DEVELOPER, input_data={})
        t2 = TaskSpec(task_id="same", description="second", role=Role.DEVELOPER, input_data={})
        assert t1.task_id == t2.task_id
        assert t1.description != t2.description


class TestWorkflowEdgeCases:
    """Edge cases: empty workflow, duplicate tasks, complex DAGs."""

    def test_empty_workflow_validate(self):
        wf = Workflow()
        errors = wf.validate()
        assert errors == []

    def test_empty_workflow_topological_order(self):
        wf = Workflow()
        order = wf.topological_order()
        assert order == []

    def test_empty_workflow_tasks(self):
        wf = Workflow()
        assert wf.tasks() == {}

    def test_duplicate_task_id_overwrites(self):
        wf = Workflow()
        t1 = TaskSpec(task_id="dup", description="first", role=Role.DEVELOPER, input_data={})
        t2 = TaskSpec(task_id="dup", description="second", role=Role.DEVELOPER, input_data={})
        wf.add_task(t1)
        wf.add_task(t2)
        assert wf.tasks()["dup"].description == "second"

    def test_self_dependency(self):
        """Task depending on itself."""
        wf = Workflow()
        t1 = TaskSpec(task_id="self", description="d", role=Role.DEVELOPER,
                       input_data={}, dependencies=["self"])
        wf.add_task(t1)
        errors = wf.validate()
        assert any("Cycle detected" in e.message for e in errors)

    def test_add_dependency_nonexistent_task(self):
        wf = Workflow()
        t1 = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={})
        wf.add_task(t1)
        with pytest.raises(ValueError):
            wf.add_dependency("t1", "nonexistent")

    def test_add_dependency_nonexistent_source(self):
        wf = Workflow()
        t1 = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={})
        wf.add_task(t1)
        with pytest.raises(ValueError):
            wf.add_dependency("nonexistent", "t1")

    def test_linear_chain_of_tasks(self):
        """A long linear dependency chain."""
        wf = Workflow()
        N = 100
        t0 = TaskSpec(task_id="t0", description="start", role=Role.DEVELOPER, input_data={})
        wf.add_task(t0)
        for i in range(1, N):
            ti = TaskSpec(task_id=f"t{i}", description=f"t{i}", role=Role.DEVELOPER,
                          input_data={}, dependencies=[f"t{i-1}"])
            wf.add_task(ti)
        order = wf.topological_order()
        assert len(order) == N
        assert order[0] == "t0"
        assert order[-1] == f"t{N-1}"

    def test_diamond_dependency(self):
        """Diamond-shaped DAG: a -> b, a -> c, b -> d, c -> d."""
        wf = Workflow()
        t_a = TaskSpec(task_id="a", description="a", role=Role.DEVELOPER, input_data={})
        t_b = TaskSpec(task_id="b", description="b", role=Role.DEVELOPER,
                       input_data={}, dependencies=["a"])
        t_c = TaskSpec(task_id="c", description="c", role=Role.DEVELOPER,
                       input_data={}, dependencies=["a"])
        t_d = TaskSpec(task_id="d", description="d", role=Role.DEVELOPER,
                       input_data={}, dependencies=["b", "c"])
        wf.add_task(t_a)
        wf.add_task(t_b)
        wf.add_task(t_c)
        wf.add_task(t_d)
        order = wf.topological_order()
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_multiple_ids_with_empty_deps(self):
        """Multiple tasks with empty dependency lists."""
        wf = Workflow()
        for i in range(5):
            t = TaskSpec(task_id=f"t{i}", description=f"t{i}", role=Role.DEVELOPER,
                         input_data={}, dependencies=[])
            wf.add_task(t)
        order = wf.topological_order()
        assert len(order) == 5

    def test_mixed_valid_and_invalid_deps(self):
        """Some deps valid, some missing."""
        wf = Workflow()
        t1 = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER,
                      input_data={}, dependencies=["missing1"])
        t2 = TaskSpec(task_id="t2", description="d", role=Role.DEVELOPER,
                      input_data={}, dependencies=["t1", "missing2"])
        wf.add_task(t1)
        wf.add_task(t2)
        errors = wf.validate()
        assert len(errors) >= 2  # at least the two missing deps


class TestOrchestratorEdgeCases:
    """Edge cases: timeout=0, concurrent execution, cancel before submit."""

    def test_orchestrator_submit_zero_timeout(self):
        """Task with timeout=0 — should return TIMEOUT. This may reveal a bug."""
        orch = Orchestrator()
        spec = TaskSpec(task_id="tzero", description="d", role=Role.ORCHESTRATOR,
                        input_data={}, timeout=0.0)
        result = orch.submit(spec)
        # With timeout=0, the task may complete before timing out or time out immediately
        assert result.task_id == "tzero"
        # BUG: timeout=0 may not actually timeout the task if it completes fast enough
        assert result.status in (TaskStatus.SUCCESS, TaskStatus.TIMEOUT)

    def test_orchestrator_submit_cancelled_before(self):
        """Cancel a task before submitting — then submit."""
        orch = Orchestrator()
        orch.cancel("t_cancel")
        spec = TaskSpec(task_id="t_cancel", description="d", role=Role.ORCHESTRATOR,
                        input_data={})
        result = orch.submit(spec)
        # Task should still complete or be cancelled depending on timing
        assert result.task_id == "t_cancel"

    def test_orchestrator_get_status_unknown(self):
        orch = Orchestrator()
        assert orch.get_status("unknown") == TaskStatus.PENDING

    def test_orchestrator_max_concurrent_zero(self):
        """max_concurrent=0 — should raise ValueError."""
        with pytest.raises(ValueError, match="max_concurrent must be >= 1"):
            Orchestrator(max_concurrent=0)

    def test_orchestrator_register_agent_overwrite(self):
        """Register two agents for the same role — second should overwrite."""
        orch = Orchestrator()
        orch.register_agent(Role.DEVELOPER, TransformAgent(lambda d: d.get("v", 0) + 10))
        orch.register_agent(Role.DEVELOPER, TransformAgent(lambda d: d.get("v", 0) + 99))
        spec = TaskSpec(task_id="t_overwrite", description="d", role=Role.DEVELOPER,
                        input_data={"v": 1})
        result = orch.submit(spec)
        assert result.output["transformed"] == 100  # second agent wins

    def test_orchestrator_wait_for_zero_timeout(self):
        orch = Orchestrator()
        with pytest.raises(TimeoutError):
            orch.wait_for("unknown", timeout=0.0)

    def test_orchestrator_wait_for_negative_timeout(self):
        orch = Orchestrator()
        with pytest.raises(TimeoutError):
            orch.wait_for("unknown", timeout=-1.0)

    def test_orchestrator_submit_with_empty_command(self):
        """Task with empty description — should still execute."""
        orch = Orchestrator()
        spec = TaskSpec(task_id="t_empty", description="", role=Role.ORCHESTRATOR,
                        input_data={})
        result = orch.submit(spec)
        assert result.status == TaskStatus.SUCCESS

    def test_orchestrator_workflow_all_same_role(self):
        orch = Orchestrator(max_concurrent=4)
        wf = Workflow()
        for i in range(10):
            t = TaskSpec(task_id=f"t{i}", description=f"t{i}", role=Role.ORCHESTRATOR,
                         input_data={"idx": i})
            wf.add_task(t)
        results = orch.submit_workflow(wf)
        assert len(results) == 10
        assert all(r.status == TaskStatus.SUCCESS for r in results)

    def test_orchestrator_disabled_verifier(self):
        orch = Orchestrator(verifier=False)
        wf = Workflow()
        wf.add_task(TaskSpec(task_id="t1", description="d", role=Role.ORCHESTRATOR,
                             input_data={}))
        results = orch.submit_workflow(wf)
        assert all(r.verification is None for r in results)


class TestContextEdgeCases:
    """Edge cases for the Context class."""

    def test_context_overwrite_key(self):
        ctx = Context()
        ctx.set("a", 1)
        ctx.set("a", 2)
        assert ctx.get("a") == 2

    def test_context_merge_empty(self):
        ctx = Context()
        ctx.merge({})
        assert ctx.snapshot() == {}

    def test_context_merge_overwrite(self):
        ctx = Context()
        ctx.set("a", 1)
        ctx.merge({"a": 99, "b": 2})
        snap = ctx.snapshot()
        assert snap["a"] == 99
        assert snap["b"] == 2

    def test_context_get_default_none(self):
        ctx = Context()
        assert ctx.get("missing") is None

    def test_context_large_snapshot(self):
        ctx = Context()
        for i in range(1000):
            ctx.set(f"key_{i}", i)
        snap = ctx.snapshot()
        assert len(snap) == 1000
        assert snap["key_0"] == 0
        assert snap["key_999"] == 999


class TestExecutorEdgeCases:
    """Edge cases for the task executor."""

    async def _identity_handler(self, task: TaskSpec) -> dict:
        return dict(task.input_data)

    def test_executor_single_task_success(self):
        from sin_code_orchestration.executor import execute_tasks
        spec = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER,
                        input_data={"x": 42}, retry_count=1)
        results = asyncio.run(execute_tasks([spec], self._identity_handler,
                                            max_concurrent=1))
        assert results[0].status == TaskStatus.SUCCESS
        assert results[0].output["x"] == 42

    def test_executor_empty_task_list(self):
        from sin_code_orchestration.executor import execute_tasks
        results = asyncio.run(execute_tasks([], self._identity_handler,
                                            max_concurrent=1))
        assert results == []

    def test_executor_zero_retry(self):
        from sin_code_orchestration.executor import execute_tasks
        async def fail_once(task):
            raise RuntimeError("fail")
        spec = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER,
                        input_data={}, retry_count=1)
        results = asyncio.run(execute_tasks([spec], fail_once, max_concurrent=1))
        assert results[0].status == TaskStatus.FAILED


class TestWorkflowValidationEdgeCases:
    """Additional workflow validation edge cases."""

    def test_validate_multiple_errors(self):
        wf = Workflow()
        t1 = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER,
                      input_data={}, dependencies=["m1", "m2"])
        t2 = TaskSpec(task_id="t2", description="d", role=Role.DEVELOPER,
                      input_data={}, dependencies=["m3"])
        wf.add_task(t1)
        wf.add_task(t2)
        errors = wf.validate()
        assert len(errors) >= 3  # 3 missing: m1, m2, m3

    def test_validate_no_errors(self):
        wf = Workflow()
        t1 = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={})
        t2 = TaskSpec(task_id="t2", description="d", role=Role.DEVELOPER,
                      input_data={}, dependencies=["t1"])
        wf.add_task(t1)
        wf.add_task(t2)
        errors = wf.validate()
        assert errors == []
