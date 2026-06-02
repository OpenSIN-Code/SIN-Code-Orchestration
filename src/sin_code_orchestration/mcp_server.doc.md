# `mcp_server.py` — MCP Server for Orchestration

What this file does: exposes workflow orchestration tools to AI agents via the Model Context Protocol.

## Dependencies

- Imported by: CLI, external MCP hosts
- Imports: `orchestrator` (TaskOrchestrator), `workflow` (WorkflowEngine)

## Tools

- `orchestrate_tasks(tasks, dependencies=None)` — orchestrate a set of tasks with dependencies and parallel execution
- `run_workflow(workflow_def, context=None)` — run a workflow definition with optional context

## Usage

```bash
python -m sin_code_orchestration.mcp_server
```

Requires `pip install -e ".[mcp]"`.

## Notes

Uses `mcp.server.fastmcp.FastMCP` for tool registration.
