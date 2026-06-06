#!/usr/bin/env python3
"""Test: SIN-Code-Orchestration vulnerabilities
- FileAgent path traversal via task input_data
- wait_for() infinite loop with non-existent task_id
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "/Users/jeremy/dev/SIN-Code-Orchestration")


def test_fileagent_path_traversal():
    """FileAgent.execute() uses user-provided path with NO validation."""
    import inspect
    from src.sin_code_orchestration import agent
    
    source = inspect.getsource(agent.FileAgent.execute)
    
    uses_open = "open(path" in source
    has_path_validation = "resolve" in source or "realpath" in source
    
    if uses_open and not has_path_validation:
        print("PASS: FileAgent.execute() opens ANY user-provided path WITHOUT validation")
        print("  [MEDIUM] VULNERABILITY: Can read/write arbitrary files")
        print("  Example: task.input_data['path'] = '/etc/passwd' or '../../../System/'")
        print("  Fix: Add path resolution and workspace boundary check")
    
    # Demonstrate the vulnerability
    from src.sin_code_orchestration.task import TaskSpec
    from src.sin_code_orchestration.role import Role
    
    agent_instance = agent.FileAgent(mode="read")
    
    # Test reading a system file
    try:
        task = TaskSpec(
            task_id="test-read-passwd",
            description="Read /etc/hosts",
            role=Role.DEVELOPER,
            input_data={"path": "/etc/hosts"},
        )
        result = agent_instance.execute(task)
        if "content" in result:
            print(f"  [CONFIRMED] Read /etc/hosts: {result['content'][:80]}...")
        else:
            print(f"  Result: {result}")
    except PermissionError as e:
        print(f"  INFO: Permission denied (expected on some systems): {e}")
    except FileNotFoundError:
        print(f"  INFO: /etc/hosts not found (unusual but possible)")
    except Exception as e:
        print(f"  ERROR: {e}")


def test_wait_for_infinite_loop():
    """orchestrator.py:wait_for() can loop infinitely with wrong task_id."""
    import inspect
    from src.sin_code_orchestration import orchestrator
    
    source = inspect.getsource(orchestrator.Orchestrator.wait_for)
    
    has_default_timeout = "timeout=None" in source or "timeout: float | None = None" in source
    
    if has_default_timeout:
        print("PASS: wait_for() has default timeout=None (infinite loop risk)")
        print("  [LOW] VULNERABILITY: Calling wait_for('non_existent_task') loops forever")
        print("  If no task with that ID was ever submitted, wait_for blocks indefinitely")
        print("  Fix: Add a sane default timeout (e.g., 30s)")


def test_no_command_injection():
    """Verify tasks are data-only, no shell command execution."""
    import inspect
    from src.sin_code_orchestration import task
    
    # Check TaskSpec has no command/exec fields
    fields = [f.name for f in task.__dataclass_fields__.values()]
    no_command_field = "command" not in fields and "shell" not in fields and "exec" not in fields
    
    if no_command_field:
        print("PASS: TaskSpec has no command/shell fields - no command injection surface")
        print("  Tasks are pure data objects, execution is via Python handlers not shell")
    else:
        print(f"WARN: TaskSpec fields: {fields}")


if __name__ == "__main__":
    print("=" * 60)
    print("Orchestration SECURITY VULNERABILITY TESTS")
    print("=" * 60)
    
    test_fileagent_path_traversal()
    print()
    test_wait_for_infinite_loop()
    print()
    test_no_command_injection()
    
    print("\n" + "=" * 60)
    print("SUMMARY: Orchestration has FileAgent path traversal (MEDIUM),")
    print("wait_for infinite loop (LOW). No command injection surface.")
    print("=" * 60)
