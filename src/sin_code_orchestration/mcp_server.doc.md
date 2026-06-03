# `mcp_server.py` — MCP Server

What this file does: exposes two tools over the Model Context Protocol (stdio transport) so an agent can drive the orchestrator: `orchestrate_tasks` and `run_workflow`.

## Dependency map

- Optional runtime dep: `mcp[cli]>=1.2` (install via `pip install 'sin-code-orchestration[mcp]'`)
- Imports: `.orchestrator` (TaskOrchestrator), `.workflow` (WorkflowEngine)
- Entry point: `main()` — also exposed via `python -m sin_code_orchestration.mcp_server`.

## Tools exposed

| Tool                | Inputs                                              | Returns                  |
|---------------------|-----------------------------------------------------|--------------------------|
| `orchestrate_tasks` | `tasks: list`, `dependencies: dict = None`           | JSON results string      |
| `run_workflow`      | `workflow_def: dict`, `context: dict = None`        | JSON results string      |

## Important config / limits

- **Transport: stdio.** JSON-RPC on stdin, JSON-RPC on stdout.
- **Optional dep.** `FastMCP` is imported lazily; the rest of the package works without it. `main()` raises `RuntimeError` if missing.
- **No state between calls.** Each tool invocation constructs a fresh orchestrator / engine.

## Design decisions

- **Why MCP?** Same protocol coding agents already speak. Wrapping the orchestrator as MCP tools means agents can drive workflows without writing Python glue.
- **Why a thin wrapper?** The orchestrator already has a clean Python API. The MCP layer is just JSON serialization on top.
- **Why is `mcp` optional?** Most users of the orchestrator don't use MCP. Forcing the dep on CI pipelines that only use the Python API would be wasteful.

## Usage

```bash
# 1. Install with MCP support
pip install 'sin-code-orchestration[mcp]'

# 2. Start the server (stdio transport)
python -m sin_code_orchestration.mcp_server
```

## Caveats / footguns

- **Tool calls can be long.** `run_workflow` may block for the duration of the whole workflow. Configure your MCP client with a generous request timeout.
- **No authentication.** Anyone with stdio access to the process can call the tools. Run in a trusted environment.
- **The server is blocking and single-threaded** by design. Don't expect to serve multiple agents from one process.

## Known issue

The tool implementations reference `TaskOrchestrator` and `WorkflowEngine`, which are not defined in this package's `orchestrator` / `workflow` modules. The actual public class is `Orchestrator`; the tool bodies need to be updated to use it. This is a pre-existing bug; this doc does not fix it.
