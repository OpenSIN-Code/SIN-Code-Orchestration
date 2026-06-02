# SIN-Code-Orchestration

DAG-based multi-agent orchestration engine with parallel execution, retry, and verification.

## Install

```bash
pip install sin-code-orchestration
```

## Quick Start

```python
from sin_code_orchestration import Orchestrator, TaskSpec, Role, Workflow

orch = Orchestrator()

# Single task
spec = TaskSpec(task_id="t1", description="Say hello", role=Role.DEVELOPER, input_data={"text": "hello"})
result = orch.submit(spec)
print(result.status)  # SUCCESS

# Workflow with dependencies
wf = Workflow()
wf.add_task(TaskSpec(task_id="build", description="Build", role=Role.DEVELOPER, input_data={}))
wf.add_task(TaskSpec(task_id="test", description="Test", role=Role.TESTER, input_data={}, dependencies=["build"]))
wf.add_task(TaskSpec(task_id="deploy", description="Deploy", role=Role.ARCHITECT, input_data={}, dependencies=["test"]))
results = orch.submit_workflow(wf)
```

## API

- `Orchestrator(max_concurrent=4, verifier=True)` — submit tasks and workflows
- `TaskSpec(task_id, description, role, input_data, dependencies=[], timeout=300, retry_count=3)`
- `Workflow()` — DAG of tasks with `add_task`, `add_dependency`, `validate`, `topological_order`
- `Agent` — base class; built-in: `EchoAgent`, `TransformAgent`, `FileAgent`

## Tests

```bash
pytest tests/ -v
```
