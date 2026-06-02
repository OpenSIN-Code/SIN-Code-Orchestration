import pytest
import asyncio
import time
from sin_code_orchestration import Orchestrator, TaskSpec, TaskResult, TaskStatus, Role, Workflow
from sin_code_orchestration.agent import EchoAgent, TransformAgent, FileAgent
from sin_code_orchestration.context import Context
from sin_code_orchestration.workflow import Error
from sin_code_orchestration.verifier import Verifier, Oracle


# ── Role tests ──

def test_role_enum_values():
    assert Role.DEVELOPER.value == "developer"
    assert Role.REVIEWER.value == "reviewer"
    assert Role.TESTER.value == "tester"
    assert Role.ARCHITECT.value == "architect"
    assert Role.ORCHESTRATOR.value == "orchestrator"


# ── TaskSpec / TaskResult / TaskStatus ──

def test_task_spec_defaults():
    spec = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={})
    assert spec.dependencies == []
    assert spec.timeout == 300.0
    assert spec.retry_count == 3


def test_task_result_creation():
    result = TaskResult(
        task_id="t1",
        status=TaskStatus.SUCCESS,
        output={"k": "v"},
        error=None,
        duration_seconds=1.2,
    )
    assert result.status == TaskStatus.SUCCESS
    assert result.verification is None


# ── Workflow ──

def test_workflow_add_task():
    wf = Workflow()
    t1 = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={})
    wf.add_task(t1)
    assert "t1" in wf.tasks()


def test_workflow_add_dependency():
    wf = Workflow()
    t1 = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={})
    t2 = TaskSpec(task_id="t2", description="d", role=Role.DEVELOPER, input_data={}, dependencies=["t1"])
    wf.add_task(t1)
    wf.add_task(t2)
    order = wf.topological_order()
    assert order.index("t1") < order.index("t2")


def test_workflow_missing_dependency():
    wf = Workflow()
    t1 = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={}, dependencies=["missing"])
    wf.add_task(t1)
    errors = wf.validate()
    assert any("Missing dependency" in e.message for e in errors)


def test_workflow_cycle_detection():
    wf = Workflow()
    t1 = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={}, dependencies=["t3"])
    t2 = TaskSpec(task_id="t2", description="d", role=Role.DEVELOPER, input_data={}, dependencies=["t1"])
    t3 = TaskSpec(task_id="t3", description="d", role=Role.DEVELOPER, input_data={}, dependencies=["t2"])
    wf.add_task(t1)
    wf.add_task(t2)
    wf.add_task(t3)
    errors = wf.validate()
    assert any("Cycle detected" in e.message for e in errors)


def test_workflow_topological_order_raises_on_cycle():
    wf = Workflow()
    t1 = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={}, dependencies=["t2"])
    t2 = TaskSpec(task_id="t2", description="d", role=Role.DEVELOPER, input_data={}, dependencies=["t1"])
    wf.add_task(t1)
    wf.add_task(t2)
    with pytest.raises(ValueError):
        wf.topological_order()


def test_workflow_add_dependency_missing_task():
    wf = Workflow()
    t1 = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={})
    wf.add_task(t1)
    with pytest.raises(ValueError):
        wf.add_dependency("t1", "t2")


# ── Agent ──

def test_echo_agent():
    agent = EchoAgent()
    task = TaskSpec(task_id="t1", description="d", role=Role.ORCHESTRATOR, input_data={"a": 1})
    result = agent.execute(task)
    assert result["echo"] == {"a": 1}


def test_transform_agent():
    agent = TransformAgent(lambda d: d["x"] * 2)
    task = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={"x": 5})
    result = agent.execute(task)
    assert result["transformed"] == 10


def test_file_agent_read(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("hello")
    agent = FileAgent(mode="read")
    task = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={"path": str(f)})
    result = agent.execute(task)
    assert result["content"] == "hello"


def test_file_agent_write(tmp_path):
    f = tmp_path / "out.txt"
    agent = FileAgent(mode="write")
    task = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={"path": str(f), "content": "world"})
    result = agent.execute(task)
    assert result["written"] is True
    assert f.read_text() == "world"


# ── Context ──

def test_context_get_set():
    ctx = Context()
    ctx.set("a", 1)
    assert ctx.get("a") == 1
    assert ctx.get("b", 2) == 2


def test_context_merge():
    ctx = Context()
    ctx.merge({"x": 10, "y": 20})
    assert ctx.snapshot() == {"x": 10, "y": 20}


# ── Orchestrator single task ──

def test_orchestrator_submit_single_task():
    orch = Orchestrator()
    spec = TaskSpec(task_id="t1", description="d", role=Role.ORCHESTRATOR, input_data={"a": 1})
    result = orch.submit(spec)
    assert result.status == TaskStatus.SUCCESS
    assert result.output["echo"] == {"a": 1}
    assert result.verification is not None


def test_orchestrator_submit_with_custom_agent():
    orch = Orchestrator()
    orch.register_agent(Role.DEVELOPER, TransformAgent(lambda d: d["v"] + 1))
    spec = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={"v": 5})
    result = orch.submit(spec)
    assert result.status == TaskStatus.SUCCESS
    assert result.output["transformed"] == 6


def test_orchestrator_get_status():
    orch = Orchestrator()
    spec = TaskSpec(task_id="t1", description="d", role=Role.ORCHESTRATOR, input_data={})
    result = orch.submit(spec)
    assert orch.get_status("t1") == TaskStatus.SUCCESS


def test_orchestrator_wait_for():
    orch = Orchestrator()
    spec = TaskSpec(task_id="t1", description="d", role=Role.ORCHESTRATOR, input_data={})
    orch.submit(spec)
    result = orch.wait_for("t1", timeout=5.0)
    assert result.status == TaskStatus.SUCCESS


