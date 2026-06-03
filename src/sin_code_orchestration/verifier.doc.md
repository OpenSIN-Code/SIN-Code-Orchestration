# `verifier.py` — Workflow Verification

What this file does: post-execution checks for `TaskResult`s. Two layers — `Oracle` (the policy: status / keys / no-error) and `Verifier` (the bulk runner that applies an `Oracle` to a list of results).

## Dependency map

- Imports: stdlib typing, `.task` (TaskResult, TaskStatus), `.workflow` (Workflow — currently unused, kept for forward compat).
- Imported by: `.orchestrator` (constructs `Verifier(Oracle())` and runs it on every result).

## Public API

| Symbol            | Purpose                                                                 |
|-------------------|-------------------------------------------------------------------------|
| `Oracle(rules={})`| Single-result policy. Three checks: status, keys, no-error.             |
| `Oracle.verify(result)` | Return `{"passed": bool, "checks": [{check, passed, detail}]}` for one result. |
| `Verifier(oracle=None)`  | Bulk runner. Wraps an `Oracle` (default: `Oracle()` with no rules). |
| `Verifier.verify(results)` | Apply the oracle to a list, return one report per result.     |

## Important config / limits

- **Three checks, all default-on.** Disable a check by subclassing and overriding `verify()`.
- **`Oracle.rules` is `{task_id: [expected_output_key, ...]}`** — an empty dict means "don't enforce keys". Per-task rules only; no global rules.
- **`Oracle.verify` does not catch exceptions in checks** — a buggy rule crashes the verification.
- **`Verifier.verify([])` returns `[]`.** No special handling for empty input.

## Design decisions

- **Why three checks (status / keys / no-error)?** They cover the three most common failure modes: the task didn't run, it ran but produced the wrong shape, or it ran and errored.
- **Why per-task key rules instead of a global schema?** Workflows are dynamic; different tasks legitimately need different output shapes. A global schema would be over-specified.
- **Why return a dict and not a Pydantic model?** Verification reports flow into JSON (MCP, logs). A dict is the most portable shape.
- **Why is the `Workflow` import unused today?** Forward-compat: a future `Verifier` that takes a `Workflow` (not just results) to verify structural properties of the DAG itself. Currently dead code; remove if it stays unused.

## Usage example

```python
from sin_code_orchestration.verifier import Oracle
from sin_code_orchestration.task import TaskSpec, TaskResult, TaskStatus
from sin_code_orchestration.role import Role

# Strict mode: enforce output shape
oracle = Oracle(rules={"build": ["artifact"]})
result = TaskResult(
    task_id="build", status=TaskStatus.SUCCESS,
    output={"artifact": "bin/app"}, error=None, duration_seconds=1.0,
)
print(oracle.verify(result))
# {"passed": True, "checks": [
#   {"check": "status", "passed": True},
#   {"check": "keys",   "passed": True},
#   {"check": "error",  "passed": True},
# ]}
```

## Caveats / footguns

- **`rules` is a strict key check, not a deep schema.** It only verifies that the listed keys are PRESENT. It doesn't check types, formats, or values.
- **Verification is best-effort.** A report saying `"passed": True` is necessary but not sufficient for correctness — the verifier doesn't run the actual tests.
- **`Oracle.verify` mutates the `report` dict in place and returns it.** The returned object is the same instance; don't share it across threads.
