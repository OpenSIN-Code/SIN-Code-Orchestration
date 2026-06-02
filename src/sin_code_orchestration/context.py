"""Context-aware shared state and MCP integration.

Docs: context.doc.md
"""

from typing import Any


class Context:
    """Shared execution context for tasks and agents.

    Holds a key-value store that persists across tasks in a workflow.
    """

    def __init__(self):
        self._store: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value from context."""
        return self._store.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Store a value in context."""
        self._store[key] = value

    def merge(self, data: dict[str, Any]) -> None:
        """Merge a dictionary into context."""
        self._store.update(data)

    def snapshot(self) -> dict[str, Any]:
        """Return a shallow copy of the current context."""
        return dict(self._store)
