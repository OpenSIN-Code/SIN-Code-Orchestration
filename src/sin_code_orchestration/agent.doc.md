# `agent.py` — Agent Base Class and Built-ins

What this file does: defines the `Agent` ABC plus three reference implementations (`EchoAgent`, `TransformAgent`, `FileAgent`). Subclass `Agent` to plug in your own LLM-backed or tool-using agent.

## Dependency map

- Imports: `.role` (Role enum), `.task` (TaskSpec)
- Imported by: `.orchestrator` (default EchoAgent is registered for ORCHESTRATOR role)

## Public API

| Class            | Role            | Purpose                                                |
|------------------|-----------------|--------------------------------------------------------|
| `Agent` (ABC)    | n/a             | Base class. Implement `execute(task) → dict`.          |
| `EchoAgent`      | ORCHESTRATOR    | Returns `{"echo": input_data}` unchanged.              |
| `TransformAgent` | DEVELOPER       | Wraps a callable: `{"transformed": func(input)}`.      |
| `FileAgent`      | DEVELOPER       | Read or write a file inside a safe workspace boundary. |

## Important config / limits

- **`FileAgent` safe prefixes:** the user's `$HOME`, `/tmp`, `/private/tmp`, `/var/tmp`, `/private/var`. Anything else (e.g. `/etc`, `/var/log`) is rejected. macOS uses `/private/tmp` as the canonical `/tmp`; both forms are listed.
- **`FileAgent` uses `os.path.realpath`** to resolve symlinks BEFORE the prefix check. A `~/../../etc/passwd` input becomes `/etc/passwd` and is rejected.
- **`Agent.execute` may be sync or async** — the orchestrator awaits its coroutine.
- **Return value is a dict**; the orchestrator attaches it as `TaskResult.output`.

## Design decisions

- **Why a callable-based `TransformAgent` instead of an expression language?** The user can supply any Python function (including lambdas, partials, methods). An expression language would be a poor subset of Python.
- **Why a workspace boundary on `FileAgent`?** File I/O is the most common vector for accidental data leaks. Restricting to home + temp dirs is a pragmatic default. Override the prefix list or subclass `FileAgent` for stricter / looser policies.
- **Why `EchoAgent` as the default ORCHESTRATOR agent?** It makes the orchestrator usable end-to-end without any user-registered agents. Production code should always register at least one DEVELOPER agent.

## Usage examples

```python
from sin_code_orchestration.agent import TransformAgent
from sin_code_orchestration.task import TaskSpec
from sin_code_orchestration.role import Role

agent = TransformAgent(lambda d: {**d, "upper": d["name"].upper()})
spec = TaskSpec(task_id="t1", description="upcase", role=Role.DEVELOPER, input_data={"name": "alice"})
print(agent.execute(spec))  # {"transformed": {"name": "alice", "upper": "ALICE"}}
```

## Caveats / footguns

- **`FileAgent` does NOT check file size or type.** A 10 GB file will be read into memory.
- **`TransformAgent.func` is called with the raw `task.input_data`**, not the context-merged version. The orchestrator merges context before calling `execute`, but `TransformAgent` ignores the merge step.
- **`Agent` subclasses that hold external state (DB connections, model handles) should implement `close()`** themselves — the orchestrator doesn't manage agent lifecycle.
