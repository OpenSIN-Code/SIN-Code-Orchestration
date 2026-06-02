# `agent.py` — Agent Base Class

What this file does: defines the base agent class and built-in agents (EchoAgent, TransformAgent, FileAgent).

## Dependencies

- Imported by: `orchestrator.py`, tests

## Public API

- `Agent` — base class with `execute(task)` method
- `EchoAgent` — returns the input data unchanged
- `TransformAgent` — applies a transformation function
- `FileAgent` — reads/writes files

## Notes

Custom agents should subclass `Agent` and override `execute()`.
