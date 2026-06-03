# `role.py` — Agent Roles

What this file does: a `Role` enum used to look up the right agent for a task. Values are strings (so they JSON-serialize cleanly through MCP and the JSON workflow format).

## Dependency map

- Imports: stdlib `enum` only.
- Imported by: `.task` (TaskSpec.role), `.agent` (base class + builtins), `.orchestrator` (agent registry key).

## Public API

| Role              | String value      | Intended use                                          |
|-------------------|-------------------|-------------------------------------------------------|
| `Role.DEVELOPER`  | `"developer"`     | Writes / edits code. Default for `TransformAgent`, `FileAgent`. |
| `Role.REVIEWER`   | `"reviewer"`      | Reads code, leaves comments.                          |
| `Role.TESTER`     | `"tester"`        | Runs tests, reports pass/fail.                        |
| `Role.ARCHITECT`  | `"architect"`     | Designs / plans; rarely mutates files.                |
| `Role.ORCHESTRATOR` | `"orchestrator"` | Default fallback. `EchoAgent` is registered here out of the box. |

## Design decisions

- **Why subclass `str` and `Enum`?** The `(str, Enum)` mixin makes each value JSON-serializable as its string form. This matters for the MCP tools and any JSON-based workflow format.
- **Why a fixed enum, not a string?** Type safety. The orchestrator's agent registry is `dict[Role, Agent]`; using a string would let typos through silently.

## Usage example

```python
from sin_code_orchestration.role import Role

role = Role.DEVELOPER
print(role.value)          # "developer"
print(role == "developer") # True (because Role subclasses str)
```

## Caveats / footguns

- **The string values are part of the public API** (they cross MCP and JSON wire formats). Renaming a value is a breaking change — bump the major version if you do.
- **Adding a new role requires** updating the orchestrator's default agent registry if you want fallback behavior. Otherwise unknown roles will fall through to the ORCHESTRATOR agent.
