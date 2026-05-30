"""Context-Aware MCP Server für dezentrale Agenten-Koordination."""
from __future__ import annotations

import json
import structlog
from pathlib import Path

import yaml

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None

from .shared_context import SharedContextStore, ContextEntry, ContextStatus
from .roles import AgentConfig, Role


logger = structlog.get_logger()


class ContextAwareMCP:
    """MCP-Server mit Shared Context Store für stateful Agenten-Koordination."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = {}
        if config_path and Path(config_path).exists():
            with open(config_path) as f:
                self.config = yaml.safe_load(f) or {}

        ctx_cfg = self.config.get("context_store", {})
        self.ctx_store = SharedContextStore(
            backend=ctx_cfg.get("backend", "memory"),
            redis_url=ctx_cfg.get("redis_url"),
            namespace=ctx_cfg.get("namespace"),
            db_path=ctx_cfg.get("db_path")
        )
        self._mcp = None

    def _get_agent_config(self, agent_id: str) -> AgentConfig:
        roles_cfg = self.config.get("roles", {})
        for role_name, role_cfg in roles_cfg.items():
            if agent_id.startswith(role_name):
                return AgentConfig(
                    agent_id=agent_id,
                    role=Role(role_name),
                    model=role_cfg.get("model", "gpt-4o"),
                    max_iterations=role_cfg.get("max_iterations", 10),
                    timeout_seconds=role_cfg.get("timeout_seconds", 300),
                    sandbox=role_cfg.get("sandbox", False),
                    require_approval=role_cfg.get("require_approval", False),
                )
        return AgentConfig(agent_id=agent_id, role=Role.CODER, model="gpt-4o")

    def register_tools(self):
        """Registriert alle MCP-Tools."""
        @self._mcp.tool()
        def create_task(task_id: str, agent_id: str, input_data: str) -> str:
            """Create a new task entry in the shared context store."""
            entry = self.ctx_store.create_entry(
                task_id=task_id,
                agent_id=agent_id,
                role=self._get_agent_config(agent_id).role.value,
                input_data=json.loads(input_data)
            )
            return json.dumps({"entry_id": entry.id, "status": entry.status.value})

        @self._mcp.tool()
        def get_task_status(entry_id: str) -> str:
            """Get the current status of a task."""
            entry = self.ctx_store.get(entry_id)
            if not entry:
                return json.dumps({"error": "Entry not found"})
            return json.dumps({
                "id": entry.id,
                "task_id": entry.task_id,
                "status": entry.status.value,
                "output": entry.output_data,
                "error": entry.error,
            })

        @self._mcp.tool()
        def update_task(entry_id: str, status: str, output_data: str = "{}", error: str = "") -> str:
            """Update a task's status and output."""
            self.ctx_store.update_status(
                entry_id,
                ContextStatus(status),
                output_data=json.loads(output_data) if output_data else None,
                error=error or None
            )
            return json.dumps({"updated": entry_id})

        @self._mcp.tool()
        def query_tasks(task_id: str = "", agent_id: str = "", status: str = "") -> str:
            """Query tasks by filters."""
            entries = self.ctx_store.query(
                task_id=task_id or None,
                agent_id=agent_id or None,
                status=ContextStatus(status) if status else None
            )
            return json.dumps([{
                "id": e.id, "task_id": e.task_id, "agent_id": e.agent_id,
                "role": e.role, "status": e.status.value,
                "created_at": e.created_at,
            } for e in entries])

        @self._mcp.tool()
        def await_dependencies(entry_id: str, timeout: int = 300) -> str:
            """Wait for dependent tasks to complete."""
            import time
            entry = self.ctx_store.get(entry_id)
            if not entry:
                return json.dumps({"error": "Entry not found"})

            start = time.time()
            while time.time() - start < timeout:
                all_ready = True
                for dep_id in entry.dependencies:
                    dep = self.ctx_store.get(dep_id)
                    if not dep or dep.status not in (ContextStatus.COMPLETED, ContextStatus.VERIFIED):
                        all_ready = False
                        break
                if all_ready:
                    return json.dumps({"ready": True, "dependencies": entry.dependencies})
                time.sleep(0.5)
            return json.dumps({"ready": False, "timeout": True})

    def run(self, host: str = "127.0.0.1", port: int = 8770):
        if FastMCP is None:
            raise RuntimeError("mcp package not installed")
        self._mcp = FastMCP("sin-code-orchestration")
        self.register_tools()
        logger.info("Starting Context-Aware MCP server", host=host, port=port)
        self._mcp.run()


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8770)
    args = parser.parse_args()

    server = ContextAwareMCP(args.config)
    server.run(args.host, args.port)


if __name__ == "__main__":
    main()
