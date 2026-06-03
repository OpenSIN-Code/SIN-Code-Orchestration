# `__init__.py` — Public Package API

What this file does: re-exports the public symbols of `sin_code_orchestration` so users can do `from sin_code_orchestration import Orchestrator, Workflow, ...`.

## Dependency map

- Imports: `.role` (Role), `.task` (TaskSpec, TaskResult, TaskStatus), `.workflow` (Workflow), `.orchestrator` (Orchestrator)
- Imported by: external user code, the MCP server

## Public API

```python
from sin_code_orchestration import (
    Orchestrator,   # central entry point for task/workflow execution
    Workflow,       # DAG of TaskSpec with cycle detection + topo sort
    TaskSpec,       # one task's spec (id, role, input, deps, timeout, retry)
    TaskResult,     # one task's outcome (status, output, error, duration)
    TaskStatus,     # enum: PENDING / RUNNING / SUCCESS / FAILED / TIMEOUT / CANCELLED
    Role,           # enum: DEVELOPER / REVIEWER / TESTER / ARCHITECT / ORCHESTRATOR
)
```

## Caveats / footguns

- Adding a new top-level class? Update `__all__` here or `import *` callers won't see it.
- The package has no `__version__`; consumers who need it should pin to a git ref or read `pyproject.toml`.
