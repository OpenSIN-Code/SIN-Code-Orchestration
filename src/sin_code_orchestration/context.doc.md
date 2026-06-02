# `context.py` — Shared Context

What this file does: provides a shared key-value store that tasks can read from and write to.

## Dependencies

- Imported by: `orchestrator.py`, tests

## Public API

- `Context()` — create a context
- `set(key, value)` — store a value
- `get(key, default=None)` — retrieve a value
- `snapshot()` — return a copy of all values

## Notes

Context is merged into task input_data before execution. Earlier tasks can pass data to later tasks.
