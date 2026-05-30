# SIN-Code Orchestration

> Advanced Multi-Agent Orchestration with Context-Aware MCP and Verified Workflows.

Part of the SIN-Code agent-engineering stack.

## Why

Single agents hit limits on complex tasks. Orchestration coordinates specialized agents (planner, coder, reviewer, verifier) with:
- **Context-Aware MCP**: Stateful, dezentrale Koordination über Shared Context Store
- **Role-based permissions**: Fine-grained tool access control
- **VMAO verification loop**: Plan → Execute → Verify → Replan cycle
- **Dependency-aware execution**: Topological workflow scheduling

## Features

- **Shared Context Store**: Redis/memory/SQLite backend for distributed state
- **Role system**: Planner, Coder, Reviewer, Verifier with configurable permissions
- **Verification loop**: Formal verification of agent outputs before progression
- **MCP server**: Exposes orchestration primitives to any MCP-compatible agent
- **CLI**: Submit tasks, query status, execute workflows from YAML

## Quickstart

```bash
pip install -e .

# Start the MCP server
sin-orch serve

# Submit a task
sin-orch submit my-task coder '{"code": "def hello(): pass"}'

# Run a workflow
sin-orch workflow my-workflow.yaml
```

## Configuration

See `config.yaml` for:
- Orchestration mode (hierarchical/parallel/reactive)
- Context store backend (redis/memory/sqlite)
- Role definitions and tool permissions
- Verification loop parameters

## MCP Integration

```yaml
# ~/.config/opencode/config.yaml
mcpServers:
  sin-orch:
    command: sin-orch
    args: [serve]
```

Exposed tools: `create_task`, `get_task_status`, `update_task`, `query_tasks`, `await_dependencies`.

## License

MIT — see LICENSE.
