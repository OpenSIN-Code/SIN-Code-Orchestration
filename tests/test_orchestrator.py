import pytest
from sin_code_orchestration.orchestrator import Orchestrator, TaskSpec, Role
from sin_code_orchestration.shared_context import SharedContextStore, ContextStatus


def test_submit_task():
    orch = Orchestrator(config_path=None)
    spec = TaskSpec(
        task_id="test-1",
        description="Test task",
        role=Role.CODER,
        input_data={"code": "print('hello')"},
    )
    entry = orch.submit_task(spec)
    assert entry.task_id == "test-1"
    assert entry.status == ContextStatus.PENDING


def test_execute_task():
    orch = Orchestrator(config_path=None)
    spec = TaskSpec(
        task_id="test-2",
        description="Execute test",
        role=Role.CODER,
        input_data={"value": 42},
    )
    entry = orch.submit_task(spec)

    def execute_fn(input_data: dict) -> dict:
        return {"result": input_data["value"] * 2}

    result = orch.execute_task(entry.id, execute_fn)
    assert result.success
    assert result.output == {"result": 84}


def test_workflow_dependencies():
    orch = Orchestrator(config_path=None)
    tasks = [
        TaskSpec("t1", "First", Role.PLANNER, {"step": 1}),
        TaskSpec("t2", "Second", Role.CODER, {"step": 2}, dependencies=["t1"]),
    ]
    results = orch.run_workflow(tasks)
    assert results["t1"].success
    assert results["t2"].success
