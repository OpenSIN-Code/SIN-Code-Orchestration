"""Context-aware shared state and MCP integration.

The `Context` class is a simple key-value store that persists across tasks
in a workflow. The orchestrator snapshots the context before each task and
merges it into `task.input_data`, so downstream agents see everything
upstream agents have written.

Docs: context.doc.md
"""

from typing import Any


# ── Context ────────────────────────────────────────────────────────────
class Context:
    """Shared execution context for tasks and agents.

    Holds a key-value store that persists across tasks in a workflow.
    Keys are strings; values can be any picklable type (the orchestrator
    doesn't enforce this, but `merge` will break on unhashable types).
    """

    def __init__(self):
        # Underscore prefix = "private" by convention; the public API is
        # the methods below. Direct access is allowed but discouraged.
        self._store: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from context; return `default` if absent."""
        return self._store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Store a value in context. Overwrites any existing value at `key`."""
        self._store[key] = value

    def merge(self, data: dict[str, Any]) -> None:
        """Merge a dictionary into context (last-writer-wins on key collision)."""
        self._store.update(data)

    def snapshot(self) -> dict[str, Any]:
        """Return a shallow copy of the current context.

        The orchestrator calls this before dispatching each task so agents
        see a stable view even if subsequent tasks mutate the live store.
        """
        return dict(self._store)
