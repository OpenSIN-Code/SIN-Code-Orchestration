# SIN-Code Orchestration

> DAG-based multi-agent orchestration engine with parallel execution, retry, and verification. Coordinate tasks across roles (developer, tester, architect) with dependency-aware scheduling.

[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

Part of the [SIN-Code](https://github.com/OpenSIN-Code) agent-engineering stack. Install all subsystems together via the [SIN-Code Bundle](https://github.com/OpenSIN-Code/SIN-Code-Bundle).

## Features

- **DAG workflows** — define tasks with dependencies and let the engine schedule them
- **Parallel execution** — run independent tasks concurrently with configurable max concurrency
- **Role-based agents** — assign tasks to roles (Developer, Tester, Architect, Orchestrator)
- **Retry and timeout** — per-task retry count and timeout with automatic failure handling
- **Verification** — optional post-task verification via the Verification Oracle
- **Context sharing** — tasks inherit context from previous tasks in the workflow
- **MCP server** — expose orchestration tools to AI agents via the Model Context Protocol

## Installation

```bash
pip install -e .
```

Optional MCP server support:
```bash
pip install -e ".[mcp]"
```

See [INSTALL.md](./INSTALL.md) for detailed setup instructions.

## Usage

### Library

```python
from sin_code_orchestration import Orchestrator, TaskSpec, Role, Workflow

orch = Orchestrator(max_concurrent=4)

# Single task
spec = TaskSpec(
    task_id="t1",
    description="Say hello",
    role=Role.DEVELOPER,
    input_data={"text": "hello"}
)
result = orch.submit(spec)
print(result.status)  # SUCCESS

# Workflow with dependencies
wf = Workflow()
wf.add_task(TaskSpec(task_id="build", description="Build", role=Role.DEVELOPER, input_data={}))
wf.add_task(TaskSpec(task_id="test", description="Test", role=Role.TESTER, input_data={}, dependencies=["build"]))
wf.add_task(TaskSpec(task_id="deploy", description="Deploy", role=Role.ARCHITECT, input_data={}, dependencies=["test"]))
results = orch.submit_workflow(wf)

# Check status
print(orch.get_status("test"))
```

## Testing

```bash
pytest tests/ -v
```

## MCP Server

Run the MCP server for agent integration:

```bash
python -m sin_code_orchestration.mcp_server
```

Tools exposed:
- `orchestrate_tasks(tasks, dependencies=None)` — orchestrate a set of tasks with dependencies and parallel execution
- `run_workflow(workflow_def, context=None)` — run a workflow definition with optional context

## Integration

Orchestration is designed to work as part of the SIN-Code ecosystem:

- **SIN-Code Bundle** — orchestrates all subsystems from a single CLI (`sin`)
- **Verification Oracle** — gate workflows on verification results
- **Ephemeral Full-Stack Mocking (EFSM)** — spin up mock environments for test tasks
- **Review Interface** — pause workflows for human review before deploy

## License

MIT — see [LICENSE](./LICENSE).
