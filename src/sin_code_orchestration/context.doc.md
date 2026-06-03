# `context.py` — Shared Execution Context

What this file does: a simple key-value store that persists across tasks in a workflow. The orchestrator snapshots the context before each task and merges it into `task.input_data` so agents see everything upstream agents have written.

## Dependency map

- Imports: stdlib typing only.
- Imported by: `.orchestrator` (one shared `Context` per orchestrator instance).

## Public API

| Method                  | Purpose                                                          |
|-------------------------|------------------------------------------------------------------|
| `Context()`             | Construct an empty context                                       |
| `.get(key, default=None)` | Retrieve a value; return default if missing                      |
| `.set(key, value)`      | Store a value (overwrites existing)                              |
| `.merge(data)`          | Update with a dict (last-writer-wins)                            |
| `.snapshot()`           | Return a shallow copy (used by the orchestrator before each task) |

## Important config / limits

- **Keys are strings; values are any picklable type.** The orchestrator doesn't enforce this, but `merge` will break on unhashable types.
- **No namespacing.** If two agents both write `"result"`, the second wins. The orchestrator does NOT prefix keys with the task_id.
- **Shallow copies only.** A value that is a mutable container (e.g. `list`) is shared by reference between the context and any agent that reads it. Mutate carefully.
- **No size limit.** A context with 100 MB of data is a 100 MB copy on every `snapshot()`.

## Design decisions

- **Why a dict and not a typed structure?** Workflows are dynamic — the keys depend on what agents decide to write. A typed schema would lock callers in.
- **Why snapshot before each task?** It decouples agents: a task reading `ctx["x"]` sees the value at dispatch time, not whatever a concurrent task might have written in the meantime.
- **Why `merge` is `dict.update`?** Same rationale as snapshot: simple, predictable, no surprise semantics.

## Usage example

```python
from sin_code_orchestration.context import Context

ctx = Context()
ctx.set("user", "alice")
ctx.merge({"role": "admin"})
print(ctx.snapshot())  # {"user": "alice", "role": "admin"}
```

## Caveats / footguns

- **Last-writer-wins on `merge`.** If `ctx.set("k", 1)` and then `ctx.merge({"k": 2})`, the value is `2`.
- **The `snapshot()` copy is shallow.** A nested dict in the context is shared by reference with whatever you pass it to. Use deep-copy yourself if you need true isolation.
