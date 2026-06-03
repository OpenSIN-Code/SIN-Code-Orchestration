"""MCP server for agent integration.

Exposes two tools over the Model Context Protocol (stdio transport) so an
agent can drive the orchestrator: `orchestrate_tasks` and `run_workflow`.

Docs: mcp_server.doc.md
"""
from __future__ import annotations

import json

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    # The `mcp` extra is optional — `main()` raises a clear error if you
    # actually try to serve. This keeps the rest of the package importable
    # in environments without the dep.
    FastMCP = None

from .orchestrator import TaskOrchestrator
from .workflow import WorkflowEngine


def main():
    """Start the MCP server over stdio (blocking).

    Raises:
        RuntimeError: if the `mcp` extra is not installed.
    """
    if FastMCP is None:
        raise RuntimeError("mcp package not installed. Install with: pip install 'sin-code-orchestration[mcp]'")

    mcp = FastMCP("sin-code-orchestration")

    @mcp.tool()
    def orchestrate_tasks(tasks: list, dependencies: dict = None) -> str:
        """Orchestrate a set of tasks with dependencies and parallel execution.

        Args:
            tasks: List of task dicts.
            dependencies: Optional `{task_id: [dep_id, ...]}` map.

        Returns:
            JSON string with the orchestrator's results.
        """
        orch = TaskOrchestrator()
        return json.dumps(orch.orchestrate(tasks, dependencies=dependencies), indent=2)

    @mcp.tool()
    def run_workflow(workflow_def: dict, context: dict = None) -> str:
        """Run a workflow definition with optional context.

        Args:
            workflow_def: Dict describing the workflow (nodes, edges, etc.).
            context: Optional initial context dict.

        Returns:
            JSON string with the workflow's results.
        """
        engine = WorkflowEngine()
        return json.dumps(engine.run(workflow_def, context=context), indent=2)

    mcp.run()


if __name__ == "__main__":
    main()
