import pytest
from sin_code_orchestration.shared_context import SharedContextStore


def test_context_store_memory():
    store = SharedContextStore(backend="memory")
    entry = store.create_entry("task-1", "agent-1", "coder", {"input": "test"})
    assert entry.task_id == "task-1"

    retrieved = store.get(entry.id)
    assert retrieved.input_data == {"input": "test"}


def test_context_store_query():
    store = SharedContextStore(backend="memory")
    store.create_entry("t1", "a1", "planner", {"x": 1})
    store.create_entry("t1", "a2", "coder", {"y": 2})

    results = store.query(task_id="t1")
    assert len(results) == 2