def test_orchestrator_wait_for_timeout():
    orch = Orchestrator()
    with pytest.raises(TimeoutError):
        orch.wait_for("unknown", timeout=0.1)


def test_orchestrator_cancel():
    orch = Orchestrator()
    spec = TaskSpec(task_id="t1", description="d", role=Role.ORCHESTRATOR, input_data={})
    orch.cancel("t1")
    result = orch.submit(spec)
    # If cancelled before submit, it may still run because event is set
    # But we verify cancel() does not crash.
    assert result.task_id == "t1"


# ── Orchestrator workflow ──

def test_orchestrator_workflow_success():
    orch = Orchestrator()
    wf = Workflow()
    t1 = TaskSpec(task_id="t1", description="d", role=Role.ORCHESTRATOR, input_data={"a": 1})
    t2 = TaskSpec(task_id="t2", description="d", role=Role.ORCHESTRATOR, input_data={"b": 2}, dependencies=["t1"])
    wf.add_task(t1)
    wf.add_task(t2)
    results = orch.submit_workflow(wf)
    assert len(results) == 2
    assert results[0].status == TaskStatus.SUCCESS
    assert results[1].status == TaskStatus.SUCCESS


def test_orchestrator_workflow_three_tasks():
    orch = Orchestrator()
    wf = Workflow()
    t1 = TaskSpec(task_id="t1", description="d", role=Role.ORCHESTRATOR, input_data={"a": 1})
    t2 = TaskSpec(task_id="t2", description="d", role=Role.ORCHESTRATOR, input_data={"b": 2}, dependencies=["t1"])
    t3 = TaskSpec(task_id="t3", description="d", role=Role.ORCHESTRATOR, input_data={"c": 3}, dependencies=["t2"])
    wf.add_task(t1)
    wf.add_task(t2)
    wf.add_task(t3)
    results = orch.submit_workflow(wf)
    assert [r.status for r in results] == [TaskStatus.SUCCESS, TaskStatus.SUCCESS, TaskStatus.SUCCESS]


def test_orchestrator_workflow_parallel_independent():
    orch = Orchestrator(max_concurrent=2)
    wf = Workflow()
    t1 = TaskSpec(task_id="t1", description="d", role=Role.ORCHESTRATOR, input_data={"a": 1})
    t2 = TaskSpec(task_id="t2", description="d", role=Role.ORCHESTRATOR, input_data={"b": 2})
    wf.add_task(t1)
    wf.add_task(t2)
    results = orch.submit_workflow(wf)
    assert len(results) == 2
    assert all(r.status == TaskStatus.SUCCESS for r in results)


def test_orchestrator_workflow_cycle_raises():
    orch = Orchestrator()
    wf = Workflow()
    t1 = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={}, dependencies=["t2"])
    t2 = TaskSpec(task_id="t2", description="d", role=Role.DEVELOPER, input_data={}, dependencies=["t1"])
    wf.add_task(t1)
    wf.add_task(t2)
    with pytest.raises(ValueError):
        orch.submit_workflow(wf)


def test_orchestrator_workflow_missing_dep_raises():
    orch = Orchestrator()
    wf = Workflow()
    t1 = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={}, dependencies=["missing"])
    wf.add_task(t1)
    with pytest.raises(ValueError):
        orch.submit_workflow(wf)


# ── Verifier / Oracle ──

def test_verifier_pass():
    result = TaskResult(
        task_id="t1",
        status=TaskStatus.SUCCESS,
        output={"k": "v"},
        error=None,
        duration_seconds=1.0,
    )
    verifier = Verifier()
    report = verifier.verify([result])[0]
    assert report["passed"] is True


def test_verifier_fail_status():
    result = TaskResult(
        task_id="t1",
        status=TaskStatus.FAILED,
        output={},
        error="boom",
        duration_seconds=1.0,
    )
    verifier = Verifier()
    report = verifier.verify([result])[0]
    assert report["passed"] is False


def test_oracle_with_rules():
    result = TaskResult(
        task_id="t1",
        status=TaskStatus.SUCCESS,
        output={"a": 1},
        error=None,
        duration_seconds=1.0,
    )
    oracle = Oracle({"t1": ["a", "b"]})
    report = oracle.verify(result)
    assert report["passed"] is False
    assert any(c["check"] == "keys" and not c["passed"] for c in report["checks"])


# ── Retry / timeout (executor-level) ──

async def _failing_handler(task: TaskSpec) -> dict:
    raise RuntimeError("always fails")


def test_executor_retry_exhaustion():
    from sin_code_orchestration.executor import execute_tasks
    spec = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={}, retry_count=2)
    results = asyncio.run(execute_tasks([spec], _failing_handler, max_concurrent=1))
    assert results[0].status == TaskStatus.FAILED
    assert "always fails" in results[0].error


async def _slow_handler(task: TaskSpec) -> dict:
    await asyncio.sleep(10)
    return {}


def test_executor_timeout():
    from sin_code_orchestration.executor import execute_tasks
    spec = TaskSpec(task_id="t1", description="d", role=Role.DEVELOPER, input_data={}, timeout=0.1)
    results = asyncio.run(execute_tasks([spec], _slow_handler, max_concurrent=1))
    assert results[0].status == TaskStatus.TIMEOUT


# ── Orchestrator with verifier disabled ──

def test_orchestrator_no_verifier():
    orch = Orchestrator(verifier=False)
    spec = TaskSpec(task_id="t1", description="d", role=Role.ORCHESTRATOR, input_data={})
    result = orch.submit(spec)
    assert result.verification is None
